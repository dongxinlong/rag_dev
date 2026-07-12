"""
文档处理任务

流程：
1. 创建解析日志
2. 更新状态为 processing
3. 调用 MinerU 解析
4. 处理图片（调用视觉模型替换为文字）
5. 保存最终 result.md 到 MinIO
6. 更新状态为 completed/failed
"""
import time
from datetime import datetime
from celery_app import celery_app


@celery_app.task(
    bind=True,
    name="tasks.process_document",
    max_retries=3,
    soft_time_limit=7200,  # 2 小时软超时（MinerU 解析大文件很慢）
    time_limit=7500,       # 2 小时 5 分钟硬超时
)
def process_document(self, kb_id: str, file_path: str, file_id: str = None):
    """
    处理文档任务

    参数：
        kb_id: 知识库 ID
        file_path: MinIO 中的文件路径
        file_id: 文件 ID（可选）
    """
    import asyncio
    from config.logging import get_logger

    logger = get_logger("celery.document")
    logger.info(f"开始处理文档: kb_id={kb_id}, file_path={file_path}")

    try:
        asyncio.run(_process_document_async(self, kb_id, file_path, file_id, logger))
    except Exception as e:
        logger.error(f"文档处理失败: {e}")
        _fail_task_sync(file_id, str(e), "unknown")
        raise self.retry(exc=e, countdown=60)


async def _process_document_async(task, kb_id: str, file_path: str, file_id: str, logger):
    """异步处理文档"""
    from database.session import db_session
    from services.knowledgebase import KnowledgeBaseService
    from services.parse_log import ParseLogService
    from core.parser.mineru_parser import MinerUParser
    from services.image_processor import image_processor
    from core.minio import MinioClient
    from config.settings import settings

    await db_session.create_pool()
    total_start_time = time.time()

    try:
        async with db_session.session_factory() as session:
            kb_service = KnowledgeBaseService(session)
            log_service = ParseLogService(session)

            # 1. 获取或创建解析日志（重试时复用旧日志）
            file_name = file_path.split("/")[-1] if file_path else None
            log = await log_service.get_by_file_id(file_id)
            if log:
                # 重试时更新现有日志
                await log_service.update(
                    log.id,
                    task_id=task.request.id,
                    task_status="started",
                    task_retry_count=task.request.retries,
                    stage="initializing",
                    stage_message=f"第 {task.request.retries + 1} 次尝试"
                )
                logger.info(f"复用现有日志: {log.id}, 重试次数: {task.request.retries}")
            else:
                # 首次创建日志
                log = await log_service.create(
                    kb_id=kb_id,
                    file_id=file_id,
                    file_name=file_name,
                    file_path=file_path,
                    task_id=task.request.id
                )
                logger.info(f"创建解析日志: {log.id}")
            log_id = log.id

            # 2. 开始任务
            await log_service.start_task(log_id, task.request.id)

            # 3. 更新知识库状态为 processing（用 file_id，不是 kb_id）
            await kb_service.update_status(file_id, "processing")
            logger.info(f"状态更新为 processing: file_id={file_id}")

            # 4. 调用 MinerU 解析
            await log_service.update_stage(log_id, "parsing", "MinerU 解析中")
            await log_service.update_mineru_info(log_id, status="processing")

            mineru_start_time = time.time()
            try:
                parser = MinerUParser()
                import tempfile
                import os

                minio_client = MinioClient()
                await minio_client.init()

                file_name = file_path.split("/")[-1]
                temp_dir = tempfile.mkdtemp()
                temp_file = os.path.join(temp_dir, file_name)

                # 下载文件
                file_data = await minio_client.get_object(settings.MINIO_BUCKET, file_path)
                with open(temp_file, "wb") as f:
                    f.write(file_data)

                # 解析
                result = await parser.parse(temp_file, file_id=kb_id)

                mineru_duration = time.time() - mineru_start_time
                await log_service.update_mineru_info(
                    log_id,
                    status="completed",
                    start_time=datetime.fromtimestamp(mineru_start_time),
                    end_time=datetime.now(),
                    duration=mineru_duration,
                    output_chars=len(result.content)
                )
                logger.info(f"MinerU 解析完成: {len(result.content)} 字符, 耗时: {mineru_duration:.1f}s")

                # 清理临时文件
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)

            except Exception as e:
                mineru_duration = time.time() - mineru_start_time
                await log_service.update_mineru_info(
                    log_id,
                    status="failed",
                    start_time=datetime.fromtimestamp(mineru_start_time),
                    end_time=datetime.now(),
                    duration=mineru_duration,
                    error=str(e)
                )
                # 只在最后一次重试时记录错误
                if task.request.retries >= task.max_retries:
                    await log_service.add_error(log_id, "mineru", str(e), "mineru_error")
                raise

            # 5. 处理图片
            parsed_minio_key = result.metadata.get("parsed_minio_key", "")
            if parsed_minio_key:
                # 统计图片数量
                import re
                md_pattern = r'!\[([^\]]*)\]\((images/[^)]+)\)'
                html_pattern = r'<img\s+[^>]*src="([^"]*images/[^"]*)"[^>]*/?>'
                md_matches = re.findall(md_pattern, result.content)
                html_matches = re.findall(html_pattern, result.content)
                total_images = len(md_matches) + len(html_matches)

                # 只有有图片时才处理
                if total_images > 0:
                    await log_service.update_stage(log_id, "image_processing", "图片处理中")
                    await log_service.update_image_info(log_id, status="processing", total_count=total_images)

                    image_start_time = time.time()
                    try:
                        # 处理图片
                        processed_content, image_errors = await image_processor.process_content(
                            content=result.content,
                            parsed_minio_key=parsed_minio_key
                        )

                        # 记录图片处理错误
                        logger.info(f"图片处理错误数: {len(image_errors)}")
                        for error in image_errors:
                            logger.info(f"记录错误: {error.get('error_type')}: {error.get('error_message')}")
                            await log_service.add_error(
                                log_id,
                                stage="image_processing",
                                message=error.get("error_message", ""),
                                error_type=error.get("error_type", "unknown")
                            )

                        # 统计结果
                        failed_count = len(image_errors)
                        success_count = total_images - failed_count

                        image_duration = time.time() - image_start_time
                        await log_service.update_image_info(
                            log_id,
                            status="completed",
                            processed_count=total_images,
                            success_count=success_count,
                            failed_count=failed_count,
                            end_time=datetime.now(),
                            duration=image_duration
                        )
                        logger.info(f"图片处理完成: {success_count}/{total_images} 成功, 失败: {failed_count}, 耗时: {image_duration:.1f}s")

                    except Exception as e:
                        image_duration = time.time() - image_start_time
                        await log_service.update_image_info(
                            log_id,
                            status="failed",
                            end_time=datetime.now(),
                            duration=image_duration
                        )
                        await log_service.add_error(log_id, "image_processing", str(e), "image_error")
                        # 图片处理失败不中断，使用原始内容
                        processed_content = result.content
                        logger.warning(f"图片处理失败，使用原始内容: {e}")
                else:
                    processed_content = result.content
                    logger.info(f"无图片需要处理，共 {total_images} 张")
            else:
                processed_content = result.content
                logger.info("无解析文件路径，跳过图片处理")

            # 6. 保存最终 result.md 到 MinIO
            await log_service.update_stage(log_id, "saving", "保存结果文件")
            await log_service.update_mineru_info(log_id, status="uploading")

            if parsed_minio_key:
                result_minio_key = parsed_minio_key.rsplit("/", 1)[0] + "/result.md"

                try:
                    minio_client2 = MinioClient()
                    await minio_client2.init()
                    await minio_client2.upload_data(
                        bucket_name=settings.MINIO_BUCKET,
                        object_name=result_minio_key,
                        data=processed_content.encode("utf-8"),
                        content_type="text/markdown"
                    )

                    await log_service.update(
                        log_id,
                        minio_original_key=file_path,
                        minio_parsed_key=parsed_minio_key,
                        minio_result_key=result_minio_key,
                        result_chars=len(processed_content),
                        minio_status="completed"
                    )
                    logger.info(f"result.md 已保存: {result_minio_key}")

                    # 7. 分块处理
                    await log_service.update_stage(log_id, "chunking", "文档分块中")
                    chunk_count = 0
                    try:
                        from core.splitter.chunker import MarkdownChunker
                        from services.vectorizer import get_vectorizer

                        chunker = MarkdownChunker()
                        chunks = chunker.chunk(
                            content=processed_content,
                            document_id=file_id,
                            document_name=file_name
                        )
                        logger.info(f"分块完成: {len(chunks)} 个 chunk")

                        # 8. 向量化并存入数据库
                        await log_service.update_stage(log_id, "vectorizing", "向量化入库中")
                        vectorizer = get_vectorizer(session)
                        chunk_count = await vectorizer.vectorize_and_store(
                            chunks=chunks,
                            file_id=file_id,
                            file_name=file_name
                        )
                        logger.info(f"向量化完成: {chunk_count} 个 chunk 已入库")

                        await log_service.update(
                            log_id,
                            chunk_count=chunk_count,
                            chunk_status="completed"
                        )
                    except Exception as e:
                        await log_service.add_error(log_id, "chunking", str(e), "chunk_error")
                        logger.error(f"分块/向量化失败: {e}")
                        # 失败不中断，继续完成任务

                    # 更新知识库
                    await kb_service.update_status(
                        file_id, "completed",
                        parsed_minio_key=result_minio_key
                    )

                except Exception as e:
                    await log_service.update(
                        log_id,
                        minio_status="failed"
                    )
                    await log_service.add_error(log_id, "saving", str(e), "minio_error")
                    raise
            else:
                await kb_service.update_status(file_id, "completed")

            # 7. 完成任务
            total_duration = time.time() - total_start_time
            await log_service.update(
                log_id,
                total_duration=total_duration
            )
            await log_service.complete_task(log_id)
            logger.info(f"文档处理完成: {kb_id}, 总耗时: {total_duration:.1f}s")

    finally:
        try:
            await db_session.close()
        except Exception:
            pass  # 忽略关闭时的错误


def _fail_task_sync(file_id: str, error_message: str, error_stage: str):
    """同步更新任务失败状态"""
    import asyncio
    from database.session import db_session
    from services.knowledgebase import KnowledgeBaseService
    from services.parse_log import ParseLogService

    async def _update():
        await db_session.create_pool()
        try:
            async with db_session.session_factory() as session:
                kb_service = KnowledgeBaseService(session)
                log_service = ParseLogService(session)

                # 更新知识库状态（用 file_id）
                await kb_service.update_status(file_id, "failed", error_message)

                # 更新日志
                log = await log_service.get_by_file_id(file_id)
                if log:
                    await log_service.fail_task(log.id, error_message, error_stage)
        finally:
            await db_session.close()

    asyncio.run(_update())

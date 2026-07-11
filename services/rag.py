"""
RAG 相关服务接口
"""
import time
import json

from fastapi import Depends

from sqlalchemy import select, delete, func

from core.llm import LLMAPIService
from core.embedding import EmbeddingService
from database.session import DatabaseSession
from schemas.rag import RAGQueryRequest, RAGQueryResponse
from models.rag import Document
from config.settings import settings
from config.logging import get_logger
from services.messages import MessagesService


logger = get_logger("rag")


class RAGService:

    def __init__(self, llm_api_service: LLMAPIService, db: DatabaseSession, embedding_service: EmbeddingService):
        self.llm_api_service = llm_api_service
        self.db = db
        self.embedding_service = embedding_service
        self.messages_service = MessagesService(self.db)
        self.system_prompts = """
            你是知识库问答助手。
            - 如果提供了参考文档，基于参考文档回答
            - 如果用户问的是对话历史相关的问题，基于历史记录回答
            - 不要编造或使用自身知识回答知识类问题
        """

    async def _get_messages_for_chatId(self, chat_id: str):
        """通过chat_id获取消息"""
        return await self.messages_service.messages_for_rag(chat_id=chat_id)
    
    async def _save_user_question(self, chat_id: str, question: str):
        """保存用户问题"""
        data = {
            "chat_id": chat_id,
            "role": "user",
            "content": question,
            "model": self.llm_api_service.mode,
            "status": "completed"
        }
        await self.messages_service.createMessages(**data)

    async def _save_llm_answer(self, chat_id: str, answer: dict):
        """保存LLM答案"""
        data = {
            "chat_id": chat_id,
            "role": "assistant",
            "content": answer.get("content", ""),
            "tokens_prompt": answer.get("tokens_prompt", 0),
            "tokens_completion": answer.get("tokens_completion", 0),
            "cache_tokens": answer.get("cache_tokens", 0),
            "cost": answer.get("cost", 0),
            "model": answer.get("model", ""),
            "extra_data": answer.get("extra_data", {}),
            "status": answer.get("status", "completed")
        }
       
        return await self.messages_service.createMessages(**data)

    async def _search(self, **kwargs: RAGQueryRequest):
        """
        RAG向量检索
        """
        # 1. 对问题进行向量化
        question = kwargs.get("question")
        top_k = kwargs.get("top_k")
        question_embedding = await self.embedding_service.get_embedding(question)
        # 2. 构建余弦距离，越小越相似
        distance = Document.embedding.cosine_distance(question_embedding).label("distance")
        # 3. 查询最相似的文档
        stmt = select(Document, distance).order_by(distance.asc()).limit(top_k)
        # 如果余弦距离大于设定的阈值，则过滤掉
        stmt = stmt.where(distance < settings.DISTANCE_THRESHOLD)
        result = await self.db.execute(stmt)
        return result.all()
    
    async def _merge_prompts(self, question: str, documents: list, history: list = None) -> tuple[list, bool]:
        """
        合并问题和文档为 prompts, 载入历史消息
        返回: (prompts, should_call_llm)
        """
        prompts = []
        if history:
            # 将历史消息转换成 OpenAI 格式
            for msg in history:
                if msg.content:
                    prompts.append({"role": msg.role, "content": msg.content})

        # 判断文档是否为空
        has_documents = bool(documents)
        docs_content = "\n".join([doc.content for doc in documents]) if documents else "无"

        if has_documents:
            # 有文档时：正常 prompt
            content = f"""
                【参考文档】:
                {docs_content}

                【用户问题】: {question}
            """
            message = {"role": "user", "content": content}
            prompts.append(message)
            return prompts, True  # 可以调用 LLM
        else:
            # 无文档时：检查是否有历史记录
            has_history = bool(history)

            if has_history:
                # 有历史记录：允许调用 LLM，让它根据历史回答
                content = f"【参考文档】: 无\n\n【用户问题】: {question}"
                message = {"role": "user", "content": content}
                prompts.append(message)
                return prompts, True
            else:
                # 无文档 + 无历史：不调用 LLM，直接返回固定文案
                return prompts, False

    async def _prepare_prompts(self, chat_id: str, question: str, top_k: int):
        """
        准备 Prompts 公共逻辑，对于 rag_query 和 rag_query_stream 复用
        返回: (prompts, sources, should_call_llm)
        """
        # 1. 载入历史记录
        history = await self._get_messages_for_chatId(chat_id=chat_id)

        # 2. 搜索文档（始终搜索，不跳过）
        result = await self._search(question=question, top_k=top_k)

        # 3. 构建Prompts（同时包含历史和文档）
        prompts, should_call_llm = await self._merge_prompts(question, [doc for doc, distance in result], history)
        # 4. 保存用户问题
        await self._save_user_question(chat_id, question)
        # 5. 构造 sources
        sources = [
            {
                "id": doc.id,
                "file_name": doc.file_name,
                "content": doc.content,
                "similarity": 1 - distance
            }
            for doc, distance in result
        ]
        return prompts, sources, should_call_llm

    async def rag_query(self, **kwargs: RAGQueryRequest) -> RAGQueryResponse:
        """
        RAG查询
        """
        chat_id = kwargs.get("chat_id")
        question = kwargs.get("question")
        top_k = kwargs.get("top_k")
        try:
            # 1. RAG前置流程
            prompts, sources, should_call_llm = await self._prepare_prompts(chat_id, question, top_k)

            # 2. 如果不需要调用 LLM（无文档 + 非历史问题），直接返回固定文案
            if not should_call_llm:
                no_answer = "抱歉，知识库中没有找到相关信息。"
                llm_answer = {
                    "content": no_answer,
                    "tokens_prompt": 0,
                    "tokens_completion": 0,
                    "cache_tokens": 0,
                    "cost": 0,
                    "model": self.llm_api_service.mode,
                    "extra_data": {"sources": []},
                    "status": "completed"
                }
                await self._save_llm_answer(chat_id, llm_answer)
                return {
                    "answer": no_answer,
                    "sources": [],
                    "cost": 0
                }

            # 3. 调用LLM API进行回答

            # 2. 调用LLM API进行回答
            answer = await self.llm_api_service.send_message(prompts, self.system_prompts)
            # 3. 保存 AI 回复
            llm_answer = {
                "content": answer.get("content", ""),
                "tokens_prompt": answer.get("cost", {}).get("meta", {}).get("input_tokens", 0),
                "tokens_completion": answer.get("cost", {}).get("meta", {}).get("completion_tokens", 0),
                "cache_tokens": answer.get("cost", {}).get("meta", {}).get("cache_input_tokens", 0),
                "cost": answer.get("cost", {}).get("cost", 0),
                "model": self.llm_api_service.mode,
                "extra_data": {"sources": sources},
                "status": "completed"
            }
            await self._save_llm_answer(chat_id, llm_answer)
            return {
                "answer": answer.get("content", ""),
                "sources": sources,
                "cost": answer.get("cost", {}).get("cost", 0)
            }
        except Exception as e:
            return {
                "answer": f"抱歉，处理您的问题时出现了错误: {str(e)}",
                "sources": [],
                "cost": 0
            }
    
    async def rag_query_stream(self, **kwargs: RAGQueryRequest):
        """
        RAG查询（流式）
        """

        chat_id = kwargs.get("chat_id")
        question = kwargs.get("question")
        top_k = kwargs.get("top_k")
        msg_id = None
        try:
            # 1. RAG前置流程
            prompts, sources, should_call_llm = await self._prepare_prompts(chat_id, question, top_k)

            # 2. 如果不需要调用 LLM（无文档 + 非历史问题），直接返回固定文案
            if not should_call_llm:
                no_answer = "抱歉，知识库中没有找到相关信息。"
                # 保存用户问题已在这之前完成
                msg_data = {
                    "role": "assistant",
                    "content": no_answer,
                    "status": "completed",
                    "extra_data": {"sources": []},
                    "model": self.llm_api_service.mode
                }
                msg_instance = await self._save_llm_answer(chat_id, msg_data)
                msg_id = msg_instance.id

                # 返回空 sources
                data = json.dumps({"type": "sources", "value": []})
                yield f"data: {data}\n\n"

                # 返回内容
                data = json.dumps({"type": "content", "value": no_answer})
                yield f"data: {data}\n\n"

                # 返回成本为 0
                data = json.dumps({"type": "cost", "value": 0})
                yield f"data: {data}\n\n"

                yield "data: [DONE]\n\n"
                return

            # 创建消息，先将source入库，状态为generating,
            msg_data = {
                "role": "assistant",
                "content": "",
                "status": "generating",
                "extra_data": {"sources": sources},
                "model": self.llm_api_service.mode
            }
            msg_instance = await self._save_llm_answer(chat_id, msg_data)
            print(f"_save_llm_answer 返回: {msg_instance}")
            print(f"类型: {type(msg_instance)}")

            msg_id = msg_instance.id
            data = json.dumps({
                "type": "sources",
                "value": sources
            })
            # 流式返回sources
            yield f"data: {data}\n\n"

            # 4. 流式调用 LLM，累计内容
            full_content = ""
            async for chunk in self.llm_api_service.send_message_streaming(prompts, self.system_prompts):
                full_content += chunk
                data = json.dumps({
                    "type": "content",
                    "value": chunk
                })
                yield f"data: {data}\n\n"
            # 5. 返回成本
            cost_data = self.llm_api_service.stream_last_cost
            # full_msg 去除空格
            full_content = full_content.strip()
            # 提取 cost 数值（cost_data 是字典 {"cost": 0.0015, "meta": {...}}）
            cost_value = cost_data.get("cost", 0) if isinstance(cost_data, dict) else cost_data
            # 更新msg信息：content，和 status
            await self.messages_service.updateMessagesStatus(msg_id, content=full_content, status="completed", cost=cost_value)

            data = json.dumps({
                "type": "cost",
                "value": cost_value
            })
            yield f"data: {data}\n\n"
        except Exception as e:
            print("msg_id: ", msg_id)
            if msg_id:
                # 更新msg信息：status
                await self.messages_service.updateMessagesStatus(msg_id, status="failed")
            yield f"data: {json.dumps({'type': 'error', 'value': str(e)})}\n\n"
        # 6. 标记结束
        yield f"data: [DONE]\n\n"


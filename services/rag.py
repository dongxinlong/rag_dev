"""
RAG 相关服务接口
"""
import time
import json
import asyncio
import httpx

from fastapi import Depends, Request
from typing import List, Dict, Tuple

from sqlalchemy import select, delete, func

from core.llm import LLMAPIService
from core.embedding import EmbeddingService
from database.session import DatabaseSession
from schemas.rag import RAGQueryRequest, RAGQueryResponse
from models.rag import Document
from config.settings import settings
from config.logging import get_logger
from services.messages import MessagesService
from services.chat import ChatService


logger = get_logger("rag")


class RAGService:

    def __init__(self, llm_api_service: LLMAPIService, db: DatabaseSession, embedding_service: EmbeddingService, request: Request):
        self.llm_api_service = llm_api_service
        self.db = db
        self.embedding_service = embedding_service
        self.messages_service = MessagesService(self.db)
        self.chat_service = ChatService(self.db)
        self.current_exchange_id = 0
        self.system_prompts = """
            你是知识库问答助手。

            回答规则：
            1. 问候语（你好、hi、hello、早上好等）→ 友好回复
            2. 感谢语（谢谢、感谢等）→ 礼貌回复
            3. 闲聊（你是谁、你能做什么等）→ 简单介绍自己
            4. 知识类问题 → 基于参考文档回答
            5. 追问（还有吗、其他的、继续、补充等）→ 基于对话历史回答，只能回答历史中明确提到的内容，不能靠自己猜想去补充信息。
            6. 参考文档为空 + 非追问 → 回答：抱歉，知识库中没有找到相关信息

            重要：区分"追问"和"新问题"
            - 追问：对上一个回答的延续（还有吗、其他的呢、继续说）
            - 新问题：完全不同的知识问题

            禁止：编造、推测、使用自身知识回答知识类问题
        """
        self.system_summary_prompts = """
            你是一个对话助手，需要同时完成两个任务：
            重要规则：
                - 你只负责【重构问题】和【更新摘要】，不负责【回答问题】
                - 无论用户说什么，你都必须严格输出JSON 格式
                - 不要直接回答用户问题，不要输出任何文本内容
            任务一：查询重构（rewritten_question）
            - 如果用户的最新问题是独立的、完整的，直接返回原问题
            - 如果用户的最新问题是追问（如"还有吗"、"继续"、"其他的呢"），结合历史对话，重构为一个完整、独立、可检索的问题
            - 重构后的问题应该能脱离上下文被独立理解

            任务二：摘要更新（summary + key_points）
            - 当前已有摘要（JSON）：
            {old_summary_json}
            - 本次新增对话内容：
            {new_turn_text}
            - 在原有摘要基础上，**增量更新**摘要内容，不要重写全部历史
            - 提取关键信息（实体、计划、意图等）

            输出格式（严格 JSON）：
            {
                "rewritten_question": "重构后的完整问题，如果原问题已经完整则原样返回",
                "summary": "一段连贯、简洁的对话摘要，突出用户意图、关键结论和已完成的动作",
                "keywords": ["核心关键词1", "核心关键词2"],
                "entities": {
                    "person": [],
                    "org": [],
                    "product": [],
                    "location": []
                },
                "plans": [
                    {"name": "核心计划1", "status": "completed", "description": "计划描述"}
                ],
                "user_intents": [
                    "用户本轮的核心意图或目标"
                ],
                "resolved_topics": [
                    "已经明确解决或达成一致的问题"
                ],
                "unresolved_topics": [
                    "仍在讨论、尚未闭环的问题"
                ]
            }
            注意：只输出 JSON，不要输出其他内容。
            要求：
            - summary 控制在 80～150 字，避免流水账；
            - keywords 不超过 8 个，优先保留检索价值高的词；
            - entities 仅填充确实出现的实体，不要编造；
            - 若新对话未改变旧摘要内容，可保持原字段不变；
            - **只输出 JSON，不要有任何解释、注释或 markdown 代码块标记**。
            示例输出：
            {"summary":"用户咨询A产品的退货政策，客服说明需保留包装并在7日内申请。用户随后补充订单号。","keywords":["A产品","退货政策","7日","订单号"],"entities":{"person":[],"org":[],"product":["A产品"],"location":[]},"plans":[],"user_intents":["了解退货流程"],"resolved_topics":["退货时限"],"unresolved_topics":["退货审核结果"]}

        """

    async def _get_messages_for_chatId(self, chat_id: str, exchange_id: Tuple[int, int] = None):
        """通过chat_id获取消息"""
        return await self.messages_service.messages_for_rag(chat_id=chat_id, exchange_id=exchange_id)

    async def _save_user_question(self, chat_id: str, question: str):
        """保存用户问题"""
        data = {
            "chat_id": chat_id,
            "role": "user",
            "content": question,
            "model": self.llm_api_service.mode,
            "status": "completed"
        }
        exchange_id = await self.messages_service.get_exchange_id(chat_id=chat_id)
        exchange_id = exchange_id + 1 if exchange_id is not None else 1
        data["exchange_id"] = exchange_id
        self.current_exchange_id = exchange_id
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
            "status": answer.get("status", "completed"),
            "exchange_id": self.current_exchange_id
        }
       
        return await self.messages_service.createMessages(**data)
    
    async def _rewrite_query(self, chat_id, question: str) -> str:
        """
        用 LLM 将用户问题重构为完整问题，同时更新摘要
        返回: 重构后的完整问题
        """
        # 1. 获取当前对话框中的现有摘要和历史轮数
        summary_info = await self.chat_service.getMaxexchangeIdAndSummary(chat_id=chat_id)
        his_summary = summary_info["summary"]
        his_exchange_id = summary_info["max_exchange_id"]
        his_key_points = summary_info["key_points"]

        # 获取当前最大的 exchange_id（不依赖 self.current_exchange_id，因为它还没设置）
        current_max_exchange_id = await self.chat_service.getMaxexchangeId(chat_id)
        current_exchange_id = current_max_exchange_id + 1

        # 如果历史摘要的最大对话轮数不为0，则收集从轮数到当前轮数之间的历史
        if his_exchange_id != 0:
            exchange_id_range = (his_exchange_id, current_exchange_id)
        else:
            exchange_id_range = None

        # 2. 获取历史消息
        history_messages = await self._get_messages_for_chatId(chat_id=chat_id, exchange_id=exchange_id_range)

        # 3. 构建 new_turn_text（LLM 的 messages 参数）
        new_turn_text = [{"role": msg.role, "content": msg.content} for msg in history_messages] + [{"role": "user", "content": question}]

        # 4. 构建 system_prompt（填入旧摘要）
        system_prompt = self.system_summary_prompts.replace(
            "{old_summary_json}", json.dumps({**his_key_points, "summary": his_summary}, ensure_ascii=False)
        ).replace(
            "{new_turn_text}", ""
        )
        result = None
        max_retries = settings.QUERY_REWRITE_MAX_RETRIES
        for attempt in range(max_retries):
            # 5. 调用 LLM（一次调用同时完成重构 + 摘要更新）
            #    第 2、3 次重试时，prompt 加强约束
            retry_prompt = system_prompt if attempt == 0 else system_prompt + "\n注意：只输出 JSON，不要输出任何其他内容。"
            answer = await self.llm_api_service.send_message(
                messages=new_turn_text,
                system_prompt=retry_prompt
            )
            # 6. 解析 JSON 输出（清理 markdown 代码块）
            raw_content = answer.get("content", "{}")
            logger.info(f"[Query重构] LLM原始返回: {raw_content[:500]}")
            try:
                # 去掉 ```json ... ``` 包裹
                if raw_content.startswith("```"):
                    raw_content = raw_content.split("\n", 1)[1]  # 去掉第一行
                if raw_content.endswith("```"):
                    raw_content = raw_content[:-3]  # 去掉最后的 ```
                raw_content = raw_content.strip()
                logger.info(f"[Query重构] 清理后内容: {raw_content[:500]}")
                result = json.loads(raw_content)
                break  # 解析成功，跳出循环
            except json.JSONDecodeError:
                logger.warning(f"[Query重构] 第{attempt+1}次解析失败，原始内容: {raw_content[:500]}")
        # 降级：如果重试都失败了，用原始问题
        if not result:
            logger.warning(f"[Query重构] {max_retries}次解析均失败，使用原始问题")
            return question

        rewritten_question = result.get("rewritten_question", question)
        new_summary = result.get("summary", his_summary)
        new_key_points = {
            "keywords": result.get("keywords", []),
            "entities": result.get("entities", {}),
            "plans": result.get("plans", []),
            "user_intents": result.get("user_intents", []),
            "resolved_topics": result.get("resolved_topics", []),
            "unresolved_topics": result.get("unresolved_topics", [])
        }

        # 7. 更新数据库中的摘要
        await self.chat_service.updateSummary(
            chat_id=chat_id,
            summary=new_summary,
            exchange_id=current_exchange_id,
            key_points=new_key_points
        )

        logger.info(f"[Query重构] 原问题: {question}, 重构后: {rewritten_question}")
        return rewritten_question

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

    async def _bm25_search(self, question: str, top_k: int = 5):
        """
        BM25 关键词搜索（PostgreSQL 全文检索）

        Args:
            question: 用户查询
            top_k: 返回结果数量

        Returns:
            [(Document, score), ...]
        """
        from sqlalchemy import func

        # 使用 jiebacfg 进行中文分词搜索
        tsquery = func.plainto_tsquery('jiebacfg', question)
        ts_rank = func.ts_rank(Document.search_vector, tsquery).label("rank")

        stmt = select(Document, ts_rank).where(
            Document.search_vector.op('@@')(tsquery)
        ).order_by(ts_rank.desc()).limit(top_k)

        result = await self.db.execute(stmt)
        return result.all()
    
    async def _hybrid_search(self, question: str, top_k: int = 5):
        """
        混合检索
        """
        # 1. 调用 _search 获取向量检索结果
        # 2. 调用 _bm25_search 获取关键词检索结果
        # 并发召回
        vector_results, bm25_results = await asyncio.gather(
            self._search(question=question, top_k=top_k ** 2),
            self._bm25_search(question=question, top_k=top_k ** 2)
        )
        # 3. 合并结果，去重 + (RRF粗排序)
        rrf_res = await self._rrf_fusion(vector_results, bm25_results)
        # 4. 精排
        reranked_results = await self._rerank(question, rrf_res, top_k)
        return reranked_results

    async def _rrf_fusion(self,
            vector_results: List[Dict], 
            bm25_results: List[Dict],
            k: int = 60
    ) -> List[Tuple]:
        """
        RRF (Reciprocal Rank Fusion) 融合
        """
        # 建立文档ID -> RRF分数的映射
        rrf_scores = {}
        doc_map = {}
        # 安全起见，统一排序
        # 1. 向量：按照 distance 升序， 越小越好
        vector_sorted = sorted(vector_results, key=lambda x: x[1], reverse=False)
        # 2. BM25：按照 score 降序， 越大越好
        bm25_sorted = sorted(bm25_results, key=lambda x: x[1], reverse=True)
        """
        由于 RRF，注重的是排名，因此这里用不到 Score
        """
        # 2. 处理向量检索的结果
        for index, (doc, score) in enumerate(vector_sorted):
            doc_id = doc.id
            value = rrf_scores.get(doc_id, 0) + 1.0 / (k + index)
            rrf_scores[doc_id] = value  
            doc_map[doc_id] = doc
        # 3. 处理 BM25 检索的结果
        for index, (doc, score) in enumerate(bm25_sorted):
            doc_id = doc.id
            value = rrf_scores.get(doc_id, 0) + 1.0 / (k + index)
            rrf_scores[doc_id] = value
            doc_map[doc_id] = doc
        # 排序：Value值越大，说明在向量检索中的排名就靠前，BM25检索中的排名也靠前，所以 n路召回的文档，value会更大
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        # 返回融合的结果
        return [(doc_map[doc_id], rrf_scores[doc_id]) for doc_id in sorted_ids]
    
    async def _rerank(self, question: str, results: List[Tuple], top_k: int = 5) -> List[Tuple]:
        """
        重排序
        精排：使用 Cross-Encoder API 对召回结果重新打分（硅基流动）
        """
        if not results:
            return results[:top_k]

        if not settings.RERANK_API_KEY:
            logger.warning("Rerank API Key 未配置，跳过重排序")
            return results[:top_k]

        logger.info("开始重排序（API 模式）")
        try:
            # 提取文档内容列表
            documents = [doc.content for doc, score in results]

            # 调用硅基流动 Rerank API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.RERANK_BASE_URL}/rerank",
                    headers={
                        "Authorization": f"Bearer {settings.RERANK_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": settings.RERANK_MODEL,
                        "query": question,
                        "documents": documents,
                        "top_n": top_k
                    }
                )
                response.raise_for_status()
                data = response.json()

            # 解析返回结果，按 index 映射回原来的 Document 对象
            rerank_results = []
            for item in data.get("results", []):
                idx = item["index"]
                score = item["relevance_score"]
                doc, _ = results[idx]
                rerank_results.append((doc, score))

            logger.info(f"重排序完成，返回 {len(rerank_results)} 条结果")
            return rerank_results

        except Exception as e:
            logger.error(f"Rerank API 调用失败: {str(e)}，返回原始结果")
            return results[:top_k]

    def _count_tokens(self, text: str) -> int:
        """
        估算文本的 Token 数量（粗略估算：中文1字≈2token，英文1词≈1.3token）
        """
        import re
        chinese_chars = len(re.findall(r'[一-鿿]', text))
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        return chinese_chars * 2 + int(english_words * 1.3)
    

    async def _smart_truncate(self, chat_id: str, max_tokens: int) -> tuple[str, list]:
        """
        智能截断历史消息
        1. 获取旧摘要
        2. 获取历史消息
        3. 保留最近 N 条消息（详细）
        4. 对超限的早期消息进行裁剪
        5. 返回 (摘要, 裁剪后的历史消息)

        Returns:
            (summary: str, trimmed_history: list)
        """
        # 1. 获取旧摘要
        summary_info = await self.chat_service.getMaxexchangeIdAndSummary(chat_id=chat_id)
        old_summary = summary_info["summary"] or ""

        # 2. 获取历史消息
        history = await self._get_messages_for_chatId(chat_id=chat_id)

        if not history:
            return old_summary, []

        # 3. 计算旧摘要的 Token
        summary_tokens = self._count_tokens(old_summary)
        recent_count = settings.SMART_TRUNCATE_RECENT_COUNT

        # 4. 如果历史消息很少，直接返回
        if len(history) <= recent_count:
            return old_summary, history

        # 5. 分离：早期消息 + 最近 N 条消息
        early_messages = history[:-recent_count]
        recent_messages = history[-recent_count:]

        # 6. 计算最近 N 条消息的 Token
        recent_tokens = sum(self._count_tokens(msg.content or "") for msg in recent_messages)

        # 7. 如果没超限，直接返回全部
        if summary_tokens + recent_tokens <= max_tokens:
            return old_summary, history

        # 8. 超限了：只保留最近 N 条，早期消息用摘要替代
        logger.info(
            f"[智能截断] Token超限({summary_tokens + recent_tokens}/{max_tokens})，"
            f"截断早期{len(early_messages)}条消息，保留最近{recent_count}条"
        )
        return old_summary, recent_messages

    def _is_greeting(self, question: str) -> bool:
        """判断是否是问候语"""
        greeting_words = [
            "你好", "您好", "hi", "hello", "嗨", "早上好", "下午好", "晚上好",
            "谢谢", "感谢", "再见", "拜拜", "你是谁", "你能做什么", "你是干什么的"
        ]
        question_lower = question.lower().strip()
        return any(word in question_lower for word in greeting_words)

    async def _merge_prompts(self, question: str, documents: list, history: list = None, summary: str = None) -> tuple[list, bool]:
        """
        合并问题和文档为 prompts, 载入历史消息和摘要
        返回: (prompts, should_call_llm)
        """
        prompts = []

        # 1. 加入摘要（补充丢失的历史，由智能截断保留）
        if summary:
            prompts.append({"role": "system", "content": f"对话摘要：{summary}"})

        # 2. 加入历史消息
        if history:
            for msg in history:
                if msg.content:
                    prompts.append({"role": msg.role, "content": msg.content})

        # 判断文档是否为空
        has_documents = bool(documents)
        docs_content = "\n".join([doc.content for doc in documents]) if documents else "无"

        # 判断是否是追问
        follow_up_keywords = ["还有", "其他的", "继续", "补充", "然后呢", "然后", "还有吗", "然后呢", "除此之外"]
        is_follow_up = any(kw in question for kw in follow_up_keywords)

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
            # 无文档时：检查是否是问候语、追问或有历史记录
            is_greeting = self._is_greeting(question)
            has_history = bool(history)

            if is_greeting or is_follow_up or has_history:
                # 问候语、追问或有历史记录：允许调用 LLM
                content = f"【参考文档】: 无\n\n【用户问题】: {question}"
                message = {"role": "user", "content": content}
                prompts.append(message)
                return prompts, True
            else:
                # 无文档 + 无历史 + 非问候 + 非追问：不调用 LLM，直接返回固定文案
                return prompts, False

    async def _prepare_prompts(self, chat_id: str, question: str, history: List, top_k: int):
        """
        准备 Prompts 公共逻辑，对于 rag_query 和 rag_query_stream 复用
        返回: (prompts, sources, should_call_llm)
        """

        # 0. Query 重构（同时更新摘要）
        if settings.QUERY_REWRITE_ENABLED:
            rewritten_question = await self._rewrite_query(chat_id, question)
            logger.info(f"[Query重构] 原问题: {question}, 重构后: {rewritten_question}")
        else:
            rewritten_question = question

        # 1. 用重构后的问题搜索文档（始终搜索，不跳过）
        result = await self._hybrid_search(question=rewritten_question, top_k=top_k)

        # 2. 智能截断历史消息（Token 限制）
        summary, trimmed_history = await self._smart_truncate(chat_id, settings.PROMPT_MAX_HISTORY_TOKENS)

        # 3. 构建Prompts（摘要 + 历史消息 + 文档）
        prompts, should_call_llm = await self._merge_prompts(
            question, [doc for doc, distance in result], trimmed_history, summary
        )
        # 3. 保存用户问题
        await self._save_user_question(chat_id, question)
        # 4. 构造 sources
        # 注意：经过 Rerank 后，distance 实际上是 rerank_score（越大越相关）
        # 而不是原始的余弦距离（越小越相似），所以直接使用
        sources = [
            {
                "id": doc.id,
                "file_name": doc.file_name,
                "content": doc.content,
                "similarity": float(distance)
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
            history = await self._get_messages_for_chatId(chat_id=chat_id)
            # 1. RAG前置流程（_prepare_prompts 内部会做 Query 重构）
            prompts, sources, should_call_llm = await self._prepare_prompts(chat_id, question, history, top_k)

            # 调试：检查 token 数量
            total_chars = sum(len(p.get("content", "")) for p in prompts)
            logger.info(f"[RAG调试] prompts 数量: {len(prompts)}, 总字符数: {total_chars}, sources 数量: {len(sources)}")

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


            # 2. 调用LLM API进行回答
            answer = await self.llm_api_service.send_message(prompts, self.system_prompts)

            # 调试：查看 LLM 返回
            logger.info(f"[RAG调试] LLM 返回: {answer.get('content', '')[:100]}...")

            # 3. 保存 AI 回复
            llm_answer = {
                "content": answer.get("content", ""),
                "tokens_prompt": answer.get("cost", {}).get("meta", {}).get("input_token", 0),
                "tokens_completion": answer.get("cost", {}).get("meta", {}).get("completion_tokens", 0),
                "cache_tokens": answer.get("cost", {}).get("meta", {}).get("cache_input_token", 0),
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
            history = await self._get_messages_for_chatId(chat_id=chat_id)
            # 1. RAG前置流程（_prepare_prompts 内部会做 Query 重构）
            prompts, sources, should_call_llm = await self._prepare_prompts(chat_id, question, history, top_k)

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
            logger.debug(f"_save_llm_answer 返回: {msg_instance}")
            logger.debug(f"类型: {type(msg_instance)}")

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
            meta = cost_data.get("meta", {}) if isinstance(cost_data, dict) else {}
            logger.debug(f"meta: {meta}")
            # 提取token
            tokens_prompt = meta.get("input_token", 0)
            tokens_completion = meta.get("completion_tokens", 0)
            cache_tokens = meta.get("cache_input_token", 0)
            # 更新msg信息：content，和 status
            await self.messages_service.updateMessagesStatus(
                msg_id, content=full_content, status="completed", 
                cost=cost_value, tokens_prompt=tokens_prompt, tokens_completion=tokens_completion, cache_tokens=cache_tokens
                )

            data = json.dumps({
                "type": "cost",
                "value": cost_value
            })
            yield f"data: {data}\n\n"
        except Exception as e:
            logger.error(f"rag_query_stream 失败: {e}, msg_id: {msg_id}")
            if msg_id:
                # 更新msg信息：status
                await self.messages_service.updateMessagesStatus(msg_id, status="failed")
            yield f"data: {json.dumps({'type': 'error', 'value': str(e)})}\n\n"
        # 6. 标记结束
        yield f"data: [DONE]\n\n"


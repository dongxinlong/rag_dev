from pydantic import BaseModel, Field


class RAGQueryRequest(BaseModel):
    """
    RAG 查询请求
    """
    question: str = Field(..., description="用户问题")
    top_k: int = Field(default=3, description="返回最相关的k个结果")
    threshold: float = Field(default=0.5, description="相似度阈值")


class Source(BaseModel):
    """
    引用来源
    """
    content: str = Field(..., description="来源内容")
    similarity: float = Field(..., description="与查询的相似度")
    file_name: str = Field(..., description="文件名")


class RAGQueryResponse(BaseModel):
    """
    RAG 查询响应
    """
    answer: str = Field(..., description="AI 回答")
    sources: list[Source] = Field(default=[], description="引用来源")
    cost: float = Field(default=0.0, description="查询成本")
# 企业级 RAG 知识库系统

基于 FastAPI + PostgreSQL + pgvector 的企业级 RAG（检索增强生成）系统，支持混合检索、Cross-Encoder 精排、Query 重构和智能上下文管理。

## 项目背景

企业积累了大量执行标准、测试方案、操作手册等文档，传统文件管理方式效率低下。本系统通过 RAG 技术，让业务人员用自然语言即可检索知识库，提升信息获取效率。

## 核心功能

- **混合检索**：向量语义检索 + BM25 关键词检索 + RRF 融合排序
- **Cross-Encoder 精排**：基于 bge-reranker-base 模型对粗排结果二次打分
- **Query 重构**：LLM 自动将追问重构成完整可检索问题
- **智能上下文截断**：Token 感知的上下文管理，摘要 + 最近 N 条消息
- **文档自动解析**：支持 PDF / Word / MD / XLSX / CSV，自动分块向量化
- **流式输出**：基于 SSE 的实时流式响应
- **异步任务**：Celery 驱动的文档解析与向量化流水线

## 技术栈

| 组件 | 技术 |
|------|------|
| 框架 | FastAPI（async） |
| 数据库 | PostgreSQL + pgvector + pg_jieba |
| ORM | SQLAlchemy（async） |
| 任务队列 | Celery + Redis |
| 对象存储 | MinIO |
| 文档解析 | MinerU（PDF / Word / XLSX 等转 Markdown） |
| 图片识别 | Ollama 视觉模型（minicpm-v，图片内容描述） |
| LLM | Qwen2.5（Ollama 本地部署） |
| Embedding | BAAI/bge-large-zh-v1.5 |
| Reranker | BAAI/bge-reranker-base |
| 容器化 | Docker Compose |

## 系统架构

```
用户提问
    ↓
Query 重构（LLM）
  └── 旧摘要 + 新问题 → 重构后的问题 + 更新摘要
    ↓
混合检索（asyncio.gather 并发）
  ├── 向量检索（pgvector 余弦距离）
  └── BM25 全文检索（pg_jieba 中文分词）
    ↓
RRF 融合排序（粗排，k=60）
    ↓
Cross-Encoder 重排序（精排）
    ↓
智能截断（Token 限制）
  └── 摘要 + 最近 N 条消息
    ↓
构建 Prompt
    ↓
LLM 生成回答（SSE 流式输出）
```

## 快速开始

### 环境要求

- Python 3.10+
- PostgreSQL 15+（需安装 pgvector 和 pg_jieba 扩展）
- Redis 7+
- MinIO
- MinerU（文档解析，PDF / Word 等转 Markdown，需安装 `mineru` 和 `magic-pdf`）
- Ollama（用于本地部署 LLM 和视觉模型）

### 安装与启动

```bash
# 克隆项目
git clone https://github.com/your-username/ai-study.git
cd ai-study

# 安装依赖（使用 uv）
uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入数据库、Redis、MinIO、Ollama 等配置

# 启动数据库和 MinIO（使用 Docker）
docker-compose up -d postgres redis minio

# 启动 Ollama 并拉取模型
ollama pull qwen2.5        # LLM 模型
ollama pull minicpm-v      # 视觉模型（图片识别）

# 执行数据库迁移
alembic upgrade head

# 启动 FastAPI 服务
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 启动 Celery Worker
celery -A celery_app worker --loglevel=info
```

### Docker 一键部署

```bash
docker-compose up -d
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/rag/query` | RAG 查询（同步） |
| GET | `/api/rag/query/stream` | RAG 查询（流式） |
| POST | `/api/knowledge/upload` | 上传文档 |
| GET | `/api/knowledge/list` | 获取知识库列表 |
| POST | `/api/chat/create` | 创建对话 |
| GET | `/api/chat/list` | 获取对话列表 |

## 项目结构

```
ai-study/
├── alembic/              # 数据库迁移
├── api/                  # 中间件和依赖注入
├── config/               # 配置管理
├── core/                 # 核心模块
│   ├── llm.py           # LLM API 客户端
│   ├── embedding.py     # Embedding 服务
│   └── splitter/        # 文档分块器
├── docker/               # Docker 构建文件
├── models/               # 数据模型
├── routers/              # API 路由
├── schemas/              # 请求/响应模型
├── services/             # 业务逻辑层
│   ├── rag.py           # RAG 核心服务
│   ├── chat.py          # 对话管理
│   ├── messages.py      # 消息管理
│   ├── vectorizer.py    # 向量化服务
│   └── knowledgebase.py # 知识库管理
├── tasks/                # Celery 异步任务
├── utils/                # 工具函数
├── main.py               # 应用入口
├── celery_app.py         # Celery 配置
└── docker-compose.yml    # Docker 编排
```

## 关键设计

### 混合检索 + RRF 融合

向量检索擅长语义理解，BM25 擅长关键词匹配。两者分数尺度不同，直接加权不可行。采用 RRF（Reciprocal Rank Fusion）基于排名融合，规避分数尺度问题。

### Query 重构

用户追问（如"还有吗"）无法直接检索，通过 LLM 将追问重构成完整问题，同时增量更新对话摘要。

### 智能上下文截断

保留最近 N 条消息详细内容，早期对话用摘要替代，既控制 Token 数又不丢失关键信息。

### 容错降级

LLM 输出 JSON 解析失败时自动重试 3 次，全部失败后降级使用原始问题。核心功能支持配置项动态开关。

### 文档解析流程

```
上传文档（PDF / Word / MD / XLSX / CSV）
    ↓
MinerU 解析 → 统一转为 Markdown 格式
    ↓
图片识别（Ollama 视觉模型 minicpm-v 生成图片描述）
    ↓
Markdown 智能分块（四步流程）
  ├── 1. 识别文档层级结构
  ├── 2. 按语义单元递归切分
  ├── 3. 语义完整性检查
  └── 4. 句子边界智能重叠
    ↓
Embedding 向量化（bge-large-zh-v1.5）
    ↓
存入 pgvector
```

## License

MIT

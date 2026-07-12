"""
分块器测试脚本

测试 Markdown 文档的智能分块
"""
import asyncio
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.splitter.chunker import MarkdownChunker, Chunk
from core.minio import MinioClient
from config.settings import settings


# 测试用的 Markdown 内容
TEST_MD_CONTENT = """
# 第一章 保险条款

## 1.1 承保范围

本保险承保以下风险：
1. 火灾造成的损失
2. 爆炸造成的损失
3. 雷击造成的损失

## 1.2 免责条款

但是，以下情况不在承保范围内：
- 战争行为
- 核辐射
- 故意行为

## 1.3 赔偿限额

| 项目 | 限额 |
|------|------|
| 火灾 | 100万 |
| 爆炸 | 50万 |
| 雷击 | 30万 |

# 第二章 理赔流程

## 2.1 报案

发生保险事故后，应在48小时内报案。

## 2.2 理赔材料

需要提供以下材料：
1. 保险单原件
2. 损失清单
3. 相关证明文件
"""


def test_basic_chunking():
    """测试基本分块功能"""
    print("=" * 60)
    print("测试 1：基本分块")
    print("=" * 60)

    chunker = MarkdownChunker(max_chunk_size=200, chunk_overlap=30)
    chunks = chunker.chunk(TEST_MD_CONTENT, document_id="test_doc")

    print(f"原始内容长度: {len(TEST_MD_CONTENT)} 字符")
    print(f"分块数量: {len(chunks)}")
    print()

    for i, chunk in enumerate(chunks):
        print(f"--- Chunk {i + 1} ---")
        print(f"标题: {chunk.heading} (Level {chunk.heading_level})")
        print(f"Token 数: {chunk.token_count}")
        print(f"内容预览: {chunk.content[:100]}...")
        print()


def test_atomic_blocks():
    """测试原子块保护"""
    print("=" * 60)
    print("测试 2：原子块保护（表格、列表）")
    print("=" * 60)

    md_content = """
## 费率表

| 年龄段 | 费率 |
|--------|------|
| 18-25岁 | 0.5% |
| 26-35岁 | 0.8% |
| 36-45岁 | 1.2% |
| 46-55岁 | 1.8% |

这是费率表后面的说明文字。
"""

    chunker = MarkdownChunker(max_chunk_size=100, chunk_overlap=20)
    chunks = chunker.chunk(md_content, document_id="test_table")

    for i, chunk in enumerate(chunks):
        print(f"--- Chunk {i + 1} ---")
        print(f"内容:\n{chunk.content}\n")


def test_completeness_check():
    """测试语义完整性检查"""
    print("=" * 60)
    print("测试 3：语义完整性检查")
    print("=" * 60)

    md_content = """
## 免责条款

以下情况不在承保范围内：
- 战争行为
- 核辐射
- 故意行为
"""

    chunker = MarkdownChunker(max_chunk_size=50, chunk_overlap=10)
    chunks = chunker.chunk(md_content, document_id="test_completeness")

    for i, chunk in enumerate(chunks):
        print(f"--- Chunk {i + 1} ---")
        print(f"内容:\n{chunk.content}\n")


def test_overlap():
    """测试智能重叠"""
    print("=" * 60)
    print("测试 4：智能重叠")
    print("=" * 60)

    md_content = """
这是第一个句子。这是第二个句子。这是第三个句子。
这是第四个句子。这是第五个句子。这是第六个句子。
这是第七个句子。这是第八个句子。这是第九个句子。
"""

    chunker = MarkdownChunker(max_chunk_size=30, chunk_overlap=15)
    chunks = chunker.chunk(md_content, document_id="test_overlap")

    for i, chunk in enumerate(chunks):
        print(f"--- Chunk {i + 1} ---")
        print(f"内容:\n{chunk.content}\n")


def test_html_content():
    """测试 HTML 内容（MinerU 输出格式）"""
    print("=" * 60)
    print("测试 5：HTML 内容兼容性")
    print("=" * 60)

    # MinerU 生成的 HTML 表格
    html_content = """
## 保险条款

<table>
<tr><td>项目</td><td>限额</td></tr>
<tr><td>火灾</td><td>100万</td></tr>
<tr><td>爆炸</td><td>50万</td></tr>
</table>

以下情况不在承保范围内：

<ul>
<li>战争行为</li>
<li>核辐射</li>
<li>故意行为</li>
</ul>
"""

    chunker = MarkdownChunker(max_chunk_size=100, chunk_overlap=20)
    chunks = chunker.chunk(html_content, document_id="test_html")

    for i, chunk in enumerate(chunks):
        print(f"--- Chunk {i + 1} ---")
        print(f"内容:\n{chunk.content}\n")


def test_all_atomic_blocks():
    """测试所有原子块类型"""
    print("=" * 60)
    print("测试 6：所有原子块类型")
    print("=" * 60)

    test_cases = {
        "HTML 表格": """
<table>
<tr><td>A</td><td>B</td></tr>
<tr><td>1</td><td>2</td></tr>
</table>
""",
        "Markdown 表格": """
| A | B |
|---|---|
| 1 | 2 |
""",
        "HTML 列表": """
<ul>
<li>项目1</li>
<li>项目2</li>
</ul>
""",
        "Markdown 列表": """
- 项目1
- 项目2
""",
        "HTML 代码块": """
<pre>
code here
</pre>
""",
        "Markdown 代码块": """
```
code here
```
""",
        "HTML 图片": """
<img src="image.png" alt="图片">
""",
        "HTML 引用": """
<blockquote>这是一段引用</blockquote>
""",
        "Markdown 引用": """
> 这是一段引用
""",
    }

    chunker = MarkdownChunker(max_chunk_size=50, chunk_overlap=10)

    for name, content in test_cases.items():
        print(f"\n--- {name} ---")
        # 直接测试 _is_atomic_block
        is_atomic = chunker._is_atomic_block(content.strip())
        print(f"  _is_atomic_block: {is_atomic}")
        # 测试分块
        chunks = chunker.chunk(content, document_id="test_atomic")
        for i, chunk in enumerate(chunks):
            print(f"  Chunk {i + 1}: {chunk.content[:30].replace(chr(10), ' ')}...")


if __name__ == "__main__":
    test_basic_chunking()
    print("\n" + "=" * 60 + "\n")
    test_atomic_blocks()
    print("\n" + "=" * 60 + "\n")
    test_completeness_check()
    print("\n" + "=" * 60 + "\n")
    test_overlap()
    print("\n" + "=" * 60 + "\n")
    test_html_content()
    print("\n" + "=" * 60 + "\n")
    test_all_atomic_blocks()

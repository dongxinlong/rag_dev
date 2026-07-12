"""
真实文档分块测试

从本地文件读取 MD，测试分块效果
"""
import asyncio
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.splitter.chunker import MarkdownChunker


async def test_real_document():
    """测试真实文档分块"""
    print("=" * 60)
    print("真实文档分块测试")
    print("=" * 60)

    # 读取本地文件
    file_path = r"C:\Users\xiaodong\Downloads\result (4).md"

    print(f"\n1. 读取文件: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    print(f"   文件大小: {len(content)} 字符")

    # 分析文档结构
    print(f"\n2. 分析文档结构:")
    analyze_structure(content)

    # 测试分块
    print(f"\n3. 测试分块:")
    chunker = MarkdownChunker(max_chunk_size=500, chunk_overlap=100)
    chunks = chunker.chunk(content, document_id="test_real", document_name="result.md")

    print(f"   分块数量: {len(chunks)}")

    if chunks:
        # 显示前 5 个 chunk
        print(f"\n4. 前 5 个 chunk:")
        for i, chunk in enumerate(chunks[:5]):
            print(f"\n--- Chunk {i + 1} ---")
            print(f"标题: {chunk.heading} (Level {chunk.heading_level})")
            print(f"Token 数: {chunk.token_count}")
            print(f"策略: {chunk.metadata.get('chunk_strategy')}")
            print(f"内容预览: {chunk.content[:150].replace(chr(10), ' ')}...")

        # 统计信息
        print(f"\n5. 统计信息:")
        print(f"   总 chunk 数: {len(chunks)}")
        print(f"   平均 token 数: {sum(c.token_count for c in chunks) // len(chunks)}")
        print(f"   最大 token 数: {max(c.token_count for c in chunks)}")
        print(f"   最小 token 数: {min(c.token_count for c in chunks)}")

        # 检查原子块
        atomic_chunks = [c for c in chunks if c.metadata.get('is_atomic')]
        print(f"   原子块数量: {len(atomic_chunks)}")

        # 检查标题层级
        heading_chunks = {}
        for chunk in chunks:
            level = chunk.heading_level
            if level not in heading_chunks:
                heading_chunks[level] = 0
            heading_chunks[level] += 1
        print(f"   标题层级分布: {heading_chunks}")


def analyze_structure(content):
    """分析文档结构"""
    import re

    # 统计标题
    md_headings = re.findall(r'^(#{1,6})\s+(.+)$', content, re.MULTILINE)
    html_headings = re.findall(r'<h([1-6])[^>]*>(.+?)</h\1>', content, re.IGNORECASE)

    print(f"   Markdown 标题: {len(md_headings)} 个")
    for level, heading in md_headings[:5]:
        print(f"     {'#' * len(level)} {heading[:30]}")

    print(f"   HTML 标题: {len(html_headings)} 个")

    # 统计表格
    md_tables = len(re.findall(r'\|.+\|', content))
    html_tables = len(re.findall(r'<table[\s>]', content, re.IGNORECASE))
    print(f"   Markdown 表格: {md_tables} 个")
    print(f"   HTML 表格: {html_tables} 个")

    # 统计列表
    md_lists = len(re.findall(r'^(\d+\.|[-*])\s', content, re.MULTILINE))
    html_lists = len(re.findall(r'<(ul|ol)[\s>]', content, re.IGNORECASE))
    print(f"   Markdown 列表: {md_lists} 个")
    print(f"   HTML 列表: {html_lists} 个")

    # 统计代码块
    code_blocks = len(re.findall(r'```', content))
    print(f"   代码块: {code_blocks // 2} 个")

    # 统计图片
    md_images = len(re.findall(r'!\[.*?\]\(.*?\)', content))
    html_images = len(re.findall(r'<img[\s>]', content, re.IGNORECASE))
    print(f"   Markdown 图片: {md_images} 个")
    print(f"   HTML 图片: {html_images} 个")

    # 统计引用
    md_quotes = len(re.findall(r'^>', content, re.MULTILINE))
    html_quotes = len(re.findall(r'<blockquote[\s>]', content, re.IGNORECASE))
    print(f"   Markdown 引用: {md_quotes} 个")
    print(f"   HTML 引用: {html_quotes} 个")


if __name__ == "__main__":
    asyncio.run(test_real_document())

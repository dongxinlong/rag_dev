"""
Markdown 文档智能分块器

============================================================
实现四步流程，保证 RAG 检索召回率和生成质量
============================================================

【第一步：识别文档层级结构】
- 解析 Markdown 标题（# ## ### ####）
- 构建文档层级树
- 识别章节边界

【第二步：按语义单元递归切分】
- 如果章节 token ≤ max_chunk_size，直接作为一个 chunk
- 如果有子章节，按子章节递归拆分
- 如果没有子章节，按段落累计
- 如果单段超限，按句子边界切分
- 特殊结构（表格、代码块、列表）作为原子块，不拆分

【第三步：语义完整性检查】
- 检查相邻 chunk 是否被错误切开
- 冒号/分号结尾 → 可能承接列表，合并
- 列表编号开头 → 与前导句合并
- 转折词开头 → 与前一句合并

【第四步：智能重叠（句子边界）】
- 找切片末尾最近的句号位置
- 从句子完整起点开始重叠
- 保证 overlap 部分是完整句子

【特殊元素处理】
- 表格：整块保留，不拆分
- 代码块：整块保留，不拆分
- 列表：前导句 + 列表项合并
- 图片：已用视觉模型转为文字，直接入库

【配置参数】
- max_chunk_size: 单 chunk 最大 token 数（默认 1024）
- chunk_overlap: 重叠 token 数（默认 150）

============================================================
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional
from config.settings import settings
from config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Chunk:
    """
    文档块数据结构

    包含完整的元数据信息，支持回溯到原始文档
    """
    # ============ 内容 ============
    content: str                    # 文本内容

    # ============ 位置信息 ============
    index: int                      # chunk 在文档中的序号
    heading: str = ""               # 所属标题文本
    heading_level: int = 0          # 标题级别（1-6，0 表示无标题）

    # ============ 统计信息 ============
    token_count: int = 0            # token 数量估算
    char_count: int = 0             # 字符数量

    # ============ 元数据（支持回溯） ============
    metadata: dict = field(default_factory=lambda: {
        "document_id": None,        # 文档 ID
        "document_name": None,      # 文档名称
        "chunk_strategy": None,     # 分块策略（paragraph/sentence/atomic）
        "parent_heading": None,     # 父级标题路径
        "is_atomic": False,         # 是否是原子块（表格/代码块/列表）
        "heading_path": [],         # 完整标题路径 ["第一章", "1.1 承保范围"]
    })


class MarkdownChunker:
    """
    Markdown 文档智能分块器

    实现四步流程：
    1. 识别文档层级结构
    2. 按语义单元递归切分
    3. 语义完整性检查
    4. 智能重叠（句子边界）
    """

    def __init__(self, max_chunk_size: int = None, chunk_overlap: int = None):
        """
        初始化分块器

        Args:
            max_chunk_size: 单 chunk 最大 token 数（默认 1024）
            chunk_overlap: 重叠 token 数（默认 150）
        """
        self.max_chunk_size = max_chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.min_chunk_size = settings.CHUNK_MIN_SIZE
        self.transition_words = settings.CHUNK_TRANSITION_WORDS
        self.sentence_pattern = settings.CHUNK_SENTENCE_PATTERNS

    def chunk(self, content: str, document_id: str = None, document_name: str = None) -> List[Chunk]:
        """
        主入口：将 Markdown 文档分块

        Args:
            content: Markdown 内容
            document_id: 文档 ID（用于元数据回溯）
            document_name: 文档名称（用于元数据回溯）

        Returns:
            Chunk 列表，每个 chunk 包含完整的元数据
        """
        logger.info(f"开始分块，文档: {document_name}, 内容长度: {len(content)} 字符")

        # 第一步：识别文档层级结构
        sections = self._parse_structure(content)
        logger.info(f"识别到 {len(sections)} 个顶层章节")

        # 第二步：递归切分
        raw_chunks = []
        for section in sections:
            section_chunks = self._recursive_split(section, heading_path=[section["heading"]])
            raw_chunks.extend(section_chunks)
        logger.info(f"切分完成，共 {len(raw_chunks)} 个原始 chunk")

        # 第三步：语义完整性检查
        checked_chunks = self._check_completeness(raw_chunks)
        logger.info(f"完整性检查后: {len(checked_chunks)} 个 chunk")

        # 第四步：智能重叠
        final_chunks = self._apply_overlap(checked_chunks)
        logger.info(f"最终: {len(final_chunks)} 个 chunk")

        # 添加序号和元数据
        for i, chunk in enumerate(final_chunks):
            chunk.index = i
            chunk.char_count = len(chunk.content)
            chunk.token_count = self._count_tokens(chunk.content)
            chunk.metadata["document_id"] = document_id
            chunk.metadata["document_name"] = document_name

        return final_chunks

    # ============ 第一步：识别文档层级结构 ============

    def _parse_structure(self, content: str) -> List[dict]:
        """
        解析 Markdown 结构，识别标题层级

        支持：
        - Markdown 标题：# ## ### ####
        - HTML 标题：<h1> <h2> <h3> 等

        返回章节列表，每个章节包含：
        - level: 标题级别（1-6）
        - heading: 标题文本
        - content: 章节内容
        - children: 子章节列表
        """
        lines = content.split("\n")
        sections = []
        current_section = {"level": 0, "heading": "", "content": "", "children": []}

        for line in lines:
            heading_level = 0
            heading_text = ""

            # 检测 Markdown 标题（# ## ### #### 等）
            md_heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if md_heading_match:
                heading_level = len(md_heading_match.group(1))
                heading_text = md_heading_match.group(2).strip()

            # 检测 HTML 标题（<h1> <h2> <h3> 等）
            if not heading_level:
                html_heading_match = re.match(r'<h([1-6])[^>]*>(.+?)</h\1>', line, re.IGNORECASE)
                if html_heading_match:
                    heading_level = int(html_heading_match.group(1))
                    heading_text = re.sub(r'<[^>]+>', '', html_heading_match.group(2)).strip()

            if heading_level > 0:
                # 保存当前章节内容
                if current_section["content"].strip():
                    sections.append(current_section)

                # 新建章节
                current_section = {
                    "level": heading_level,
                    "heading": heading_text,
                    "content": "",
                    "children": []
                }
            else:
                # 普通内容，追加到当前章节
                current_section["content"] += line + "\n"

        # 保存最后一个章节
        if current_section["content"].strip():
            sections.append(current_section)

        return sections

    # ============ 第二步：递归切分 ============

    def _recursive_split(self, section: dict, heading_path: List[str] = None) -> List[Chunk]:
        """
        递归切分章节

        规则：
        1. token 数 ≤ max_chunk_size → 直接作为一个 chunk
        2. 有子章节 → 按子章节拆分，递归处理
        3. 无子章节 → 按段落累计
        4. 单段超限 → 按句子边界切分
        """
        if heading_path is None:
            heading_path = []

        content = section["content"].strip()
        if not content:
            return []

        token_count = self._count_tokens(content)

        # 规则 1：如果够小，直接作为一个 chunk
        if token_count <= self.max_chunk_size:
            # 检查是否是原子块
            is_atomic = self._is_atomic_block(content)
            return [Chunk(
                content=content,
                index=0,
                heading=section["heading"],
                heading_level=section["level"],
                metadata={
                    "heading_path": heading_path,
                    "chunk_strategy": "atomic" if is_atomic else "section",
                    "is_atomic": is_atomic
                }
            )]

        # 规则 2：如果有子章节，按子章节拆分
        if section["children"]:
            chunks = []
            for child in section["children"]:
                child_path = heading_path + [child["heading"]]
                chunks.extend(self._recursive_split(child, heading_path=child_path))
            return chunks

        # 规则 3：按段落累计
        return self._split_by_paragraphs(content, section["heading"], section["level"], heading_path)

    def _split_by_paragraphs(self, content: str, heading: str, heading_level: int, heading_path: List[str]) -> List[Chunk]:
        """按段落切分，遇到原子块单独处理"""
        # 先提取所有原子块（表格、代码块等），避免被错误分割
        atomic_blocks = []
        protected_content = content

        # 提取 HTML 表格（支持嵌套表格）
        # 使用计数法处理嵌套：从 <table> 开始，计数到对应的 </table>
        table_positions = []
        i = 0
        while i < len(protected_content):
            # 找到 <table 开头
            table_start = protected_content.lower().find('<table', i)
            if table_start == -1:
                break

            # 计数嵌套的 table 标签
            depth = 0
            j = table_start
            while j < len(protected_content):
                # 找下一个 <table 或 </table>
                next_open = protected_content.lower().find('<table', j)
                next_close = protected_content.lower().find('</table>', j)

                if next_open == -1 and next_close == -1:
                    break

                if next_open != -1 and (next_close == -1 or next_open < next_close):
                    depth += 1
                    j = next_open + 6
                else:
                    depth -= 1
                    j = next_close + 8
                    if depth == 0:
                        # 找到匹配的闭合标签
                        table_end = j
                        table_content = protected_content[table_start:table_end]
                        table_positions.append((table_start, table_end, table_content))
                        i = table_end
                        break

        # 从后往前替换，避免位置偏移
        for idx, (start, end, table_content) in enumerate(reversed(table_positions)):
            placeholder = f"__ATOMIC_BLOCK_{len(table_positions) - 1 - idx}__"
            atomic_blocks.append((placeholder, table_content))
            protected_content = protected_content[:start] + placeholder + protected_content[end:]

        atomic_blocks.reverse()  # 恢复顺序

        # 提取 Markdown 表格
        md_table_pattern = r'(?:^|\n)(\|.+\|[ \t]*\n)+'
        md_tables = re.findall(md_table_pattern, protected_content)
        for i, table in enumerate(md_tables):
            placeholder = f"__ATOMIC_BLOCK_{len(atomic_blocks) + i}__"
            atomic_blocks.append((placeholder, table))
            protected_content = protected_content.replace(table, placeholder, 1)

        # 现在按段落分割（不会破坏表格）
        paragraphs = re.split(r'\n\s*\n|</p>\s*<p[\s>]', protected_content)
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # 检查是否是原子块（表格、代码块、列表）
            if self._is_atomic_block(para):
                # 先保存当前积累的内容
                if current_chunk.strip():
                    chunks.append(Chunk(
                        content=current_chunk.strip(),
                        index=0,
                        heading=heading,
                        heading_level=heading_level,
                        metadata={"heading_path": heading_path, "chunk_strategy": "paragraph"}
                    ))
                    current_chunk = ""
                # 原子块：检查是否需要拆分
                if self._count_tokens(para) > self.max_chunk_size:
                    # 大表格/大代码块：尝试拆分
                    if self._is_table(para):
                        chunks.extend(self._split_large_table(para, heading, heading_level, heading_path))
                    else:
                        # 其他原子块不拆分
                        chunks.append(Chunk(
                            content=para,
                            index=0,
                            heading=heading,
                            heading_level=heading_level,
                            metadata={"heading_path": heading_path, "chunk_strategy": "atomic", "is_atomic": True}
                        ))
                else:
                    # 小原子块：直接作为一个 chunk
                    chunks.append(Chunk(
                        content=para,
                        index=0,
                        heading=heading,
                        heading_level=heading_level,
                        metadata={"heading_path": heading_path, "chunk_strategy": "atomic", "is_atomic": True}
                    ))
                continue

            # 普通段落：尝试累计
            test_content = current_chunk + "\n\n" + para if current_chunk else para
            if self._count_tokens(test_content) <= self.max_chunk_size:
                current_chunk = test_content
            else:
                # 保存当前积累
                if current_chunk.strip():
                    chunks.append(Chunk(
                        content=current_chunk.strip(),
                        index=0,
                        heading=heading,
                        heading_level=heading_level,
                        metadata={"heading_path": heading_path, "chunk_strategy": "paragraph"}
                    ))
                # 检查单段是否超限
                if self._count_tokens(para) > self.max_chunk_size:
                    # 规则 4：按句子切分
                    chunks.extend(self._split_by_sentences(para, heading, heading_level, heading_path))
                else:
                    current_chunk = para

        # 保存最后积累的内容
        if current_chunk.strip():
            chunks.append(Chunk(
                content=current_chunk.strip(),
                index=0,
                heading=heading,
                heading_level=heading_level,
                metadata={"heading_path": heading_path, "chunk_strategy": "paragraph"}
            ))

        # 还原原子块占位符
        for placeholder, original_content in atomic_blocks:
            for chunk in chunks:
                if placeholder in chunk.content:
                    chunk.content = chunk.content.replace(placeholder, original_content)

        return chunks

    def _is_table(self, content: str) -> bool:
        """判断是否是表格"""
        content_stripped = content.strip()
        # Markdown 表格
        if re.search(r'\|.+\|', content_stripped):
            return True
        # HTML 表格
        if re.search(r'<table[\s>]', content_stripped, re.IGNORECASE):
            return True
        return False

    def _split_large_table(self, table_content: str, heading: str, heading_level: int, heading_path: List[str]) -> List[Chunk]:
        """
        拆分大表格，保留表头

        策略：
        1. 提取表头（第一行）
        2. 按行分组，每组不超过 max_chunk_size
        3. 每组前面加上表头
        """
        lines = table_content.strip().split("\n")
        if len(lines) < 2:
            return [Chunk(
                content=table_content,
                index=0,
                heading=heading,
                heading_level=heading_level,
                metadata={"heading_path": heading_path, "chunk_strategy": "table_split", "is_atomic": True}
            )]

        # 提取表头（第一行）
        header = lines[0]
        # 提取分隔行（第二行，包含 ---）
        separator = lines[1] if len(lines) > 1 and "---" in lines[1] else None
        # 数据行
        data_lines = lines[2:] if separator else lines[1:]

        if not data_lines:
            return [Chunk(
                content=table_content,
                index=0,
                heading=heading,
                heading_level=heading_level,
                metadata={"heading_path": heading_path, "chunk_strategy": "table_split", "is_atomic": True}
            )]

        # 按行分组
        chunks = []
        current_group = []

        for line in data_lines:
            test_group = current_group + [line]
            test_content = header + "\n"
            if separator:
                test_content += separator + "\n"
            test_content += "\n".join(test_group)

            if self._count_tokens(test_content) <= self.max_chunk_size:
                current_group.append(line)
            else:
                # 保存当前组
                if current_group:
                    group_table = header + "\n"
                    if separator:
                        group_table += separator + "\n"
                    group_table += "\n".join(current_group)
                    chunks.append(Chunk(
                        content=group_table,
                        index=0,
                        heading=heading,
                        heading_level=heading_level,
                        metadata={"heading_path": heading_path, "chunk_strategy": "table_split", "is_atomic": True}
                    ))
                current_group = [line]

        # 保存最后一组
        if current_group:
            group_table = header + "\n"
            if separator:
                group_table += separator + "\n"
            group_table += "\n".join(current_group)
            chunks.append(Chunk(
                content=group_table,
                index=0,
                heading=heading,
                heading_level=heading_level,
                metadata={"heading_path": heading_path, "chunk_strategy": "table_split", "is_atomic": True}
            ))

        return chunks

    def _split_by_sentences(self, content: str, heading: str, heading_level: int, heading_path: List[str]) -> List[Chunk]:
        """按句子边界切分"""
        # 中英文句子分割
        sentences = re.split(f'(?<={self.sentence_pattern})\\s*', content)
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            test_content = current_chunk + " " + sentence if current_chunk else sentence
            if self._count_tokens(test_content) <= self.max_chunk_size:
                current_chunk = test_content
            else:
                if current_chunk.strip():
                    chunks.append(Chunk(
                        content=current_chunk.strip(),
                        index=0,
                        heading=heading,
                        heading_level=heading_level,
                        metadata={"heading_path": heading_path, "chunk_strategy": "sentence"}
                    ))
                current_chunk = sentence

        if current_chunk.strip():
            chunks.append(Chunk(
                content=current_chunk.strip(),
                index=0,
                heading=heading,
                heading_level=heading_level,
                metadata={"heading_path": heading_path, "chunk_strategy": "sentence"}
            ))

        return chunks

    def _is_atomic_block(self, content: str) -> bool:
        """判断是否是原子块（不可拆分）"""
        content_stripped = content.strip()
        lines = content_stripped.split("\n")

        # ============ 占位符 ============
        # 检测原子块占位符
        if re.match(r'^__ATOMIC_BLOCK_\d+__$', content_stripped):
            return True

        # ============ 表格 ============
        # Markdown 表格：包含 | 分隔符
        if any("|" in line for line in lines):
            return True
        # HTML 表格：<table> 标签
        if re.search(r'<table[\s>]', content_stripped, re.IGNORECASE):
            return True

        # ============ 代码块 ============
        # Markdown 代码块：``` 包裹
        if content_stripped.startswith("```") or content_stripped.endswith("```"):
            return True
        # HTML 代码块：<pre> 或 <code> 标签
        if re.search(r'<(pre|code)[\s>]', content_stripped, re.IGNORECASE):
            return True

        # ============ 列表 ============
        # Markdown 列表：以数字或 - * 开头
        if re.match(r'^(\d+\.|[-*])\s', content_stripped):
            return True
        # HTML 列表：<ul> 或 <ol> 标签
        if re.search(r'<(ul|ol)[\s>]', content_stripped, re.IGNORECASE):
            return True

        # ============ 图片 ============
        # HTML 图片：<img> 标签
        if re.search(r'<img[\s>]', content_stripped, re.IGNORECASE):
            return True

        # ============ 链接块 ============
        # 如果整个内容就是一个链接，不拆分
        if re.match(r'^\[.+\]\(.+\)$', content_stripped):
            return True
        # HTML 链接块：<a> 标签包裹整个内容
        if re.match(r'^<a[\s>].+</a>$', content_stripped, re.IGNORECASE | re.DOTALL):
            return True

        # ============ 引用块 ============
        # Markdown 引用：> 开头
        if re.match(r'^>', content_stripped):
            return True
        # HTML 引用：<blockquote> 标签
        if re.search(r'<blockquote[\s>]', content_stripped, re.IGNORECASE):
            return True

        # ============ 段落 ============
        # HTML 段落：<p> 标签（如果整个内容就是一个段落）
        if re.match(r'^<p[\s>].+</p>$', content_stripped, re.IGNORECASE | re.DOTALL):
            return True

        return False

    # ============ 第三步：语义完整性检查 ============

    def _check_completeness(self, chunks: List[Chunk]) -> List[Chunk]:
        """
        检查相邻 chunk 是否被错误切开

        场景：
        1. 冒号/分号结尾 → 后面大概率承接列表，合并
        2. 列表编号开头 → 与前导句合并
        3. 转折词开头 → 与前一句合并
        """
        if len(chunks) <= 1:
            return chunks

        merged = []
        i = 0

        while i < len(chunks):
            current = chunks[i]

            # 检查是否需要与下一个合并
            if i + 1 < len(chunks):
                next_chunk = chunks[i + 1]
                should_merge = self._should_merge(current.content, next_chunk.content)

                if should_merge:
                    # 合并两个 chunk
                    merged_content = current.content + "\n" + next_chunk.content
                    merged.append(Chunk(
                        content=merged_content,
                        index=0,
                        heading=current.heading,
                        heading_level=current.heading_level,
                        metadata={
                            "heading_path": current.metadata.get("heading_path", []),
                            "chunk_strategy": "merged"
                        }
                    ))
                    i += 2
                    continue

            merged.append(current)
            i += 1

        return merged

    def _should_merge(self, current_end: str, next_start: str) -> bool:
        """判断两个 chunk 是否应该合并"""
        # 场景1：当前 chunk 以冒号/分号结尾
        if re.search(r'[：:；;]\s*$', current_end.strip()):
            return True

        # 场景2：下一个 chunk 以列表编号开头
        if re.match(r'^\s*(\d+\.|[-*])\s', next_start):
            return True

        # 场景3：下一个 chunk 以转折词开头
        for word in self.transition_words:
            if next_start.strip().startswith(word):
                return True

        return False

    # ============ 第四步：智能重叠 ============

    def _apply_overlap(self, chunks: List[Chunk]) -> List[Chunk]:
        """
        应用智能重叠（句子边界）

        规则：
        1. 找切片末尾最近的句号位置
        2. 从句子完整起点开始重叠
        3. 保证 overlap 部分是完整句子
        """
        if len(chunks) <= 1 or self.chunk_overlap <= 0:
            return chunks

        overlapped = [chunks[0]]

        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            current_chunk = chunks[i]

            # 从上一个 chunk 的末尾提取重叠内容
            overlap_text = self._extract_overlap(prev_chunk.content)

            if overlap_text:
                # 在当前 chunk 开头添加重叠
                new_content = overlap_text + "\n" + current_chunk.content
                overlapped.append(Chunk(
                    content=new_content,
                    index=current_chunk.index,
                    heading=current_chunk.heading,
                    heading_level=current_chunk.heading_level,
                    metadata=current_chunk.metadata.copy()
                ))
            else:
                overlapped.append(current_chunk)

        return overlapped

    def _extract_overlap(self, text: str) -> str:
        """从文本末尾提取重叠内容（句子边界）"""
        # 找所有句子边界位置
        sentence_ends = [m.end() for m in re.finditer(self.sentence_pattern, text)]

        if not sentence_ends:
            return ""

        # 重叠字符数估算（1 token ≈ 2 字符）
        overlap_chars = self.chunk_overlap * 2

        # 从后往前找，找到合适的重叠起点
        for end_pos in reversed(sentence_ends):
            remaining = len(text) - end_pos
            if remaining >= overlap_chars:
                return text[end_pos:].strip()

        # 如果找不到合适的点，返回最后几个句子
        return text[-overlap_chars:].strip() if len(text) > overlap_chars else text

    # ============ 工具方法 ============

    def _count_tokens(self, text: str) -> int:
        """
        估算 token 数量

        简单估算：中文 1 字 ≈ 1 token，英文 1 词 ≈ 1 token
        """
        # 中文字符数
        chinese_chars = len(re.findall(r'[一-鿿]', text))
        # 英文单词数
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        # 数字和标点
        other = len(re.findall(r'[\d\W]', text)) // 2

        return chinese_chars + english_words + other


# 全局实例
chunker = MarkdownChunker()

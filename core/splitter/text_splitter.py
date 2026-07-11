"""
文本切分逻辑
"""

import re
from typing import List, Dict

from .base import BaseSplitter


class TextSplitter(BaseSplitter):
    
    def split(self, file_path: str) -> List[Dict]:
        text = self._read_text(file_path)
        metadata = self._default_metadata(file_path)
        chunks = self.split_text(text)
        for chunk in chunks:
            chunk.update(metadata)
        return chunks

    def split_text(
        self,
        text: str,
        chunk_size: int = 80,
        overlap_sentences: int = 2,
    ) -> List[Dict]:
        """
        按段落 + 句子切分文本
        - 不跨段落
        - 不拆句子
        - overlap 为完整句子
        """
        sentence_endings = r'(?<=[。！？\.!?])'
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        chunks = []
        chunk_index = 0

        for para_idx, paragraph in enumerate(paragraphs):
            # 段落内按句子切分
            sentences = [
                s.strip() for s in re.split(sentence_endings, paragraph) if s.strip()
            ]

            current_sentences = []
            current_len = 0

            i = 0
            while i < len(sentences):
                sent = sentences[i]

                # 单句超长，直接成块（避免死循环）
                if len(sent) > chunk_size and not current_sentences:
                    chunks.append({
                        "chunk_index": chunk_index,
                        "paragraph_index": para_idx,
                        "content": sent,
                        "length": len(sent),
                        "sentences": 1
                    })
                    chunk_index += 1
                    i += 1
                    continue

                # 尝试加入句子
                if current_len + len(sent) <= chunk_size:
                    current_sentences.append(sent)
                    current_len += len(sent)
                    i += 1
                else:
                    # 1. 保存当前 chunk
                    chunks.append({
                        "chunk_index": chunk_index,
                        "paragraph_index": para_idx,
                        "content": "".join(current_sentences),
                        "length": current_len,
                        "sentences": len(current_sentences)
                    })
                    chunk_index += 1

                    # 2. 取 overlap 句子
                    overlap_count = min(overlap_sentences, len(current_sentences))
                    current_sentences = current_sentences[-overlap_count:]

                    # 3. ✅ 关键：把当前 sent 加入新 chunk
                    current_sentences.append(sent)
                    current_len = sum(len(s) for s in current_sentences)
                    i += 1

            # 段落剩余部分
            if current_sentences:
                chunks.append({
                    "chunk_index": chunk_index,
                    "paragraph_index": para_idx,
                    "content": "".join(current_sentences),
                    "length": current_len,
                    "sentences": len(current_sentences),
                    
                })
                chunk_index += 1

        return chunks

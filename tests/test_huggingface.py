# 测试能否正常加载模型
from sentence_transformers import CrossEncoder

model = CrossEncoder('BAAI/bge-reranker-base')
score = model.predict([("什么是人工智能", "人工智能是计算机科学的一个分支")])
print(score)

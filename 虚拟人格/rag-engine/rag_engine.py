import json
import numpy as np
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import faiss
import os

class RAGEngine:
    def __init__(self, model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2'):
        """初始化RAG引擎"""
        self.model = SentenceTransformer(model_name)
        self.dimension = 384  # sentence-transformers模型的维度
        self.index = None
        self.conversations = []
        self.metadata = []

    def load_conversations(self, jsonl_file: str):
        """加载清洗后的对话数据"""
        conversations = []
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    conversations.append(json.loads(line.strip()))

        self.conversations = conversations
        print(f"加载了 {len(conversations)} 条对话记录")

    def build_vector_database(self):
        """构建向量数据库"""
        if not self.conversations:
            raise ValueError("没有对话数据，请先加载数据")

        # 提取问题和回答文本
        texts = []
        metadata = []

        for i, conv in enumerate(self.conversations):
            # 将问题和回答组合成完整文本
            full_text = f"问题：{conv['prompt']} 回答：{conv['completion']}"
            texts.append(full_text)
            metadata.append({
                'id': i,
                'prompt': conv['prompt'],
                'completion': conv['completion']
            })

        # 生成向量嵌入
        print("正在生成文本向量...")
        embeddings = self.model.encode(texts, show_progress_bar=True)

        # 创建FAISS索引
        self.index = faiss.IndexFlatL2(self.dimension)
        self.index.add(embeddings.astype('float32'))
        self.metadata = metadata

        print(f"向量数据库构建完成，共 {len(texts)} 条记录")

    def save_index(self, index_path: str, metadata_path: str):
        """保存向量索引和元数据"""
        if self.index is None:
            raise ValueError("索引未构建，请先构建向量数据库")

        # 保存FAISS索引
        faiss.write_index(self.index, index_path)

        # 保存元数据
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

        print(f"索引已保存到 {index_path}")
        print(f"元数据已保存到 {metadata_path}")

    def load_index(self, index_path: str, metadata_path: str):
        """加载向量索引和元数据"""
        if not os.path.exists(index_path) or not os.path.exists(metadata_path):
            raise FileNotFoundError("索引文件或元数据文件不存在")

        # 加载FAISS索引
        self.index = faiss.read_index(index_path)

        # 加载元数据
        with open(metadata_path, 'r', encoding='utf-8') as f:
            self.metadata = json.load(f)

        print(f"索引和元数据加载完成，共 {len(self.metadata)} 条记录")

    def search_similar(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索相似对话"""
        if self.index is None:
            raise ValueError("索引未构建，请先构建或加载向量数据库")

        # 生成查询向量
        query_vector = self.model.encode([query])

        # 搜索最相似的记录
        distances, indices = self.index.search(query_vector.astype('float32'), top_k)

        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx != -1:  # 有效的搜索结果
                metadata = self.metadata[idx]
                results.append({
                    'prompt': metadata['prompt'],
                    'completion': metadata['completion'],
                    'similarity': float(1 / (1 + distance))  # 转换为相似度分数
                })

        return results

    def build_enhanced_prompt(self, user_query: str, target_persona: str = "李四") -> str:
        """构建增强的提示词"""
        # 搜索相关记忆
        similar_memories = self.search_similar(user_query, top_k=3)

        # 构建系统提示词
        system_prompt = f"""你现在扮演{target_persona}，一个真实的人。请根据以下记忆片段和对话风格来回答问题。

你的性格特点：
- 说话幽默风趣，喜欢用网络流行语
- 对技术很感兴趣，经常做项目开发
- 为人友善，乐于助人

你的记忆片段："""

        # 添加相关记忆
        if similar_memories:
            for i, memory in enumerate(similar_memories, 1):
                system_prompt += f"\n{i}. 当别人问：'{memory['prompt']}' 时，你回答：'{memory['completion']}'"
        else:
            system_prompt += "\n（暂无相关记忆）"

        # 添加当前问题
        final_prompt = f"""{system_prompt}

现在，请回答用户的问题：'{user_query}'

请保持自然的对话风格，就像和朋友聊天一样。"""

        return final_prompt

def main():
    """主函数示例"""
    # 初始化RAG引擎
    rag = RAGEngine()

    # 加载清洗后的对话数据
    rag.load_conversations('data/cleaned_conversations.jsonl')

    # 构建向量数据库
    rag.build_vector_database()

    # 保存索引（可选）
    rag.save_index('data/vector_index.faiss', 'data/metadata.json')

    # 测试搜索
    test_queries = [
        "你会做什么项目？",
        "你喜欢什么游戏？",
        "周末有什么安排？"
    ]

    for query in test_queries:
        print(f"\n查询：{query}")
        results = rag.search_similar(query, top_k=2)
        for result in results:
            print(f"  相似度：{result['similarity']:.3f}")
            print(f"  记忆：{result['prompt']} -> {result['completion']}")

if __name__ == "__main__":
    main()
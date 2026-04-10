import json
import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import faiss
import os

class ImprovedRAGEngine:
    """改进的RAG引擎，优化向量检索策略"""

    def __init__(self, model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2'):
        """初始化改进的RAG引擎"""
        self.model = SentenceTransformer(model_name)
        self.dimension = 384
        self.prompt_index = None  # 专门用于问题检索的索引
        self.completion_index = None  # 专门用于回答检索的索引（可选）
        self.prompt_metadata = []  # 存储问题元数据
        self.completion_metadata = []  # 存储回答元数据

    def load_conversations(self, jsonl_file: str):
        """加载清洗后的对话数据"""
        conversations = []
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    conversations.append(json.loads(line.strip()))

        self.conversations = conversations
        print(f"加载了 {len(conversations)} 条对话记录")

    def build_vector_database(self, strategy: str = "prompt_only"):
        """构建向量数据库（改进策略）"""

        if not self.conversations:
            raise ValueError("没有对话数据，请先加载数据")

        if strategy == "prompt_only":
            self._build_prompt_only_index()
        elif strategy == "dual_index":
            self._build_dual_index()
        else:
            raise ValueError(f"不支持的策略: {strategy}")

    def _build_prompt_only_index(self):
        """只对问题进行向量化（推荐策略）"""

        print("正在构建问题专用向量索引...")

        # 只提取问题文本
        prompt_texts = []
        self.prompt_metadata = []

        for i, conv in enumerate(self.conversations):
            prompt = conv.get('prompt', '').strip()
            if prompt:  # 确保问题不为空
                prompt_texts.append(prompt)
                self.prompt_metadata.append({
                    'id': i,
                    'prompt': prompt,
                    'completion': conv.get('completion', ''),
                    'full_conversation': conv
                })

        if not prompt_texts:
            raise ValueError("没有找到有效的问题数据")

        # 生成问题向量
        print(f"为 {len(prompt_texts)} 个问题生成向量...")
        prompt_embeddings = self.model.encode(prompt_texts, show_progress_bar=True)

        # 创建FAISS索引
        self.prompt_index = faiss.IndexFlatL2(self.dimension)
        self.prompt_index.add(prompt_embeddings.astype('float32'))

        print(f"问题向量索引构建完成，共 {len(prompt_texts)} 条记录")

    def _build_dual_index(self):
        """构建双索引（问题和回答分别索引）"""

        print("正在构建双向量索引...")

        # 问题索引
        prompt_texts = [conv.get('prompt', '').strip() for conv in self.conversations if conv.get('prompt')]
        prompt_embeddings = self.model.encode(prompt_texts)
        self.prompt_index = faiss.IndexFlatL2(self.dimension)
        self.prompt_index.add(prompt_embeddings.astype('float32'))
        self.prompt_metadata = [
            {
                'id': i,
                'prompt': conv.get('prompt', ''),
                'completion': conv.get('completion', ''),
                'full_conversation': conv
            }
            for i, conv in enumerate(self.conversations) if conv.get('prompt')
        ]

        # 回答索引（可选，用于回答相似度检索）
        completion_texts = [conv.get('completion', '').strip() for conv in self.conversations if conv.get('completion')]
        if completion_texts:
            completion_embeddings = self.model.encode(completion_texts)
            self.completion_index = faiss.IndexFlatL2(self.dimension)
            self.completion_index.add(completion_embeddings.astype('float32'))
            self.completion_metadata = [
                {
                    'id': i,
                    'prompt': conv.get('prompt', ''),
                    'completion': conv.get('completion', ''),
                    'full_conversation': conv
                }
                for i, conv in enumerate(self.conversations) if conv.get('completion')
            ]

        print(f"双索引构建完成：问题 {len(prompt_texts)} 条，回答 {len(completion_texts)} 条")

    def search_similar_prompts(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索相似问题（改进的检索策略）"""

        if self.prompt_index is None:
            raise ValueError("问题索引未构建，请先构建向量数据库")

        # 生成查询向量
        query_vector = self.model.encode([query])

        # 搜索最相似的问题
        distances, indices = self.prompt_index.search(query_vector.astype('float32'), top_k)

        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx != -1 and idx < len(self.prompt_metadata):
                metadata = self.prompt_metadata[idx]
                similarity = float(1 / (1 + distance))  # 转换为相似度分数

                results.append({
                    'query': query,
                    'matched_prompt': metadata['prompt'],
                    'matched_completion': metadata['completion'],
                    'similarity': similarity,
                    'original_conversation': metadata['full_conversation']
                })

        return results

    def search_similar_completions(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索相似回答（可选功能）"""

        if self.completion_index is None:
            print("警告：回答索引未构建")
            return []

        query_vector = self.model.encode([query])
        distances, indices = self.completion_index.search(query_vector.astype('float32'), top_k)

        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx != -1 and idx < len(self.completion_metadata):
                metadata = self.completion_metadata[idx]
                similarity = float(1 / (1 + distance))

                results.append({
                    'query': query,
                    'matched_prompt': metadata['prompt'],
                    'matched_completion': metadata['completion'],
                    'similarity': similarity
                })

        return results

    def build_enhanced_prompt(self, user_query: str, target_persona: str = "李四",
                             strategy: str = "semantic_matching") -> str:
        """构建增强的提示词（改进版本）"""

        if strategy == "semantic_matching":
            return self._build_semantic_prompt(user_query, target_persona)
        elif strategy == "context_enrichment":
            return self._build_context_enriched_prompt(user_query, target_persona)
        else:
            raise ValueError(f"不支持的提示词构建策略: {strategy}")

    def _build_semantic_prompt(self, user_query: str, target_persona: str) -> str:
        """基于语义匹配构建提示词"""

        # 搜索相关记忆（基于问题相似度）
        similar_memories = self.search_similar_prompts(user_query, top_k=3)

        # 构建系统提示词
        system_prompt = f"""你现在扮演{target_persona}，一个真实的人。请根据以下记忆片段来回答问题。

你的性格特点：
- 说话幽默风趣，喜欢用网络流行语
- 对技术很感兴趣，经常做项目开发
- 为人友善，乐于助人

你的相关记忆："""

        if similar_memories:
            for i, memory in enumerate(similar_memories, 1):
                similarity_score = memory['similarity']
                # 只包含相似度较高的记忆
                if similarity_score > 0.3:  # 相似度阈值
                    system_prompt += f"\n{i}. 当别人问：'{memory['matched_prompt']}' 时，你回答：'{memory['matched_completion']}'"
        else:
            system_prompt += "\n（暂无高度相关的记忆，请基于你的性格特点回答）"

        # 添加当前问题
        final_prompt = f"""{system_prompt}

现在，用户问：'{user_query}'

请基于你的记忆和性格特点，给出自然、友好的回答。如果记忆中有相关经验，可以适当引用，但要保持回答的连贯性和自然性。"""

        return final_prompt

    def _build_context_enriched_prompt(self, user_query: str, target_persona: str) -> str:
        """基于上下文丰富的提示词构建"""

        # 搜索相似问题和回答
        prompt_memories = self.search_similar_prompts(user_query, top_k=2)
        completion_memories = self.search_similar_completions(user_query, top_k=2)

        # 构建更丰富的上下文
        system_prompt = f"""你现在扮演{target_persona}，一个真实的人。请根据以下相关经历和知识来回答问题。

你的性格特点：
- 说话幽默风趣，喜欢用网络流行语
- 对技术很感兴趣，经常做项目开发
- 为人友善，乐于助人

你的相关经历："""

        # 添加问题相关的记忆
        if prompt_memories:
            system_prompt += "\n🔍 类似问题的处理经验："
            for memory in prompt_memories:
                if memory['similarity'] > 0.3:
                    system_prompt += f"\n- 问题：'{memory['matched_prompt']}' → 回答：'{memory['matched_completion']}'"

        # 添加回答相关的记忆
        if completion_memories:
            system_prompt += "\n💡 相关知识："
            for memory in completion_memories:
                if memory['similarity'] > 0.3:
                    system_prompt += f"\n- 经验：'{memory['matched_completion']}'"

        final_prompt = f"""{system_prompt}

现在，用户问：'{user_query}'

请基于以上经历和你的性格特点，给出详细、自然的回答。可以适当引用相关经验，但要确保回答的连贯性和个性化。"""

        return final_prompt

    def save_index(self, prompt_index_path: str, prompt_metadata_path: str,
                   completion_index_path: str = None, completion_metadata_path: str = None):
        """保存索引和元数据"""

        if self.prompt_index is None:
            raise ValueError("索引未构建，请先构建向量数据库")

        # 保存问题索引
        faiss.write_index(self.prompt_index, prompt_index_path)
        with open(prompt_metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.prompt_metadata, f, ensure_ascii=False, indent=2)

        print(f"问题索引已保存到 {prompt_index_path}")
        print(f"问题元数据已保存到 {prompt_metadata_path}")

        # 保存回答索引（如果存在）
        if self.completion_index and completion_index_path:
            faiss.write_index(self.completion_index, completion_index_path)
            if completion_metadata_path:
                with open(completion_metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(self.completion_metadata, f, ensure_ascii=False, indent=2)
            print(f"回答索引已保存到 {completion_index_path}")

    def load_index(self, prompt_index_path: str, prompt_metadata_path: str,
                   completion_index_path: str = None, completion_metadata_path: str = None):
        """加载索引和元数据"""

        if not os.path.exists(prompt_index_path) or not os.path.exists(prompt_metadata_path):
            raise FileNotFoundError("问题索引文件或元数据文件不存在")

        # 加载问题索引
        self.prompt_index = faiss.read_index(prompt_index_path)
        with open(prompt_metadata_path, 'r', encoding='utf-8') as f:
            self.prompt_metadata = json.load(f)

        # 加载回答索引（如果存在）
        if completion_index_path and os.path.exists(completion_index_path):
            self.completion_index = faiss.read_index(completion_index_path)
            if completion_metadata_path and os.path.exists(completion_metadata_path):
                with open(completion_metadata_path, 'r', encoding='utf-8') as f:
                    self.completion_metadata = json.load(f)

        print(f"索引和元数据加载完成")
        print(f"问题记录数：{len(self.prompt_metadata)}")
        print(f"回答记录数：{len(self.completion_metadata) if self.completion_metadata else 0}")

def main():
    """主函数示例"""

    # 初始化改进的RAG引擎
    rag = ImprovedRAGEngine()

    # 加载数据
    rag.load_conversations('data/cleaned_conversations.jsonl')

    # 构建向量数据库（使用推荐的问题专用策略）
    rag.build_vector_database(strategy="prompt_only")

    # 保存索引
    rag.save_index(
        'data/prompt_index.faiss',
        'data/prompt_metadata.json'
    )

    # 测试搜索
    test_queries = [
        "你会做什么项目？",
        "你喜欢什么游戏？",
        "周末有什么安排？",
        "最近在学习什么技术？"
    ]

    for query in test_queries:
        print(f"\n查询：'{query}'")
        print("=" * 50)

        # 搜索相似问题
        results = rag.search_similar_prompts(query, top_k=3)
        for i, result in enumerate(results, 1):
            print(f"{i}. 相似度：{result['similarity']:.3f}")
            print(f"   匹配问题：{result['matched_prompt']}")
            print(f"   对应回答：{result['matched_completion']}")
            print()

        # 构建增强提示词
        enhanced_prompt = rag.build_enhanced_prompt(query, "李四", "semantic_matching")
        print("增强提示词预览：")
        print(enhanced_prompt[:200] + "..." if len(enhanced_prompt) > 200 else enhanced_prompt)
        print("\n" + "=" * 50)

if __name__ == "__main__":
    main()
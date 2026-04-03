from flask import Flask, request, jsonify
from flask_cors import CORS
from rag_engine import RAGEngine
import os

app = Flask(__name__)
CORS(app)

# 初始化RAG引擎
rag_engine = None

@app.before_first_request
def initialize_rag():
    global rag_engine
    try:
        rag_engine = RAGEngine()

        # 检查是否存在已保存的索引
        if os.path.exists('data/vector_index.faiss') and os.path.exists('data/metadata.json'):
            print("加载已保存的向量索引...")
            rag_engine.load_index('data/vector_index.faiss', 'data/metadata.json')
        else:
            print("构建新的向量数据库...")
            # 加载并处理数据
            if os.path.exists('data/cleaned_conversations.jsonl'):
                rag_engine.load_conversations('data/cleaned_conversations.jsonl')
                rag_engine.build_vector_database()
                # 保存索引供下次使用
                rag_engine.save_index('data/vector_index.faiss', 'data/metadata.json')
            else:
                print("警告：未找到清洗后的对话数据")

    except Exception as e:
        print(f"RAG引擎初始化失败: {e}")

@app.route('/rag-query', methods=['POST'])
def rag_query():
    try:
        data = request.get_json()
        query = data.get('query', '')
        target_persona = data.get('target_persona', '李四')

        if not query:
            return jsonify({
                'error': '查询内容不能为空',
                'enhanced_prompt': '你现在是李四，说话风格幽默风趣，喜欢用网络流行语。请回答用户的问题。'
            }), 400

        if rag_engine is None:
            return jsonify({
                'error': 'RAG引擎未初始化',
                'enhanced_prompt': f'你现在是{target_persona}，说话风格幽默风趣，喜欢用网络流行语。请回答用户的问题。'
            }), 500

        # 构建增强的提示词
        enhanced_prompt = rag_engine.build_enhanced_prompt(query, target_persona)

        return jsonify({
            'query': query,
            'enhanced_prompt': enhanced_prompt,
            'success': True
        })

    except Exception as e:
        print(f"处理RAG查询时出错: {e}")
        return jsonify({
            'error': str(e),
            'enhanced_prompt': f'你现在是李四，说话风格幽默风趣，喜欢用网络流行语。请回答用户的问题。'
        }), 500

@app.route('/search-memories', methods=['POST'])
def search_memories():
    """搜索相关记忆"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        top_k = data.get('top_k', 5)

        if not query:
            return jsonify({'error': '查询内容不能为空'}), 400

        if rag_engine is None:
            return jsonify({'error': 'RAG引擎未初始化'}), 500

        # 搜索相似记忆
        memories = rag_engine.search_similar(query, top_k)

        return jsonify({
            'query': query,
            'memories': memories,
            'success': True
        })

    except Exception as e:
        print(f"搜索记忆时出错: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'ok',
        'rag_initialized': rag_engine is not None,
        'vector_count': len(rag_engine.metadata) if rag_engine else 0
    })

if __name__ == '__main__':
    print("启动RAG服务...")
    app.run(host='0.0.0.0', port=5000, debug=True)
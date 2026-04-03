from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import requests
from typing import Dict, List, Any, Optional
from tools import ToolRegistry
import os

app = Flask(__name__)
CORS(app)

# 初始化工具注册中心
tool_registry = ToolRegistry()

class FunctionCallingAgent:
    """基于Function Calling的AI Agent"""

    def __init__(self, llm_api_key: str, llm_api_url: str):
        self.llm_api_key = llm_api_key
        self.llm_api_url = llm_api_url
        self.tool_registry = tool_registry

    def process_message_with_function_calling(self, user_message: str, system_prompt: str) -> Dict[str, Any]:
        """使用Function Calling处理消息"""

        # 第一步：调用大模型，让它决定是否需要调用工具
        function_call_result = self._call_llm_with_functions(user_message, system_prompt)

        # 如果没有函数调用，直接返回回复
        if not function_call_result.get("function_call"):
            return {
                "response": function_call_result.get("content", "抱歉，我现在无法回答这个问题。"),
                "tool_used": None,
                "success": True
            }

        # 如果有函数调用，执行工具
        function_call = function_call_result["function_call"]
        tool_name = function_call["name"]
        tool_arguments = function_call["arguments"]

        try:
            # 执行工具
            tool_result = self.tool_registry.execute_tool(tool_name, tool_arguments)

            # 第二步：将工具结果再次发送给大模型，生成最终回复
            final_response = self._generate_final_response(
                user_message,
                tool_name,
                tool_arguments,
                tool_result,
                system_prompt
            )

            return {
                "response": final_response,
                "tool_used": tool_name,
                "tool_result": tool_result,
                "success": True
            }

        except Exception as e:
            return {
                "response": f"工具调用失败：{str(e)}",
                "tool_used": tool_name,
                "success": False,
                "error": str(e)
            }

    def _call_llm_with_functions(self, user_message: str, system_prompt: str) -> Dict[str, Any]:
        """调用大模型Function Calling API"""

        # 构建包含工具定义的请求
        tools = self.tool_registry.get_all_tools()

        request_body = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "tools": tools,
            "tool_choice": "auto",  # 让模型自动决定是否调用工具
            "temperature": 0.7,
            "max_tokens": 1000
        }

        try:
            headers = {
                "Authorization": f"Bearer {self.llm_api_key}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                self.llm_api_url,
                json=request_body,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()

                if "choices" in result and len(result["choices"]) > 0:
                    message = result["choices"][0]["message"]

                    # 检查是否有工具调用
                    if "tool_calls" in message and message["tool_calls"]:
                        tool_call = message["tool_calls"][0]  # 取第一个工具调用
                        return {
                            "function_call": {
                                "name": tool_call["function"]["name"],
                                "arguments": json.loads(tool_call["function"]["arguments"])
                            }
                        }
                    else:
                        # 没有工具调用，直接返回内容
                        return {
                            "content": message.get("content", "")
                        }
                else:
                    return {"content": "抱歉，服务暂时不可用。"}
            else:
                return {"content": f"API调用失败：{response.status_code}"}

        except Exception as e:
            print(f"Function Calling API调用失败: {e}")
            # 降级到基础回复
            return {"content": "你好！我是李四，很高兴和你聊天！有什么我可以帮助你的吗？"}

    def _generate_final_response(self, user_message: str, tool_name: str,
                                tool_arguments: Dict, tool_result: Dict,
                                system_prompt: str) -> str:
        """使用工具结果生成最终回复"""

        # 构建包含工具结果的提示词
        tool_context = f"""
用户问题：{user_message}

你调用了工具 '{tool_name}'，参数为：{json.dumps(tool_arguments, ensure_ascii=False)}

工具执行结果：
{json.dumps(tool_result, ensure_ascii=False, indent=2)}

请根据以上工具结果，用自然友好的语言回答用户的问题。保持你作为李四的说话风格：幽默风趣，喜欢用网络流行语。
"""

        request_body = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": tool_context}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }

        try:
            headers = {
                "Authorization": f"Bearer {self.llm_api_key}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                self.llm_api_url,
                json=request_body,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"]

            return "工具调用成功，但生成回复时出现问题。"

        except Exception as e:
            print(f"生成最终回复失败: {e}")
            return "工具调用成功，但生成回复时出现错误。"

# 从环境变量获取配置
LLM_API_KEY = os.getenv('LLM_API_KEY', 'your-api-key')
LLM_API_URL = os.getenv('LLM_API_URL', 'https://api.deepseek.com/v1/chat/completions')

# 初始化Function Calling Agent
function_agent = FunctionCallingAgent(LLM_API_KEY, LLM_API_URL)

@app.route('/function-call-chat', methods=['POST'])
def function_call_chat():
    """Function Calling聊天接口"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        system_prompt = data.get('system_prompt', '你现在是李四，说话风格幽默风趣，喜欢用网络流行语。')

        if not user_message:
            return jsonify({
                'error': '消息内容不能为空',
                'success': False
            }), 400

        # 使用Function Calling处理消息
        result = function_agent.process_message_with_function_calling(user_message, system_prompt)

        return jsonify(result)

    except Exception as e:
        print(f"Function Calling处理失败: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@app.route('/tools/schema', methods=['GET'])
def get_tools_schema():
    """获取工具Schema定义"""
    return jsonify({
        'tools': tool_registry.get_all_tools(),
        'success': True
    })

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'agent_type': 'function_calling',
        'tools_count': len(tool_registry.tools),
        'llm_configured': bool(LLM_API_KEY != 'your-api-key')
    })

if __name__ == '__main__':
    print("启动Function Calling AI Agent服务...")
    app.run(host='0.0.0.0', port=5002, debug=True)
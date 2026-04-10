from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import re
from typing import Dict, List, Any
from tools import ToolRegistry

app = Flask(__name__)
CORS(app)

# 初始化工具注册中心
tool_registry = ToolRegistry()

class AIAgent:
    """AI Agent主类"""

    def __init__(self):
        self.tool_registry = tool_registry
        self.conversation_history = []

    def process_message_with_tools(self, user_message: str, system_prompt: str) -> Dict[str, Any]:
        """处理带工具调用的消息"""

        # 构建包含工具定义的提示词
        tools_prompt = self._build_tools_prompt(system_prompt)

        # 模拟大模型响应（在实际应用中这里会调用真实的大模型API）
        # 这里我们模拟一个简单的工具调用决策逻辑
        tool_call = self._decide_tool_call(user_message)

        if tool_call:
            # 执行工具调用
            tool_result = self._execute_tool_call(tool_call)

            # 构建最终回复
            final_response = self._build_final_response(user_message, tool_call, tool_result)

            return {
                "response": final_response,
                "tool_used": tool_call["name"],
                "tool_result": tool_result,
                "success": True
            }
        else:
            # 不使用工具，直接回复
            return {
                "response": self._generate_normal_response(user_message, system_prompt),
                "tool_used": None,
                "success": True
            }

    def _build_tools_prompt(self, base_prompt: str) -> str:
        """构建包含工具信息的提示词"""
        tools_info = "\n\n你可以使用以下工具来帮助你回答问题：\n"

        for tool in self.tool_registry.get_all_tools():
            func = tool["function"]
            tools_info += f"\n- {func['name']}: {func['description']}"

        tools_info += "\n\n如果用户的问题需要使用这些工具，请先调用相应的工具，然后基于工具的结果来回答用户。"

        return base_prompt + tools_info

    def _decide_tool_call(self, user_message: str) -> Dict[str, Any] | None:
        """决定是否调用工具以及调用哪个工具（简化版本）"""
        message_lower = user_message.lower()

        # GitHub相关查询
        if any(keyword in message_lower for keyword in ["github", "开源", "项目", "代码", "仓库"]):
            if "vue" in message_lower or "react" in message_lower or "spring" in message_lower:
                return {
                    "name": "search_github",
                    "arguments": {
                        "query": "vue spring react",
                        "language": "javascript"
                    }
                }

        # 天气查询
        if any(keyword in message_lower for keyword in ["天气", "气温", "温度"]):
            # 简单的城市提取
            cities = ["北京", "上海", "广州", "深圳"]
            for city in cities:
                if city in user_message:
                    return {
                        "name": "get_weather",
                        "arguments": {
                            "city": city
                        }
                    }

        # 时间查询
        if any(keyword in message_lower for keyword in ["时间", "几点", "日期"]):
            return {
                "name": "get_current_time",
                "arguments": {}
            }

        # 计算相关
        if re.search(r'\d+\s*[+\-*/]\s*\d+', user_message):
            # 提取数学表达式
            match = re.search(r'(\d+\s*[+\-*/]\s*\d+(?:\s*[+\-*/]\s*\d+)*)', user_message)
            if match:
                expression = match.group(1).replace(' ', '')
                return {
                    "name": "calculate",
                    "arguments": {
                        "expression": expression
                    }
                }

        return None

    def _execute_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用"""
        try:
            tool_name = tool_call["name"]
            arguments = tool_call["arguments"]

            result = self.tool_registry.execute_tool(tool_name, arguments)
            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"工具执行失败: {str(e)}"
            }

    def _build_final_response(self, user_message: str, tool_call: Dict, tool_result: Dict) -> str:
        """基于工具结果构建最终回复"""

        if not tool_result.get("success", False):
            return f"抱歉，调用工具时出现了问题：{tool_result.get('error', '未知错误')}"

        tool_name = tool_call["name"]

        if tool_name == "search_github":
            results = tool_result.get("results", [])
            if results:
                response = "我为你找到了几个相关的项目：\n"
                for i, repo in enumerate(results, 1):
                    response += f"\n{i}. {repo['full_name']}\n"
                    response += f"   描述：{repo['description'] or '暂无描述'}\n"
                    response += f"   ⭐ {repo['stargazers_count']} stars | 🔗 {repo['html_url']}\n"
                return response
            else:
                return "抱歉，没有找到相关的项目。"

        elif tool_name == "get_weather":
            data = tool_result.get("data", {})
            city = tool_result.get("city", "")
            return f"{city}的天气情况：\n🌡️ 温度：{data.get('temperature', 'N/A')}\n☁️ 天气：{data.get('condition', 'N/A')}\n💧 湿度：{data.get('humidity', 'N/A')}"

        elif tool_name == "get_current_time":
            current_time = tool_result.get("current_time", "")
            return f"现在是：{current_time}"

        elif tool_name == "calculate":
            expression = tool_result.get("expression", "")
            result = tool_result.get("result", "")
            return f"计算结果：{expression} = {result}"

        return "工具调用成功，但无法生成回复。"

    def _generate_normal_response(self, user_message: str, system_prompt: str) -> str:
        """生成普通的回复"""
        # 这里是简化的回复生成，实际应用中应该调用大模型API
        responses = [
            "哈哈，这个问题问得好！",
            "让我想想...",
            "根据我的理解，",
            "我觉得可以这样看，",
            "嗯，这个问题挺有意思的。"
        ]

        import random
        base_response = random.choice(responses)

        # 根据用户消息内容生成更具体的回复
        if "你好" in user_message or "hello" in user_message.lower():
            return "你好啊！我是李四，很高兴认识你！"
        elif "项目" in user_message or "工作" in user_message:
            return "说到项目，我最近在做一个小商城系统，用Vue和Spring Boot写的，还挺有意思的！"
        elif "游戏" in user_message:
            return "游戏啊，我最近沉迷原神，你也在玩吗？"

        return base_response + "这个问题我需要多想想。"

# 初始化AI Agent
ai_agent = AIAgent()

@app.route('/agent-chat', methods=['POST'])
def agent_chat():
    """AI Agent聊天接口"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        system_prompt = data.get('system_prompt', '你现在是李四，说话风格幽默风趣。')

        if not user_message:
            return jsonify({
                'error': '消息内容不能为空',
                'success': False
            }), 400

        # 处理消息
        result = ai_agent.process_message_with_tools(user_message, system_prompt)

        return jsonify(result)

    except Exception as e:
        print(f"处理Agent聊天时出错: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@app.route('/tools/list', methods=['GET'])
def list_tools():
    """获取可用工具列表"""
    return jsonify({
        'tools': tool_registry.get_all_tools(),
        'success': True
    })

@app.route('/tools/execute', methods=['POST'])
def execute_tool():
    """直接执行工具"""
    try:
        data = request.get_json()
        tool_name = data.get('tool_name')
        arguments = data.get('arguments', {})

        if not tool_name:
            return jsonify({
                'error': '工具名称不能为空',
                'success': False
            }), 400

        result = tool_registry.execute_tool(tool_name, arguments)

        return jsonify({
            'result': result,
            'success': True
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'agent_ready': True,
        'tools_count': len(tool_registry.tools)
    })

if __name__ == '__main__':
    print("启动AI Agent服务...")
    app.run(host='0.0.0.0', port=5001, debug=True)
import requests
import json
from typing import Dict, List, Any
from datetime import datetime
import re

class ToolRegistry:
    """工具注册中心"""

    def __init__(self):
        self.tools = {}
        self.register_default_tools()

    def register_default_tools(self):
        """注册默认工具"""
        # GitHub搜索工具
        self.register_tool(
            name="search_github",
            description="在GitHub上搜索开源项目，返回项目信息包括名称、描述、star数量等",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，例如：vue, react, spring boot"
                    },
                    "language": {
                        "type": "string",
                        "description": "编程语言过滤，例如：javascript, python, java（可选）"
                    }
                },
                "required": ["query"]
            },
            function=self._search_github
        )

        # 天气查询工具
        self.register_tool(
            name="get_weather",
            description="获取指定城市的当前天气信息，包括温度、天气状况和湿度",
            parameters={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，例如：北京、上海、广州、深圳"
                    }
                },
                "required": ["city"]
            },
            function=self._get_weather
        )

        # 时间查询工具
        self.register_tool(
            name="get_current_time",
            description="获取当前的日期和时间信息",
            parameters={
                "type": "object",
                "properties": {}
            },
            function=self._get_current_time
        )

        # 计算工具
        self.register_tool(
            name="calculate",
            description="执行基础数学计算，支持加减乘除和括号运算",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式，例如：2+2, 3*5, 10/2, (2+3)*4"
                    }
                },
                "required": ["expression"]
            },
            function=self._calculate
        )

    def register_tool(self, name: str, description: str, parameters: Dict, function):
        """注册新工具"""
        self.tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "function": function
        }

    def get_all_tools(self) -> List[Dict]:
        """获取所有工具定义"""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"]
                }
            }
            for tool in self.tools.values()
        ]

    def execute_tool(self, tool_name: str, arguments: Dict) -> Any:
        """执行指定工具"""
        if tool_name not in self.tools:
            raise ValueError(f"工具 {tool_name} 不存在")

        tool = self.tools[tool_name]
        return tool["function"](**arguments)

    def _search_github(self, query: str, language: str = None) -> Dict:
        """GitHub搜索实现"""
        try:
            # 构建搜索URL
            base_url = "https://api.github.com/search/repositories"
            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": 5
            }

            if language:
                params["q"] = f"{query} language:{language}"

            headers = {
                "Accept": "application/vnd.github.v3+json"
            }

            response = requests.get(base_url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                results = []

                for repo in data.get("items", [])[:3]:  # 只返回前3个结果
                    results.append({
                        "name": repo["name"],
                        "full_name": repo["full_name"],
                        "description": repo["description"],
                        "html_url": repo["html_url"],
                        "stargazers_count": repo["stargazers_count"],
                        "language": repo["language"]
                    })

                return {
                    "success": True,
                    "query": query,
                    "results": results,
                    "total_count": data.get("total_count", 0)
                }
            else:
                return {
                    "success": False,
                    "error": f"GitHub API返回错误: {response.status_code}"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _get_weather(self, city: str) -> Dict:
        """天气查询实现（模拟数据）"""
        try:
            # 这里使用模拟数据，实际项目中可以接入真实的天气API
            weather_data = {
                "北京": {"temperature": "15°C", "condition": "晴", "humidity": "45%"},
                "上海": {"temperature": "18°C", "condition": "多云", "humidity": "60%"},
                "广州": {"temperature": "25°C", "condition": "小雨", "humidity": "75%"},
                "深圳": {"temperature": "26°C", "condition": "阴", "humidity": "70%"}
            }

            if city in weather_data:
                return {
                    "success": True,
                    "city": city,
                    "data": weather_data[city]
                }
            else:
                return {
                    "success": False,
                    "error": f"暂不支持查询{city}的天气信息"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _get_current_time(self) -> Dict:
        """获取当前时间"""
        try:
            now = datetime.now()
            return {
                "success": True,
                "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
                "timezone": "北京时间 (UTC+8)"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _calculate(self, expression: str) -> Dict:
        """数学计算实现"""
        try:
            # 安全地评估数学表达式
            allowed_chars = set("0123456789+-*/(). ")
            if not all(c in allowed_chars for c in expression):
                return {
                    "success": False,
                    "error": "表达式包含非法字符"
                }

            # 使用eval计算（在生产环境中应该使用更安全的数学表达式解析器）
            result = eval(expression)

            return {
                "success": True,
                "expression": expression,
                "result": result
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"计算错误: {str(e)}"
            }

def main():
    """测试工具"""
    registry = ToolRegistry()

    # 测试GitHub搜索
    print("测试GitHub搜索:")
    result = registry.execute_tool("search_github", {"query": "vue", "language": "javascript"})
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # 测试天气查询
    print("\n测试天气查询:")
    result = registry.execute_tool("get_weather", {"city": "北京"})
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # 测试时间查询
    print("\n测试时间查询:")
    result = registry.execute_tool("get_current_time", {})
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # 测试计算
    print("\n测试计算:")
    result = registry.execute_tool("calculate", {"expression": "2+3*4"})
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
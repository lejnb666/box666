import re
import json
import requests
from typing import List, Dict, Tuple, Optional
from datetime import datetime

class AdvancedDataCleaner:
    """高级数据清洗引擎，支持大模型辅助清洗"""

    def __init__(self, llm_api_key: str = None, llm_api_url: str = None):
        self.llm_api_key = llm_api_key
        self.llm_api_url = llm_api_url
        self.basic_patterns = [
            r'\d{4}-\d{1,2}-\d{1,2}\s\d{1,2}:\d{1,2}:\d{1,2}',
            r'已撤回一条消息',
            r'拍了拍',
            r'\[.+?\]',
            r'图片|语音|视频|位置|名片|转账|红包',
            r'邀请.*加入了群聊',
            r'修改群聊名称',
            r'你已添加了.*，现在可以开始聊天了'
        ]

    def clean_with_llm(self, raw_text: str, target_name: str) -> List[Dict[str, str]]:
        """使用大模型进行高级数据清洗和Q&A提取"""

        if not self.llm_api_key or not self.llm_api_url:
            print("警告：未提供LLM API配置，使用基础清洗模式")
            return self.basic_clean(raw_text, target_name)

        # 构建提示词让大模型进行清洗
        system_prompt = f"""你是一个专业的数据清洗助手，专门处理微信聊天记录。

        任务要求：
        1. 过滤掉所有系统消息、时间戳、撤回消息等噪音
        2. 识别出高质量的对话问答对
        3. 确保每个Q&A对都是完整、有意义的
        4. 目标人物是：{target_name}

        输出格式要求：
        返回JSON数组，每个元素包含prompt和completion字段：
        [
          {{"prompt": "用户的问题", "completion": "目标人物的回答"}},
          {{"prompt": "另一个问题", "completion": "另一个回答"}}
        ]

        如果没有找到有效的Q&A对，返回空数组[]。
        """

        user_prompt = f"请清洗以下微信聊天记录并提取Q&A对：\n\n{raw_text}"

        try:
            request_body = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.1,  # 低温度确保输出稳定
                "max_tokens": 2000
            }

            headers = {
                "Authorization": f"Bearer {self.llm_api_key}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                self.llm_api_url,
                json=request_body,
                headers=headers,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]

                # 解析大模型返回的JSON
                try:
                    qa_pairs = json.loads(content)
                    if isinstance(qa_pairs, list):
                        return qa_pairs
                except json.JSONDecodeError:
                    # 如果JSON解析失败，尝试提取JSON部分
                    json_match = re.search(r'\[.*\]', content, re.DOTALL)
                    if json_match:
                        qa_pairs = json.loads(json_match.group())
                        return qa_pairs

        except Exception as e:
            print(f"大模型清洗失败: {e}，降级到基础清洗模式")

        # 降级到基础清洗
        return self.basic_clean(raw_text, target_name)

    def basic_clean(self, raw_text: str, target_name: str) -> List[Dict[str, str]]:
        """基础清洗模式，改进的Q&A提取算法"""

        # 首先进行基础清理
        cleaned_lines = self._clean_lines(raw_text)

        # 改进的对话分割算法
        conversations = self._extract_conversations_improved(cleaned_lines, target_name)

        return conversations

    def _clean_lines(self, text: str) -> List[str]:
        """清理文本行"""
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 移除时间戳和系统消息
            for pattern in self.basic_patterns:
                line = re.sub(pattern, '', line)

            # 移除多余空格
            line = re.sub(r'\s+', ' ', line).strip()

            if line:
                cleaned_lines.append(line)

        return cleaned_lines

    def _extract_conversations_improved(self, lines: List[str], target_name: str) -> List[Dict[str, str]]:
        """改进的对话提取算法"""

        conversations = []
        current_context = []  # 存储当前对话上下文
        current_question = None

        for line in lines:
            # 识别说话者
            speaker, content = self._identify_speaker_improved(line, target_name)

            if not content:
                continue

            # 添加到上下文
            current_context.append({"speaker": speaker, "content": content})

            # 如果上下文太长，进行清理
            if len(current_context) > 10:
                current_context = current_context[-5:]  # 保留最近5条

            # 处理不同类型的消息
            if speaker == target_name:
                # 目标人物的回复
                if current_question:
                    conversations.append({
                        "prompt": current_question,
                        "completion": content
                    })
                    current_question = None
                elif len(current_context) >= 2:
                    # 尝试从上下文中找到问题
                    question = self._find_question_in_context(current_context[:-1], target_name)
                    if question:
                        conversations.append({
                            "prompt": question,
                            "completion": content
                        })
            else:
                # 其他人的消息，可能是问题
                if self._is_likely_question(content):
                    current_question = content

        return conversations

    def _identify_speaker_improved(self, line: str, target_name: str) -> Tuple[str, str]:
        """改进的说话者识别"""

        # 支持多种格式
        formats = [
            r'^(.+?):\s*(.+)$',  # 标准格式：姓名: 内容
            r'^(.+?)\s+(.+)$',   # 姓名 内容
        ]

        for pattern in formats:
            match = re.match(pattern, line)
            if match:
                speaker = match.group(1).strip()
                content = match.group(2).strip()
                return speaker, content

        # 如果没有匹配到格式，尝试基于内容判断
        if target_name in line:
            # 可能是目标人物的自言自语
            return target_name, line.replace(target_name, '').strip()
        else:
            # 默认为其他用户
            return "其他用户", line

    def _is_likely_question(self, content: str) -> bool:
        """判断内容是否可能是问题"""
        question_indicators = ['？', '?', '什么', '怎么', '如何', '为什么', '吗', '呢']
        return any(indicator in content for indicator in question_indicators)

    def _find_question_in_context(self, context: List[Dict], target_name: str) -> Optional[str]:
        """在上下文中找到最可能的问题"""

        # 从后往前找，找到第一个非目标人物的消息
        for msg in reversed(context):
            if msg["speaker"] != target_name:
                if self._is_likely_question(msg["content"]):
                    return msg["content"]

        # 如果没有明确的问题，返回最近的非目标人物消息
        for msg in reversed(context):
            if msg["speaker"] != target_name:
                return msg["content"]

        return None

    def process_file(self, input_file: str, target_name: str, output_file: str,
                    use_llm: bool = True) -> List[Dict[str, str]]:
        """处理文件"""

        # 读取原始数据
        with open(input_file, 'r', encoding='utf-8') as f:
            raw_text = f.read()

        # 清洗数据
        if use_llm and self.llm_api_key:
            conversations = self.clean_with_llm(raw_text, target_name)
        else:
            conversations = self.basic_clean(raw_text, target_name)

        # 保存结果
        with open(output_file, 'w', encoding='utf-8') as f:
            for conv in conversations:
                f.write(json.dumps(conv, ensure_ascii=False) + '\n')

        print(f"处理完成！生成了 {len(conversations)} 条对话记录")
        print(f"使用模式: {'大模型辅助' if use_llm and self.llm_api_key else '基础清洗'}")

        return conversations

def main():
    """示例使用"""

    # 初始化清洗器（可以配置LLM API）
    cleaner = AdvancedDataCleaner(
        llm_api_key="your-api-key",  # 可选
        llm_api_url="https://api.deepseek.com/v1/chat/completions"  # 可选
    )

    # 处理数据
    conversations = cleaner.process_file(
        input_file="data/raw_chat.txt",
        target_name="李四",
        output_file="data/advanced_cleaned_conversations.jsonl",
        use_llm=False  # 先使用基础模式测试
    )

    # 显示一些示例
    print("\n清洗结果示例:")
    for i, conv in enumerate(conversations[:5]):
        print(f"{i+1}. Q: {conv['prompt']}")
        print(f"   A: {conv['completion']}")
        print()

if __name__ == "__main__":
    main()
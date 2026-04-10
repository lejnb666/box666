import re
import json
import csv
from datetime import datetime
from typing import List, Dict, Tuple

class WeChatDataCleaner:
    def __init__(self):
        # 定义需要过滤的系统消息模式
        self.system_patterns = [
            r'\d{4}-\d{1,2}-\d{1,2}\s\d{1,2}:\d{1,2}:\d{1,2}',  # 时间戳
            r'已撤回一条消息',  # 撤回消息
            r'拍了拍',  # 拍一拍
            r'\[.+?\]',  # 表情符号占位符
            r'图片|语音|视频|位置|名片|转账|红包',  # 多媒体消息
            r'邀请.*加入了群聊',  # 群聊邀请
            r'修改群聊名称',  # 群聊改名
            r'你已添加了.*，现在可以开始聊天了'  # 好友验证
        ]

        # 编译正则表达式
        self.compiled_patterns = [re.compile(pattern) for pattern in self.system_patterns]

    def clean_text(self, text: str) -> str:
        """清理单条文本消息"""
        if not text or not isinstance(text, str):
            return ""

        # 移除时间戳和系统消息
        cleaned_text = text.strip()
        for pattern in self.compiled_patterns:
            cleaned_text = pattern.sub('', cleaned_text)

        # 移除多余的空格和换行
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        cleaned_text = cleaned_text.strip()

        return cleaned_text

    def identify_speaker(self, line: str, target_name: str) -> Tuple[str, str]:
        """识别说话者和内容
        返回：(speaker, content)
        """
        # 假设微信导出格式为 "姓名: 消息内容"
        if ':' in line:
            parts = line.split(':', 1)
            speaker = parts[0].strip()
            content = parts[1].strip()
            return speaker, content

        # 如果没有冒号，尝试其他模式
        # 这里可以根据实际的微信导出格式进行调整
        return "unknown", line.strip()

    def process_chat_history(self, input_file: str, target_name: str, output_file: str):
        """处理聊天历史记录"""
        conversations = []
        current_q = None

        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line in lines:
            # 清理文本
            cleaned_line = self.clean_text(line)
            if not cleaned_line:
                continue

            # 识别说话者和内容
            speaker, content = self.identify_speaker(cleaned_line, target_name)

            if not content:
                continue

            # 如果是目标人物说的话
            if speaker == target_name:
                if current_q:
                    # 保存Q&A对
                    conversations.append({
                        "prompt": current_q,
                        "completion": content
                    })
                    current_q = None
            else:
                # 如果是其他人说的话，作为问题
                current_q = content

        # 保存为JSONL格式
        with open(output_file, 'w', encoding='utf-8') as f:
            for conv in conversations:
                f.write(json.dumps(conv, ensure_ascii=False) + '\n')

        print(f"处理完成！生成了 {len(conversations)} 条对话记录")
        return conversations

    def process_csv_data(self, csv_file: str, target_name: str, output_file: str):
        """处理CSV格式的微信数据"""
        conversations = []
        current_q = None

        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                # 假设CSV包含 sender, message, timestamp 列
                sender = row.get('sender', '')
                message = row.get('message', '')

                # 清理消息内容
                cleaned_message = self.clean_text(message)
                if not cleaned_message:
                    continue

                # 识别Q&A
                if sender == target_name:
                    if current_q:
                        conversations.append({
                            "prompt": current_q,
                            "completion": cleaned_message
                        })
                        current_q = None
                else:
                    current_q = cleaned_message

        # 保存结果
        with open(output_file, 'w', encoding='utf-8') as f:
            for conv in conversations:
                f.write(json.dumps(conv, ensure_ascii=False) + '\n')

        print(f"CSV处理完成！生成了 {len(conversations)} 条对话记录")
        return conversations

if __name__ == "__main__":
    cleaner = WeChatDataCleaner()

    # 示例用法
    target_person = "张三"  # 目标人物姓名

    # 处理文本格式数据
    conversations = cleaner.process_chat_history(
        input_file="data/raw_chat.txt",
        target_name=target_person,
        output_file="data/cleaned_conversations.jsonl"
    )

    print("数据清洗示例完成！")
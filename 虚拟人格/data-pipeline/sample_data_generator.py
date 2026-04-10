import json
import random
from datetime import datetime, timedelta

def generate_sample_data():
    """生成示例微信聊天记录用于测试"""

    # 示例对话数据
    sample_conversations = [
        {"speaker": "朋友A", "message": "今天中午吃什么？"},
        {"speaker": "李四", "message": "随便吧，我都行，点个外卖？"},
        {"speaker": "朋友A", "message": "昨天那个项目怎么样了？"},
        {"speaker": "李四", "message": "还行吧，就是有点累，加班到很晚"},
        {"speaker": "朋友A", "message": "周末一起打游戏吗？"},
        {"speaker": "李四", "message": "好啊，不过我最近迷上了原神"},
        {"speaker": "朋友A", "message": "你那个小米商城项目做完了吗？"},
        {"speaker": "李四", "message": "差不多了，前端用Vue写的，后端是Spring Boot"},
        {"speaker": "朋友A", "message": "厉害啊，能教教我吗？"},
        {"speaker": "李四", "message": "没问题，改天给你看看代码"}
    ]

    # 生成带时间戳的原始数据
    base_time = datetime.now() - timedelta(days=30)
    raw_messages = []

    for i, conv in enumerate(sample_conversations):
        timestamp = base_time + timedelta(hours=i*2)
        raw_message = f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')} {conv['speaker']}: {conv['message']}"
        raw_messages.append(raw_message)

    # 保存原始数据
    with open('data/raw_chat.txt', 'w', encoding='utf-8') as f:
        for msg in raw_messages:
            f.write(msg + '\n')

    print("示例数据已生成到 data/raw_chat.txt")

if __name__ == "__main__":
    generate_sample_data()
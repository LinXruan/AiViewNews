"""Fixed prompt templates. Only JSON output is accepted."""
from __future__ import annotations

EXTRACTION_SYSTEM = """你是新闻事件抽取器。只输出一个 JSON 对象，不要输出解释、Markdown 代码块或任何多余文字。
JSON 结构必须是：
{"events":[{"event_text":"事件的一句话事实描述","event_time":"YYYY-MM-DD 或 null","source_quote":"原文逐字片段"}]}

硬性要求：
1. 只抽取与用户查询直接相关的事件；完全无关时返回 {"events":[]}。
2. event_time 必须是绝对日期，统一写成 YYYY-MM-DD；只能确定到月份时写 YYYY-MM-01；无法确定时填 null。禁止使用"近日""上周"等相对时间。
3. source_quote 必须逐字复制给定文本中的原句，不超过 120 个字符，不得改写、概括或拼接。
4. 不得编造事件、日期或引用。每条事件必须有原文依据。
"""


def extraction_messages(query: str, text: str) -> list[dict]:
    return [
        {"role": "system", "content": EXTRACTION_SYSTEM},
        {"role": "user", "content": "查询：" + query + "\n\n待抽取文本：\n" + text},
    ]


def repair_messages(
    query: str, text: str, invalid_items: list, errors: list[str]
) -> list[dict]:
    summary = "；".join(errors[:8])
    return [
        {"role": "system", "content": EXTRACTION_SYSTEM},
        {
            "role": "user",
            "content": (
                "查询：" + query
                + "\n\n待抽取文本：\n" + text
                + "\n\n以下条目未通过校验：" + str(invalid_items)
                + "\n错误摘要：" + summary
                + "\n请只返回修正后的完整 JSON（仍使用 events 数组），不要重复已经合格的条目。"
            ),
        },
    ]


def timeline_messages(events: list[dict]) -> list[dict]:
    lines = []
    for event in events:
        lines.append((event.get("event_time") or "时间不详") + "｜" + event["event_text"])
    return [
        {
            "role": "system",
            "content": (
                "你是新闻时间线编辑。只输出 JSON：{\"timeline_summary\":\"不超过300字的摘要\"}。"
                "摘要必须按时间顺序概括事件脉络，不得加入原文没有的事实。"
            ),
        },
        {"role": "user", "content": "事件列表：\n" + "\n".join(lines)},
    ]


def report_messages(query: str, events: list[dict]) -> list[dict]:
    lines = []
    for event in events:
        lines.append((event.get("event_time") or "时间不详") + "｜" + event["event_text"])
    return [
        {
            "role": "system",
            "content": (
                "你是新闻分析报告撰写者。只输出 JSON："
                '{"title":"报告标题","sections":[{"heading":"事件概述","content":"..."}]}。'
                "sections 必须严格包含且只包含六段，标题依次为：事件概述、关键节点、各方立场、"
                "影响分析、趋势预测、不确定性说明。趋势预测必须标注为推断，不得写成确定事实；"
                "所有内容必须基于给定事件，不得编造。"
            ),
        },
        {
            "role": "user",
            "content": "用户查询：" + query + "\n相关事件：\n" + "\n".join(lines),
        },
    ]

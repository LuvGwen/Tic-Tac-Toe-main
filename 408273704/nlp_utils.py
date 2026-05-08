import re
from collections import Counter


STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "is", "are", "am",
    "was", "were", "be", "been", "being", "to", "of", "in", "on", "for",
    "with", "as", "by", "at", "from", "this", "that", "these", "those",
    "it", "its", "i", "you", "he", "she", "we", "they", "me", "him",
    "her", "us", "them", "my", "your", "our", "their", "have", "has",
    "had", "do", "does", "did", "not", "so", "very", "can", "could",
    "would", "should", "will", "just", "about", "there", "here", "hello",
    "hi", "ok", "okay", "yes", "no",
    "的", "了", "是", "我", "你", "他", "她", "它", "我们", "你们", "他们",
    "这个", "那个", "然后", "但是", "因为", "所以", "可以", "就是", "一下"
}


def clean_chat_line(line):
    line = re.sub(r"\[(Positive|Neutral|Negative)\]", "", line)
    line = re.sub(r"^\[[^\]]+\]", "", line)
    line = re.sub(r"^System:.*$", "", line)
    return line.strip()


def extract_keywords(lines, limit=8):
    text = " ".join(clean_chat_line(line) for line in lines)
    english_tokens = re.findall(r"[a-zA-Z][a-zA-Z']+", text.lower())
    chinese_tokens = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    tokens = english_tokens + chinese_tokens

    useful_tokens = [
        token
        for token in tokens
        if len(token) > 1 and token not in STOP_WORDS
    ]

    return [word for word, count in Counter(useful_tokens).most_common(limit)]


def summarize_chat(lines, max_sentences=3):
    cleaned_lines = [
        clean_chat_line(line)
        for line in lines
        if clean_chat_line(line)
    ]

    if not cleaned_lines:
        return "No chat messages to summarize yet."

    keywords = extract_keywords(cleaned_lines, limit=6)
    selected = cleaned_lines[-max_sentences:]
    summary = "Recent discussion: " + " / ".join(selected)

    if keywords:
        summary += "\nMain keywords: " + ", ".join(keywords)

    return summary

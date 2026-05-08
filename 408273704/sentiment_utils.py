import re


POSITIVE_WORDS = {
    "good", "great", "awesome", "excellent", "amazing", "nice", "happy",
    "love", "like", "win", "winner", "cool", "fun", "thanks", "thank",
    "perfect", "best", "wonderful", "fantastic", "enjoy", "excited",
    "哈哈", "开心", "喜欢", "赢", "棒", "好", "谢谢", "厉害", "不错"
}

NEGATIVE_WORDS = {
    "bad", "sad", "angry", "hate", "terrible", "awful", "lose", "loser",
    "wrong", "boring", "annoying", "upset", "mad", "worse", "worst",
    "fail", "failed", "failure", "problem", "sorry",
    "难过", "生气", "讨厌", "输", "差", "糟糕", "失败", "问题", "烦"
}


def _tokens(text):
    english_tokens = re.findall(r"[a-zA-Z']+", text.lower())
    chinese_hits = []

    for word in POSITIVE_WORDS | NEGATIVE_WORDS:
        if any("\u4e00" <= char <= "\u9fff" for char in word) and word in text:
            chinese_hits.append(word)

    return english_tokens + chinese_hits


def analyze_sentiment(text):
    tokens = _tokens(text)
    positive_count = sum(1 for token in tokens if token in POSITIVE_WORDS)
    negative_count = sum(1 for token in tokens if token in NEGATIVE_WORDS)
    score = positive_count - negative_count

    if score > 0:
        return "Positive"
    if score < 0:
        return "Negative"
    return "Neutral"


def format_sentiment_label(text):
    return f"[{analyze_sentiment(text)}]"

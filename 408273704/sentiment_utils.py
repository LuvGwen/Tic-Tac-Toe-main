import re

try:
    from textblob import TextBlob
except ImportError:
    TextBlob = None


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

NEGATION_WORDS = {
    "not", "no", "never", "none", "neither", "nor", "cannot", "cant",
    "can't", "dont", "don't", "doesnt", "doesn't", "didnt", "didn't",
    "isnt", "isn't", "arent", "aren't", "wasnt", "wasn't", "werent",
    "weren't", "wont", "won't", "wouldnt", "wouldn't", "shouldnt",
    "shouldn't", "couldnt", "couldn't", "hardly", "rarely", "seldom",
    "不", "没", "没有", "别", "不是", "不喜欢", "讨厌"
}


def _normalize_text(text):
    return text.lower().replace("‘", "'").replace("’", "'")


def _tokens(text):
    normalized_text = _normalize_text(text)
    english_tokens = re.findall(r"[a-zA-Z']+", normalized_text)
    chinese_hits = []

    for word in POSITIVE_WORDS | NEGATIVE_WORDS:
        if any("\u4e00" <= char <= "\u9fff" for char in word) and word in normalized_text:
            chinese_hits.append(word)

    return english_tokens + chinese_hits


def _has_recent_negation(tokens, index, window_size=3):
    start = max(0, index - window_size)
    return any(token in NEGATION_WORDS for token in tokens[start:index])


def _rule_based_score(text):
    tokens = _tokens(text)
    score = 0

    for index, token in enumerate(tokens):
        if token in POSITIVE_WORDS:
            score += -1 if _has_recent_negation(tokens, index) else 1
        elif token in NEGATIVE_WORDS:
            score += 1 if _has_recent_negation(tokens, index) else -1

    return score


def _label_from_score(score):
    if score > 0:
        return "Positive 😊"
    if score < 0:
        return "Negative 😡"
    return "Neutral 😐"


def analyze_sentiment(text):
    rule_score = _rule_based_score(text)

    # TextBlob is the main implementation recommended by the bonus guide.
    # The rule score still handles common negation cases like "I don't like this game".
    if TextBlob is not None:
        polarity = TextBlob(text).sentiment.polarity

        if rule_score != 0:
            return _label_from_score(rule_score)
        if polarity > 0.1:
            return "Positive 😊"
        if polarity < -0.1:
            return "Negative 😡"
        return "Neutral 😐"

    return _label_from_score(rule_score)


def format_sentiment_label(text):
    return f"[{analyze_sentiment(text)}]"

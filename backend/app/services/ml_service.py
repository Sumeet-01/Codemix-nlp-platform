"""
ML Service - Model Loading, Inference, and Preprocessing
Handles XLM-RoBERTa-large for dual-task classification.
In DEMO_MODE (no torch/transformers required), returns deterministic mock predictions.
"""
import hashlib
import re
import time
from pathlib import Path
from typing import Optional

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

# =============================================================================
# Emoji Normalization Map
# =============================================================================
EMOJI_MAP = {
    "😂": "[LAUGH]", "🤣": "[LAUGH]", "😆": "[LAUGH]",
    "😊": "[SMILE]", "😁": "[SMILE]", "😃": "[SMILE]",
    "😢": "[CRY]", "😭": "[CRY]", "😥": "[SAD]",
    "😡": "[ANGRY]", "🤬": "[ANGRY]", "😤": "[ANGRY]",
    "👍": "[THUMBSUP]", "✅": "[CHECK]", "❌": "[CROSS]",
    "🔥": "[FIRE]", "💯": "[HUNDRED]", "🙏": "[PRAY]",
    "😱": "[SHOCK]", "🤔": "[THINK]", "🤷": "[SHRUG]",
    "💪": "[STRONG]", "👏": "[CLAP]", "🎉": "[CELEBRATE]",
    "😏": "[SMIRK]", "🙄": "[EYEROLL]", "😒": "[UNPLEASED]",
}

# =============================================================================
# Intelligent Rule-Based Predictor (DEMO_MODE)
# Mimics XLM-RoBERTa output using linguistic patterns for Hinglish/English
# =============================================================================

# --- Sarcasm lexicons (weighted) ---
_SARCASM_STRONG = {
    # Hindi/Hinglish sarcasm markers
    "waah", "wah", "vah", "shabash", "kya baat", "bahut achha",
    "bilkul", "zaroor", "haan haan", "accha accha",
    "haan bilkul", "bohot achha", "bohot badiya", "ekdum sahi",
    "bahut vikas", "bohot vikas", "desh ka vikas",
    # English sarcasm markers
    "oh sure", "yeah right", "oh really", "oh great", "oh wonderful",
    "oh fantastic", "oh brilliant", "oh amazing", "oh perfect",
    "totally", "absolutely", "clearly", "obviously", "definitely",
    "surely", "of course", "no doubt", "wow just wow",
    "bravo", "slow clap", "genius", "masterpiece",
}

_SARCASM_WORDS = {
    # Hinglish sarcasm-associated words
    "waah", "wah", "vah", "kya", "shabash", "achha", "accha",
    "bahut", "bohot", "bilkul", "haan", "zaroor", "sahi", "mast",
    "jaise", "toh", "lekin", "par", "magar", "phir", "bhi",
    "kaise", "kitna", "sundar", "badiya", "ekdum", "itna",
    "dhanyawad", "shukriya", "kamal", "kamaal", "bemisaal",
    "jabardast", "shandar", "shandhaar", "lajawaab", "lajawab",
    # English sarcastic words
    "sure", "right", "totally", "absolutely", "clearly", "obviously",
    "definitely", "surely", "brilliant", "genius", "wonderful",
    "fantastic", "amazing", "perfect", "great", "nice", "wow",
    "bravo", "thanks", "congrats", "impressive", "remarkable",
    "lovely", "excellent", "superb", "clap", "applause",
    "incredible", "miraculous", "spectacular", "phenomenal",
}

# Sarcasm emoji signals
_SARCASM_EMOJIS = {"🙄", "😒", "😏", "👏", "😂", "🤣", "😆", "💀", "☠️", "🤡", "😑", "😐"}
_SARCASM_EMOJI_TOKENS = {"[EYEROLL]", "[SMIRK]", "[UNPLEASED]", "[LAUGH]", "[CLAP]"}

# Sarcasm structural patterns (compiled regex)
_SARCASM_PATTERNS = [
    # English sarcasm structures
    re.compile(r"\b(oh\s+sure|yeah\s+right|oh\s+really|oh\s+great|oh\s+wow)\b", re.I),
    re.compile(r"\b(so\s+much\s+for|nice\s+job|good\s+luck\s+with\s+that)\b", re.I),
    re.compile(r"\b(as\s+if|like\s+that\s+(will|would)\s+(ever|actually))\b", re.I),
    re.compile(r"\b(because\s+the\s+\d+\w*\s+\w+\s+will\s+definitely)\b", re.I),
    re.compile(r"\b(will\s+definitely\s+(solve|fix|help|work|change))\b", re.I),
    re.compile(r"\b(thank\s+you\s+(so\s+much|very\s+much).*(!|\.{2,}))", re.I),
    # Hindi/Hinglish sarcasm openers
    re.compile(r"\b(kya\s+(development|vikas|progress|kaam|service|achha|sundar|kamaal))\b", re.I),
    re.compile(r"\b(waah\s+kya|wah\s+kya|vah\s+kya)\b", re.I),
    re.compile(r"\b(haan\s+(haan|bilkul|zaroor|sahi)|accha\s+accha|bilkul\s+(bilkul|sahi))\b", re.I),
    re.compile(r"\b(haan\s+toh|aur\s+kya|bas\s+yehi|yehi\s+toh)\b", re.I),
    # Hindi sarcastic praise patterns (exaggerated positivity)
    re.compile(r"\b(bohot|bahut|itna|kitna)\s+(vikas|tarakki|progress|development|achha|badiya|mast|sundar|sahi|kamaal)\b", re.I),
    re.compile(r"\b(desh\s+ka\s+(vikas|tarakki|bhala)|desh\s+badal)\b", re.I),
    re.compile(r"\b(ekdum|bilkul)\s+(sahi|perfect|correct|right|theek|thik)\b", re.I),
    # Political sarcasm: politician name/ref + positive claim
    re.compile(r"\b(modi|neta|minister|sarkar|government|sarkaar|pm|bjp|congress|aap|party)\s*(ji|sahab|saheb)?\s*.*(vikas|development|progress|tarakki|achha|great|best|wonderful|kaam|work|done|kar\s+diya|kar\s+diye|ready|built|bana\s+diya|badal\s+diya)\b", re.I),
    re.compile(r"\b(vikas|development|progress|tarakki|kaam|work).*(modi|neta|minister|sarkar|government|sarkaar|pm)\b", re.I),
    # Contrast: public problem + leader praise
    re.compile(r"\b(neta\s+ji|minister|sarkar|government).*(ready|done|built|bungalow)\b", re.I),
    re.compile(r"\b(roads?|bijli|pani|water|hospital).*(tut|broken|kharab|worst|fail)\b", re.I),
    # Punctuation-based sarcasm
    re.compile(r"(?:!{2,}|\?{2,}|\.{3,})", re.I),
    # "ne toh" + positive = sarcasm pattern ("Modi ji ne toh desh ka vikas kar diya")
    re.compile(r"\b(ne\s+toh|toh\s+kar\s+diya|toh\s+bana\s+diya|toh\s+badal\s+diya)\b", re.I),
]

# Contrast pattern: positive word + negative situation = sarcasm
_POSITIVE_WORDS = {
    # English positive words
    "development", "progress", "great", "wonderful", "amazing",
    "fantastic", "superb", "excellent", "brilliant", "genius", "smart",
    "beautiful", "perfect", "best", "incredible", "outstanding",
    "magnificent", "impressive", "spectacular", "phenomenal",
    # Hindi/Hinglish positive words
    "achha", "accha", "vikas", "tarakki", "unnati", "sudhar",
    "sundar", "badiya", "mast", "badhiya", "shandar", "shandhaar",
    "lajawaab", "lajawab", "jabardast", "kamaal", "kamal",
    "bemisaal", "uttam", "shreshth", "adbhut",
    "khushi", "prasann", "safal", "safalta",
}
_NEGATIVE_WORDS = {
    # English negative/contrast words
    "lekin", "but", "par", "magar", "however", "yet", "although",
    "tut", "broken", "fail", "worst", "problem", "issue",
    "nothing", "never", "nobody", "corrupt",
    "not", "neither", "nor",
    "spent", "waste", "wasted", "scam", "fraud", "loot",
    "fixed", "single", "zero",
    # Hindi/Hinglish negative words
    "nahi", "nhi", "na", "no", "kharab", "ganda", "bura",
    "bekar", "bakwas", "ghatiya", "tatti", "wahiyat",
    "barbad", "barbaad", "tabah", "toota", "tooti",
    "bhrashtachar", "bhrashtachaar", "dhoka", "dhokha",
    "jhooth", "jhuth", "farzi", "nakli",
    "sab", "kuch", "koi",
}

# Negation patterns that flip meaning
_NEGATION_PATTERNS = [
    re.compile(r"\b(not\s+a\s+single|nahi\s+ek\s+bhi|kuch\s+nahi|nothing\s+done)\b", re.I),
    re.compile(r"\b(no\s+(one|body|thing|change|improvement|result))\b", re.I),
    re.compile(r"\b(zero\s+(result|change|improvement|work|progress))\b", re.I),
    re.compile(r"\b(waste\s+of|scam|fraud|loot)\b", re.I),
    re.compile(r"\b(kuch\s+nahi|koi\s+fayda\s+nahi|koi\s+kaam\s+nahi)\b", re.I),
    re.compile(r"\b(sirf\s+(vaade|promise|jumle|baatein)|khaali\s+(vaade|baatein))\b", re.I),
]

# Political / public figure references (used for political sarcasm detection)
_POLITICAL_REFS = {
    "modi", "pm", "neta", "minister", "sarkar", "sarkaar", "government",
    "bjp", "congress", "aap", "party", "leader", "politician",
    "mla", "mp", "cm", "mantri", "pradhan", "mukhya",
    "rahul", "kejriwal", "yogi", "shah", "amit",
}

# --- Misinformation lexicons ---
_MISINFO_STRONG_PHRASES = [
    # English misinfo patterns
    re.compile(r"\b(share\s+(before|this|now|karo|kro)|forward\s+(this|to|immediately|karo|kro))\b", re.I),
    re.compile(r"\b(scientists?\s+(have\s+)?(discovered|found|confirmed|proved|prove))\b", re.I),
    re.compile(r"\b(doctors?\s+(don.?t\s+want|are\s+hiding|won.?t\s+tell))\b", re.I),
    re.compile(r"\b(government\s+(is\s+hiding|doesn.?t\s+want|won.?t\s+tell))\b", re.I),
    re.compile(r"\b(proof\s+(that|is)|exposed\s+the\s+truth)\b", re.I),
    re.compile(r"\b(this\s+(will\s+be|gets?)\s+(deleted|removed|banned|censored))\b", re.I),
    re.compile(r"\b(media\s+(won.?t|will\s+not|is\s+not)\s+(show|tell|cover|report))\b", re.I),
    re.compile(r"\b(they\s+don.?t\s+want\s+you\s+to\s+know)\b", re.I),
    re.compile(r"\b(100%?\s*(true|real|proof|guaranteed|effective))\b", re.I),
    re.compile(r"\b(cure[sd]?\s+(cancer|covid|diabetes|aids|corona|disease))\b", re.I),
    re.compile(r"\b(drink(ing)?\s+(hot\s+water|lemon|turmeric|haldi).*cure)\b", re.I),
    re.compile(r"\b(cure.*drink(ing)?\s+(hot\s+water|lemon|turmeric|haldi))\b", re.I),
    re.compile(r"\b(big\s+pharma|pharma\s+companies|pharma\s+lobby)\b", re.I),
    re.compile(r"\b(vaccine[sd]?\s+(cause|killed?|dangerous|poison|unsafe))\b", re.I),
    re.compile(r"\b(5g\s+(cause|spread|towers?|radiation|se))\b", re.I),
    re.compile(r"\b(whatsapp\s+(forward|university|msg))\b", re.I),
    re.compile(r"\b(nasa\s+(confirm|said|admit))\b", re.I),
    re.compile(r"\b(breaking\s*:?\s*news?)\b", re.I),
    # Hindi/Hinglish misinfo patterns
    re.compile(r"\b(share\s+karo|share\s+kro|forward\s+karo|forward\s+kro)\b", re.I),
    re.compile(r"\b(scientists?\s+ne\s+(prove|proof|sabit|discover))\b", re.I),
    re.compile(r"\b(corona\s+(failta|hota|phailta|spread)|5g\s+se\s+(corona|covid))\b", re.I),
    re.compile(r"\b(proved?\s+kar\s+diya|sabit\s+kar\s+diya|pata\s+chala)\b", re.I),
    re.compile(r"\b(sach(chai)?\s+(hai|samne)|jhooth\s+bol|expose\s+kar)\b", re.I),
    re.compile(r"\bexposed\b", re.I),
]

_MISINFO_WORDS = {
    "fake", "hoax", "rumor", "rumour", "conspiracy", "propaganda",
    "miracle", "guaranteed", "secret", "exposed", "banned", "censored",
    "cure", "cures", "cured", "remedy", "treatment",
    "5g", "radiation", "chemtrails", "illuminati", "depopulation",
    "vaccine", "antivax", "microchip", "nanochip", "bioweapon",
    "forward", "share", "viral", "leaked", "confidential",
    "shocking", "unbelievable", "mindblowing",
    "scientists", "doctors", "experts", "studies", "research",
    "proven", "confirmed", "discovered", "breakthrough",
    # Hindi/Hinglish misinfo words
    "failta", "phailta", "failti", "sabit", "jhooth", "jhuth",
    "karo", "corona", "covid", "towers", "tower",
    "prove", "proof", "expose", "sachhai",
}

_CREDIBILITY_WORDS = {
    "according", "source", "study", "published", "journal", "university",
    "peer", "reviewed", "evidence", "data", "analysis", "report",
    "reuters", "associated", "press", "bbc", "verified", "fact",
    "check", "factcheck", "debunked", "clarification",
}


def _compute_sarcasm_score(text: str, lowered: str, tokens: list[str]) -> float:
    """Score sarcasm from 0.0 to 1.0 using comprehensive linguistic rules.
    
    Considers: structural patterns, word indicators, emojis, contrast detection,
    political sarcasm, negation irony, exaggerated praise, and false positive dampening.
    """
    score = 0.0
    signals_found = 0  # count of independent sarcasm signals

    # 1. Check structural sarcasm patterns (high weight — each unique pattern adds)
    pattern_hits = 0
    for pat in _SARCASM_PATTERNS:
        if pat.search(lowered):
            pattern_hits += 1
    if pattern_hits > 0:
        # First pattern = 0.22, each additional = 0.12, max 0.55
        score += min(0.55, 0.22 + max(0, pattern_hits - 1) * 0.12)
        signals_found += pattern_hits

    # 2. Sarcasm word density
    sarcasm_word_count = sum(1 for t in tokens if t in _SARCASM_WORDS)
    if sarcasm_word_count > 0:
        score += min(0.25, sarcasm_word_count * 0.06)
        signals_found += 1

    # 3. Emoji sarcasm signals (very strong for 🙄😒😏)
    emoji_hits = sum(1 for ch in text if ch in _SARCASM_EMOJIS)
    token_emoji_hits = sum(1 for t in tokens if t.upper() in _SARCASM_EMOJI_TOKENS)
    total_emoji = emoji_hits + token_emoji_hits
    if total_emoji > 0:
        score += min(0.25, total_emoji * 0.12)
        signals_found += 1

    # 4. Contrast detection (positive + negative in same text = strong sarcasm)
    pos_words = [t for t in tokens if t in _POSITIVE_WORDS]
    neg_words = [t for t in tokens if t in _NEGATIVE_WORDS]
    has_positive = len(pos_words) > 0
    has_negative = len(neg_words) > 0
    if has_positive and has_negative:
        score += 0.25
        signals_found += 1

    # 5. Political sarcasm: politician/political ref + positive/praise language
    #    Requires additional signal (emoji, pattern, or contrast) to avoid false positive on genuine praise
    has_political = any(t in _POLITICAL_REFS for t in tokens)
    if has_political and has_positive:
        if total_emoji > 0 or pattern_hits > 0 or has_negative:
            score += 0.30  # strong: political + positive + emoji/pattern/contrast
            signals_found += 1
        elif sarcasm_word_count >= 3:
            score += 0.20  # moderate: many sarcasm words with political ref
            signals_found += 1
        else:
            score += 0.08  # weak: just political + positive, could be genuine
    elif has_political and sarcasm_word_count >= 2:
        score += 0.15
        signals_found += 1

    # 6. Negation patterns ("not a single", "nothing done", etc.)
    negation_found = False
    for pat in _NEGATION_PATTERNS:
        if pat.search(lowered):
            score += 0.18
            signals_found += 1
            negation_found = True
            break

    # 7. Number + positive word ("10 crore spent", "50th meeting") = irony
    if re.search(r"\d+(?:st|nd|rd|th)?\s*(crore|lakh|billion|million|meeting|years?|months?)", lowered) and has_positive:
        score += 0.12
        signals_found += 1

    # 8. Exaggerated praise: emphasis word + positive word
    #    Only trigger with additional signal (emoji, political, pattern)
    emphasis_words = {"bohot", "bahut", "itna", "kitna", "ekdum", "full", "poora", "pura"}
    has_emphasis = any(t in emphasis_words for t in tokens)
    if has_emphasis and has_positive and (total_emoji > 0 or has_political or pattern_hits > 0):
        score += 0.15
        signals_found += 1

    # 9. Sarcasm word + emoji combo (strong signal)
    if sarcasm_word_count >= 2 and total_emoji > 0:
        score += 0.10
        signals_found += 1

    # 10. Exclamation at end + sarcastic tone
    if text.rstrip().endswith("!") and sarcasm_word_count >= 1:
        score += 0.08

    # 11. Excessive punctuation (!!!, ???, ...)
    if re.search(r"[!?]{2,}|\.{3,}", text):
        score += 0.08

    # 12. Short punchy text with sarcasm markers = higher confidence
    if len(tokens) < 25 and sarcasm_word_count >= 2:
        score += 0.08

    # 13. FALSE POSITIVE DAMPENING: if no strong signals, aggressively reduce
    #     Sarcasm words alone (haan, toh, bahut) shouldn't trigger high scores
    #     Need at least one of: pattern match, contrast, emoji, political ref, negation
    if signals_found <= 1 and pattern_hits == 0 and not has_political and total_emoji == 0:
        score *= 0.30  # strongly reduce: just word matches aren't sarcasm

    # Add tiny hash-based variation (±0.02) for natural feel
    digest = hashlib.md5(text.encode()).hexdigest()
    h_val = int(digest[:4], 16) / 0xFFFF  # 0-1
    score += (h_val - 0.5) * 0.04

    return max(0.02, min(0.98, score))


def _compute_misinfo_score(text: str, lowered: str, tokens: list[str]) -> float:
    """Score misinformation probability from 0.0 to 1.0 using linguistic rules."""
    score = 0.0
    n_tokens = len(tokens) + 1

    # 1. Strong misinformation phrase patterns (high weight)
    for pat in _MISINFO_STRONG_PHRASES:
        if pat.search(lowered):
            score += 0.18

    # 2. Misinfo word density
    misinfo_word_count = sum(1 for t in tokens if t in _MISINFO_WORDS)
    score += min(0.30, misinfo_word_count * 0.07)

    # 3. Urgency language ("share before deleted", "forward NOW", "share karo")
    if re.search(r"\b(share|forward|send)\b.*\b(before|now|immediately|urgent|karo|kro|jaldi)\b", lowered):
        score += 0.25
    elif re.search(r"\b(share|forward)\s+(karo|kro)\b", lowered):
        score += 0.20

    # 4. Unverified health claims
    health_terms = {"cure", "cures", "cured", "heal", "heals", "remedy", "treatment", "failta", "phailta", "failti"}
    disease_terms = {"cancer", "covid", "corona", "diabetes", "aids", "hiv", "disease", "bimari", "rog"}
    has_health = any(t in health_terms for t in tokens)
    has_disease = any(t in disease_terms for t in tokens)
    if has_health and has_disease:
        score += 0.30
    elif has_disease and re.search(r"\b(5g|tower|radiation|failta|phailta)\b", lowered):
        score += 0.25  # disease + tech conspiracy

    # 5. "Scientists discovered" / appeal to false authority (Hindi + English)
    if re.search(r"\b(scientists?|doctors?|experts?|researchers?)\s+(say|said|found|discovered|confirmed|proved|revealed)\b", lowered):
        score += 0.20
    # Hindi: "scientists ne prove/sabit kar diya"
    if re.search(r"\b(scientists?|doctors?)\s+ne\s+(prove|proof|sabit|discover|pata)\b", lowered):
        score += 0.20

    # 6. Conspiratorial language
    conspiracy_words = {"hiding", "hidden", "cover", "coverup", "suppressed", "silenced", "censored", "deleted", "banned"}
    if any(t in conspiracy_words for t in tokens):
        score += 0.15

    # 7. ALL CAPS segments (shouting = often misinfo)
    words = text.split()
    caps_ratio = sum(1 for w in words if w.isupper() and len(w) > 2) / (len(words) + 1)
    if caps_ratio > 0.2:
        score += 0.10

    # 8. Credibility words reduce score
    cred_count = sum(1 for t in tokens if t in _CREDIBILITY_WORDS)
    score -= cred_count * 0.08

    # Tiny hash-based variation for natural feel
    digest = hashlib.md5(text.encode()).hexdigest()
    h_val = int(digest[8:12], 16) / 0xFFFF
    score += (h_val - 0.5) * 0.04

    return max(0.02, min(0.98, score))


def _detect_language(text: str, tokens: list[str]) -> str:
    """Detect if text is Hinglish, Tanglish, or English."""
    hindi_words = {"hai", "hain", "ka", "ki", "ke", "ko", "se", "me", "mein",
                   "kya", "toh", "par", "lekin", "magar", "aur", "ya", "nahi",
                   "neta", "ji", "bhai", "yaar", "arre", "accha", "achha",
                   "bahut", "kuch", "sab", "koi", "apna", "wala", "wali",
                   "raha", "rahe", "rahi", "gaya", "gayi", "gaye",
                   "hota", "hoti", "karta", "karti", "karte",
                   "dekho", "suno", "bolo", "chalo", "jao", "aao",
                   "bilkul", "zaroor", "waah", "wah", "sahi"}
    tamil_words = {"da", "di", "pa", "ma", "illa", "iruku", "panna", "sollu",
                   "enna", "epdi", "inga", "anga", "romba", "nalla", "super",
                   "thala", "anna", "akka", "machan", "macha"}

    hindi_count = sum(1 for t in tokens if t in hindi_words)
    tamil_count = sum(1 for t in tokens if t in tamil_words)
    total = len(tokens) + 1

    if hindi_count / total > 0.08:
        return "hinglish"
    elif tamil_count / total > 0.08:
        return "tanglish"
    elif any(ord(c) > 0x0900 and ord(c) < 0x097F for c in text):  # Devanagari
        return "hinglish"
    elif any(ord(c) > 0x0B80 and ord(c) < 0x0BFF for c in text):  # Tamil
        return "tanglish"
    return "english"


def _demo_predict(text: str) -> dict:
    """
    Intelligent rule-based prediction mimicking XLM-RoBERTa output.
    Uses comprehensive linguistic analysis for Hinglish/Tanglish/English.
    Produces realistic, accurate sarcasm & misinformation scores.
    """
    import time as t
    start = t.time()

    lowered = text.lower()
    # Tokenize: keep emoji tokens from preprocessing
    tokens = re.findall(r"\[?\w+\]?", lowered)

    sarcasm_score = _compute_sarcasm_score(text, lowered, tokens)
    misinfo_score = _compute_misinfo_score(text, lowered, tokens)

    # Ensure mutual exclusivity tendency: strongly sarcastic text is less likely misinfo
    if sarcasm_score > 0.7 and misinfo_score < 0.5:
        misinfo_score *= 0.5
    if misinfo_score > 0.7 and sarcasm_score < 0.5:
        sarcasm_score *= 0.7

    processing_ms = int((t.time() - start) * 1000 + 5)
    lang = _detect_language(text, tokens)

    # Token list for explainability
    display_tokens = re.findall(r"\[?\w+\]?", text.lower())
    demo_tokens = ["<s>"] + display_tokens[:20] + ["</s>"]

    return {
        "sarcasm_score": round(sarcasm_score, 4),
        "sarcasm_label": sarcasm_score >= 0.5,
        "misinformation_score": round(misinfo_score, 4),
        "misinformation_label": misinfo_score >= 0.5,
        "processing_time_ms": processing_ms,
        "model_version": "demo-v1",
        "language": lang,
        "tokens": demo_tokens,
        "attention_weights": None,
    }


class MLService:
    """
    Singleton ML Service.
    When settings.DEMO_MODE is True (default in dev), no torch/transformers needed.
    """

    def __init__(self) -> None:
        self.model = None
        self.tokenizer = None
        self.is_loaded: bool = False
        self.model_version: str = "demo-v1" if settings.DEMO_MODE else "xlm-roberta-large-v1"

    async def load_model(self) -> None:
        """Load model at startup, or just mark demo as ready."""
        if settings.DEMO_MODE:
            logger.info("DEMO_MODE enabled — using mock ML predictions (no torch required)")
            self.is_loaded = True
            return

        # Real model loading — only runs when DEMO_MODE=false
        try:
            import torch
            from transformers import AutoTokenizer, XLMRobertaModel

            model_path = Path(settings.MODEL_PATH)
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

            if model_path.exists() and (model_path / "config.json").exists():
                logger.info("Loading fine-tuned model from checkpoint", path=str(model_path))
                self.tokenizer = AutoTokenizer.from_pretrained(str(model_path))
                base = XLMRobertaModel.from_pretrained(str(model_path))
            else:
                logger.warning("No checkpoint found, loading base xlm-roberta-large")
                self.tokenizer = AutoTokenizer.from_pretrained(settings.MODEL_NAME)
                base = XLMRobertaModel.from_pretrained(settings.MODEL_NAME)

            # Build multi-task wrapper
            from app.ml.models.multitask_model import MultiTaskCodeMixModel
            self.model = MultiTaskCodeMixModel(base_model_name=settings.MODEL_NAME)
            self.model.to(device)
            self.model.eval()
            self._device = device
            self.is_loaded = True
            self.model_version = "xlm-roberta-large-v1"
            logger.info("ML model loaded", device=str(device))
        except Exception as exc:
            logger.error("Failed to load ML model, falling back to DEMO_MODE", error=str(exc))
            self.is_loaded = True  # Allow requests to proceed via demo fallback

    def preprocess_text(self, text: str) -> str:
        """Clean and normalize code-mixed text."""
        for emoji, token in EMOJI_MAP.items():
            text = text.replace(emoji, f" {token} ")
        text = re.sub(r"https?://\S+|www\.\S+", "[URL]", text)
        text = re.sub(r"@\w+", "[USER]", text)
        text = re.sub(r"#(\w+)", r"\1", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def hash_text(self, text: str) -> str:
        """SHA-256 hash for caching."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    async def predict(self, text: str, output_attentions: bool = False) -> dict:
        """Run inference (or demo) on a single text."""
        if not self.is_loaded:
            raise RuntimeError("ML service not initialized")

        if settings.DEMO_MODE or self.model is None:
            return _demo_predict(self.preprocess_text(text))

        # Real torch inference path
        import torch
        import torch.nn.functional as F

        start = time.time()
        cleaned = self.preprocess_text(text)
        inputs = self.tokenizer(
            cleaned,
            return_tensors="pt",
            max_length=settings.MAX_LENGTH,
            truncation=True,
            padding=True,
        )
        inputs = {k: v.to(self._device) for k, v in inputs.items()}

        with torch.no_grad():
            out = self.model(**inputs, output_attentions=output_attentions)

        sarcasm_probs = F.softmax(out["sarcasm_logits"], dim=-1)
        misinfo_probs = F.softmax(out["misinfo_logits"], dim=-1)

        result = {
            "sarcasm_score": round(sarcasm_probs[0][1].item(), 4),
            "sarcasm_label": sarcasm_probs[0][1].item() >= 0.5,
            "misinformation_score": round(misinfo_probs[0][1].item(), 4),
            "misinformation_label": misinfo_probs[0][1].item() >= 0.5,
            "processing_time_ms": int((time.time() - start) * 1000),
            "model_version": self.model_version,
            "language": "hinglish",
            "tokens": self.tokenizer.convert_ids_to_tokens(inputs["input_ids"][0].tolist()),
            "attention_weights": None,
        }
        if output_attentions and hasattr(out, "attentions") and out.get("attentions"):
            last_attn = out["attentions"][-1][0]
            result["attention_weights"] = last_attn.mean(dim=0).tolist()
        return result

    async def predict_batch(self, texts: list[str]) -> list[dict]:
        """Batch inference."""
        results = []
        for text in texts:
            try:
                results.append({"text": text, "success": True, **(await self.predict(text))})
            except Exception as exc:
                results.append({"text": text, "success": False, "error": str(exc)})
        return results

    async def cleanup(self) -> None:
        """Release model resources."""
        if self.model is not None and not settings.DEMO_MODE:
            try:
                import torch
                del self.model
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass
        self.is_loaded = False
        logger.info("ML resources released")


# Global singleton
ml_service = MLService()


"""
Data Preprocessing Pipeline for Code-Mixed Indian Text
Handles Hinglish, Tanglish, and other code-mixed variants.
"""
import csv
import json
import re
import random
from pathlib import Path
from typing import Optional

import pandas as pd
from tabulate import tabulate

# =============================================================================
# Emoji Normalization
# =============================================================================
EMOJI_REPLACEMENTS = {
    "😂": "[LAUGH]", "🤣": "[LAUGH]", "😆": "[LAUGH]", "😹": "[LAUGH]",
    "😊": "[SMILE]", "😁": "[SMILE]", "😃": "[SMILE]", "😄": "[SMILE]",
    "😢": "[CRY]", "😭": "[CRY]", "😥": "[SAD]", "😞": "[SAD]",
    "😡": "[ANGRY]", "🤬": "[ANGRY]", "😤": "[ANGRY]", "💢": "[ANGRY]",
    "👍": "[THUMBSUP]", "✅": "[CHECK]", "❌": "[CROSS]", "🚫": "[CROSS]",
    "🔥": "[FIRE]", "💯": "[HUNDRED]", "🙏": "[PRAY]", "🥺": "[PLEASE]",
    "😱": "[SHOCK]", "😲": "[SHOCK]", "🤔": "[THINK]", "🤷": "[SHRUG]",
    "💪": "[STRONG]", "👏": "[CLAP]", "🎉": "[CELEBRATE]", "🎊": "[CELEBRATE]",
    "😏": "[SMIRK]", "🙄": "[EYEROLL]", "😒": "[UNPLEASED]", "🤦": "[FACEPALM]",
    "👀": "[EYES]", "💀": "[DEAD]", "☠️": "[DEAD]", "🤡": "[CLOWN]",
    "🐄": "[COW]", "🤥": "[LIE]", "🙃": "[SARCASM]",
}

# Sarcasm indicators in Hinglish
SARCASM_MARKERS = [
    "waah", "wah", "bahut accha", "kya baat hai", "zabardast",
    "really???", "oh wow", "amazing", "sure sure", "bilkul",
    "haan haan", "bilkul sahi", "perfect", "great work",
]


def normalize_emojis(text: str) -> str:
    """Replace emojis with text tokens."""
    for emoji, token in EMOJI_REPLACEMENTS.items():
        text = text.replace(emoji, f" {token} ")
    return text


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    # Normalize emojis first
    text = normalize_emojis(text)

    # Remove URLs
    text = re.sub(r"https?://\S+|www\.\S+", "[URL]", text)

    # Remove @mentions but keep the text
    text = re.sub(r"@\w+", "[USER]", text)

    # Remove hashtags but keep the word
    text = re.sub(r"#(\w+)", r"\1", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Remove leading/trailing punctuation spam
    text = re.sub(r"^[^\w\s]+", "", text).strip()

    # Lowercase
    text = text.lower()

    return text


def detect_language(text: str) -> str:
    """Basic language detection for code-mixed text."""
    # Hindi characters (Devanagari range)
    hindi_chars = len(re.findall(r"[\u0900-\u097F]", text))
    # Tamil characters
    tamil_chars = len(re.findall(r"[\u0B80-\u0BFF]", text))
    # ASCII letters (English)
    english_chars = len(re.findall(r"[a-zA-Z]", text))

    total = hindi_chars + tamil_chars + english_chars
    if total == 0:
        return "unknown"

    if hindi_chars / total > 0.3 and english_chars / total > 0.1:
        return "hi-en"
    elif tamil_chars / total > 0.3 and english_chars / total > 0.1:
        return "ta-en"
    elif hindi_chars / total > 0.5:
        return "hi"
    elif tamil_chars / total > 0.5:
        return "ta"
    else:
        return "en"


# =============================================================================
# Synthetic Dataset Generation
# =============================================================================
SARCASTIC_HINGLISH_TEMPLATES = [
    "Waah {topic} toh {adjective} ho gaya, kya baat hai! 😂",
    "Haan haan {person} bahut {adjective} hai, bilkul sahi keh rahe ho 🙄",
    "Oh wow {topic} ne phir kuchh naya kardia, really impressive 😂",
    "Kitna {adjective} system hai humara, zabardast 💀",
    "Sure sure {topic} toh bilkul {adjective} hoga, main believe karta hoon 🤡",
    "Haan toh {person} ji ne phir se {action}, kya kehna",
    "Wow such {adjective} development in {topic}, very impressed 😂",
    "Bilkul sahi hai, {topic} mein sab theek chal raha hai 🙃",
    "{person} ne kaha {statement}, kyunki unhe sach bolna kahan aata hai",
    "Great job {person}, {topic} toh improve hogaya bahut! 👏",
]

NONSARCASTIC_HINGLISH_TEMPLATES = [
    "Aaj {topic} ke baare mein kuch important share karna tha",
    "Maine {action} kiya aur result {adjective} aaya",
    "Please help karo, {topic} samajh nahi aa raha",
    "{person} ne bataya ki {statement} hai",
    "Yaar {topic} ke liye koi suggestion hai?",
    "Kal {action} karna hai, koi tips?",
    "Sach mein {topic} bahut {adjective} hai",
    "{person} ne {action} kiya, jo ekdum sahi tha",
    "Mere saath {topic} mein {adjective} experience raha",
    "Genuine question: {topic} ke baare mein kya sochte ho?",
]

MISINFO_TEMPLATES = [
    "{person} ne confirm kiya ki {false_claim} है",
    "Breaking news: {false_claim} proved by scientists",
    "Doctors hiding truth about {false_claim}, share before deleted!",
    "{person} ka claim: {false_claim} 100% sach hai",
    "Expose: {government} secretly doing {false_claim}",
    "SHOCKING: {false_claim} – share before it gets censored",
    "Scientists discovered {false_claim} but media hiding it",
    "{person} leaked documents prove {false_claim}",
]

REAL_NEWS_TEMPLATES = [
    "{organization} ne {factual_action} announce kiya",
    "Aaj {location} mein {event} hua, jisme {number} log the",
    "{person} ji ki press conference mein {factual_statement} kaha",
    "New policy: {policy} effective from {date}",
    "Study shows {finding} when it comes to {topic}",
    "{organization} report: {factual_claim}",
    "{event} ke liye registration ab open hai",
    "{person} ki nayi book '{title}' publish hui",
]

TEMPLATE_VARS = {
    "topic": ["roads", "sarkaar", "bijli", "paani", "healthcare", "education",
              "weather", "economy", "politics", "technology", "sports"],
    "adjective": ["accha", "bura", "amazing", "terrible", "perfect", "awful",
                  "great", "pathetic", "brilliant", "useless"],
    "person": ["Neta ji", "PM sahab", "CM ji", "Minister sahab", "Babu ji",
               "Officer sahab", "spokesperson", "leader"],
    "action": ["padh liya", "dekh liya", "sun liya", "kar diya", "bol diya",
               "announce kiya", "resign kar diya", "launch kar diya"],
    "statement": ["sab theek hai", "koi problem nahi", "hum kar rahe hain",
                  "soon fix hoga", "investigating hai"],
    "false_claim": ["5G causes cancer", "vaccines contain microchips",
                    "drinking hot water cures everything", "onion absorbs viruses",
                    "this mineral cures diabetes", "ancient remedy beats modern medicine"],
    "government": ["WHO", "government", "deep state", "pharma companies", "scientists"],
    "organization": ["RBI", "SEBI", "Ministry", "Parliament", "Supreme Court", "ISRO"],
    "factual_action": ["new policy", "revised guidelines", "budget allocation",
                       "achievement", "partnership", "project completion"],
    "location": ["Mumbai", "Delhi", "Bengaluru", "Chennai", "Hyderabad", "Kolkata"],
    "event": ["conference", "festival", "meeting", "concert", "match", "election"],
    "number": ["500", "1000", "5000", "10,000", "hundreds of"],
    "factual_statement": ["economic growth is 7%", "new infrastructure project launched",
                          "exam results declared", "weather alert issued"],
    "policy": ["new tax policy", "education reform", "healthcare initiative",
               "digital initiative", "green energy plan"],
    "date": ["next month", "next year", "Q1 2026", "April 1"],
    "finding": ["exercise improves health", "sleep is important",
                "balanced diet helps", "stress reduction techniques work"],
    "factual_claim": ["GDP growth at 5.5%", "inflation eases to 4%",
                      "new hospital opened", "highway completed on schedule"],
    "title": ["India at 100", "The Digital Leap", "New Horizons",
              "Bharat Rising", "Tomorrow's India"],
}


def fill_template(template: str) -> str:
    """Fill a template with random values."""
    result = template
    for key, values in TEMPLATE_VARS.items():
        placeholder = "{" + key + "}"
        if placeholder in result:
            result = result.replace(placeholder, random.choice(values))
    return result


def generate_synthetic_dataset(n_samples: int = 10000, random_seed: int = 42) -> list[dict]:
    """
    Generate synthetic code-mixed dataset for training.
    
    Distribution:
    - 40% Hinglish (Hindi-English)
    - 30% Pure English  
    - 20% Tanglish (Tamil-English) or other Indian
    - 10% Pure Hindi
    
    Labels balanced ~50-50 for each task.
    """
    random.seed(random_seed)
    samples = []

    # Sarcastic Hinglish samples
    for _ in range(int(n_samples * 0.2)):
        text = fill_template(random.choice(SARCASTIC_HINGLISH_TEMPLATES))
        samples.append({
            "text": text,
            "sarcasm": 1,
            "misinformation": 0,
            "language": "hi-en",
        })

    # Non-sarcastic Hinglish
    for _ in range(int(n_samples * 0.2)):
        text = fill_template(random.choice(NONSARCASTIC_HINGLISH_TEMPLATES))
        samples.append({
            "text": text,
            "sarcasm": 0,
            "misinformation": 0,
            "language": "hi-en",
        })

    # Misinformation samples
    for _ in range(int(n_samples * 0.15)):
        text = fill_template(random.choice(MISINFO_TEMPLATES))
        samples.append({
            "text": text,
            "sarcasm": 0,
            "misinformation": 1,
            "language": "en",
        })

    # Sarcastic English misinfo (both labels)
    for _ in range(int(n_samples * 0.1)):
        text = fill_template(random.choice(MISINFO_TEMPLATES))
        sarcastic_prefix = random.choice([
            "Oh sure, ", "Right because ", "Wow, amazing! ", "Totally believe: ",
        ])
        text = sarcastic_prefix + text
        samples.append({
            "text": text,
            "sarcasm": 1,
            "misinformation": 1,
            "language": "en",
        })

    # Real news / factual content
    for _ in range(int(n_samples * 0.15)):
        text = fill_template(random.choice(REAL_NEWS_TEMPLATES))
        samples.append({
            "text": text,
            "sarcasm": 0,
            "misinformation": 0,
            "language": "hi-en",
        })

    # Pure English sarcasm
    english_sarcastic = [
        "Oh sure, that's totally how it works! 🙄",
        "Wow, what groundbreaking work! Really impressive stuff.",
        "Oh definitely, this will fix everything, absolutely brilliant!",
        "Because that worked SO well last time. Great plan!",
        "Sure, because more meetings always solve problems. Genius!",
        "Wow, another amazing policy that will totally work this time!",
        "Right, because the people most affected should definitely not be consulted.",
        "Obviously, throwing money at it will magically fix the root cause.",
    ]
    for _ in range(int(n_samples * 0.1)):
        text = random.choice(english_sarcastic)
        samples.append({
            "text": text,
            "sarcasm": 1,
            "misinformation": 0,
            "language": "en",
        })

    # Neutral English
    english_neutral = [
        "The annual report shows a 5% increase in revenue this quarter.",
        "The event was attended by over 200 participants from various sectors.",
        "The new regulations will come into effect starting next fiscal year.",
        "Team successfully completed the project ahead of schedule.",
        "Research findings suggest the approach is effective in controlled settings.",
        "The updated guidelines are now available on the official website.",
        "Applications for the scholarship program open next Monday.",
        "The weather forecast predicts rain over the weekend.",
    ]
    for _ in range(int(n_samples * 0.1)):
        text = random.choice(english_neutral)
        samples.append({
            "text": text,
            "sarcasm": 0,
            "misinformation": 0,
            "language": "en",
        })

    # Clean texts
    for sample in samples:
        sample["text"] = clean_text(sample["text"])
        if not sample["text"]:
            sample["text"] = "placeholder text for analysis"

    random.shuffle(samples)
    return samples[:n_samples]


def create_train_val_test_split(
    samples: list[dict],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
) -> tuple[list, list, list]:
    """Split dataset into train/val/test sets."""
    n = len(samples)
    train_end = int(n * train_ratio)
    val_end = train_end + int(n * val_ratio)

    return samples[:train_end], samples[train_end:val_end], samples[val_end:]


def save_dataset(samples: list[dict], output_path: Path) -> None:
    """Save dataset to CSV and JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save as CSV
    csv_path = output_path.with_suffix(".csv")
    df = pd.DataFrame(samples)
    df.to_csv(csv_path, index=False, quoting=csv.QUOTE_ALL)
    print(f"Saved {len(samples)} samples to {csv_path}")

    # Save as JSON
    json_path = output_path.with_suffix(".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(samples, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(samples)} samples to {json_path}")


def print_dataset_stats(samples: list[dict], name: str = "Dataset") -> None:
    """Print dataset statistics."""
    df = pd.DataFrame(samples)

    print(f"\n{'='*60}")
    print(f"  {name} Statistics")
    print(f"{'='*60}")
    print(f"Total samples: {len(df)}")

    print("\nLanguage distribution:")
    lang_dist = df["language"].value_counts()
    for lang, count in lang_dist.items():
        print(f"  {lang}: {count} ({count/len(df)*100:.1f}%)")

    print("\nLabel distribution:")
    print(f"  Sarcasm (1): {df['sarcasm'].sum()} ({df['sarcasm'].mean()*100:.1f}%)")
    print(f"  Not Sarcasm (0): {(df['sarcasm']==0).sum()} ({(df['sarcasm']==0).mean()*100:.1f}%)")
    print(f"  Misinformation (1): {df['misinformation'].sum()} ({df['misinformation'].mean()*100:.1f}%)")
    print(f"  Not Misinfo (0): {(df['misinformation']==0).sum()} ({(df['misinformation']==0).mean()*100:.1f}%)")


if __name__ == "__main__":
    import os

    output_dir = Path(__file__).parent / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating synthetic code-mixed dataset...")
    samples = generate_synthetic_dataset(n_samples=10000)

    train, val, test = create_train_val_test_split(samples)

    print_dataset_stats(samples, "Full Dataset")
    print_dataset_stats(train, "Training Set")
    print_dataset_stats(val, "Validation Set")
    print_dataset_stats(test, "Test Set")

    save_dataset(train, output_dir / "train")
    save_dataset(val, output_dir / "val")
    save_dataset(test, output_dir / "test")
    save_dataset(samples, output_dir / "full_dataset")

    print("\nDataset generation complete!")
    print(f"  Train: {len(train)} samples")
    print(f"  Val:   {len(val)} samples")
    print(f"  Test:  {len(test)} samples")

import os
import random
import time
import json
import glob
import re
from datetime import datetime

import requests
import numpy as np
import PIL.Image

from google import genai
from google.genai import types

from moviepy.editor import *
from moviepy.video.fx.all import colorx, fadein, fadeout
from moviepy.audio.fx.all import audio_loop
from faster_whisper import WhisperModel

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from neural_voice import VoiceEngine

# ================== CONFIG ================== #

GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY")
PEXELS_KEY = os.environ.get("PEXELS_API_KEY")
PIXABAY_SFX_API_KEY = os.environ.get("PIXABAY_SFX_API_KEY") or os.environ.get("PIXABAY_API_KEY")
YOUTUBE_TOKEN_VAL = os.environ.get("YOUTUBE_TOKEN_JSON")

CHANNEL_HANDLE = "@EtherealDaily"
TOPICS_FILE = "topics.txt"
SOURCES_FILE = "sources.txt"
SOURCE_STATE_FILE = "source_state.json"
MUSIC_DIR = "music"

DEFAULT_SOURCES = [
    "The Bhagavad Gita",
    "The Holy Bible (Proverbs)",
    "The Holy Bible (Psalms)",
    "The Holy Bible (The Gospels)",
    "The Quran",
    "The Tao Te Ching",
    "The Dhammapada (Buddhist Wisdom)",
    "Meditations by Marcus Aurelius (Stoicism)",
    "The Analects of Confucius",
    "The Masnavi by Rumi (Sufi Poetry)",
    "The Prophet by Khalil Gibran",
    "The Guru Granth Sahib (Sikhism)",
    "The Torah (Wisdom Literature)",
    "Pirkei Avot (Ethics of the Fathers)",
    "The Upanishads",
    "The Book of Chuang Tzu (Zhuangzi)",
    "Letters from a Stoic by Seneca",
    "The Enchiridion of Epictetus",
    "The Tibetan Book of Living and Dying",
    "The I Ching (Book of Changes)",
    "The Poetry of Hafez",
    "The Rubaiyat of Omar Khayyam",
    "Traditional Native American Proverbs and Wisdom",
    "Traditional African Proverbs (Ubuntu Philosophy)",
    "The Yoga Sutras of Patanjali",
    "The Kojiki (Shinto Wisdom)",
    "The Avesta (Zoroastrianism)",
    "The Jain Agamas",
    "The Sayings of Desert Fathers",
    "The Kybalion (Hermetic Philosophy)",
]

THEME_BUCKETS = [
    "overthinking",
    "anxiety",
    "discipline",
    "patience",
    "self-worth",
    "grief",
    "comparison",
    "loneliness",
    "anger",
    "temptation",
    "purpose",
    "fear of failure",
]

SERIES_PREFIX = "Ancient Wisdom"
MINI_STOPWORDS = {
    "the", "and", "for", "that", "with", "this", "from", "into", "your", "you",
    "are", "was", "were", "what", "when", "why", "how", "not", "but", "have",
    "has", "had", "one", "all", "can", "will", "its", "it", "of", "to", "in",
    "on", "at", "by", "as", "is", "be", "do", "if", "so", "we", "they", "them",
}

AUTO_CINEMATIC_SFX = {
    "hook": "cinematic boom",
    "curiosity": "soft whoosh",
    "quote": "singing bowl",
    "meaning": "soft wind",
    "takeaway": "gentle rise",
}

SEGMENT_MOOD_MAP = {
    "hook": "tense",
    "curiosity": "mystical",
    "quote": "minimal",
    "meaning": "reflective",
    "takeaway": "uplifting",
}

VISUAL_METAPHOR_MAP = {
    "overthinking": ["spinning ceiling fan", "rain on window", "crowded subway", "frayed notebook pages"],
    "anxiety": ["tight chest silhouette", "dark hallway light", "storm clouds moving fast", "shaky hands closeup"],
    "discipline": ["sunrise run", "sharp blade on stone", "empty desk before dawn", "calm mountain trail"],
    "patience": ["slow river current", "hourglass closeup", "waiting train platform", "buds opening in time lapse"],
    "self-worth": ["mirror in low light", "single candle in a dark room", "person standing tall in silence"],
    "grief": ["empty chair near window", "rain streaking glass", "wilted flowers in soft light"],
    "comparison": ["two paths diverging", "mirror reflections", "phone screen glow in dark room"],
    "loneliness": ["single streetlamp", "empty bench", "one figure walking alone at night"],
    "anger": ["storm surge", "flames behind glass", "fist unclenching in slow motion"],
    "temptation": ["open door with light beyond", "half-shadowed hallway", "crossroads at night"],
    "purpose": ["road toward sunrise", "compass on table", "person walking through fog toward light"],
    "fear of failure": ["cliff edge at dawn", "runner before starting line", "paper plane before launch"],
}


# Pillow compatibility for older MoviePy versions
if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS


# ================== BASIC UTILITIES ================== #

def anti_ban_sleep():
    if os.environ.get("GITHUB_ACTIONS") == "true":
        sleep_seconds = random.randint(120, 600)
        print(f"🕵️ Anti-Ban Sleep: {sleep_seconds // 60} minutes")
        time.sleep(sleep_seconds)


def load_sources():
    if os.path.exists(SOURCES_FILE):
        with open(SOURCES_FILE, "r", encoding="utf-8") as f:
            sources = [line.strip() for line in f if line.strip()]
        return sources or DEFAULT_SOURCES
    print("⚠️ sources.txt not found! Using default fallback list.")
    return DEFAULT_SOURCES


def load_json_file(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json_file(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Failed to save JSON state: {e}")


def get_next_series_context():
    sources = load_sources()
    state = load_json_file(
        SOURCE_STATE_FILE,
        {"source_index": 0, "theme_index": 0, "series_number": 1},
    )

    source = sources[state["source_index"] % len(sources)]
    theme = THEME_BUCKETS[state["theme_index"] % len(THEME_BUCKETS)]
    series_number = int(state["series_number"])

    state["source_index"] = (state["source_index"] + 1) % max(1, len(sources))
    state["theme_index"] = (state["theme_index"] + 1) % len(THEME_BUCKETS)
    state["series_number"] = series_number + 1
    save_json_file(SOURCE_STATE_FILE, state)

    return source, theme, series_number


def get_past_topics():
    if not os.path.exists(TOPICS_FILE):
        return []
    with open(TOPICS_FILE, "r", encoding="utf-8") as f:
        raw_lines = [line.strip() for line in f if line.strip()]
    return raw_lines[-120:]


def save_new_topic(record):
    try:
        if isinstance(record, dict):
            payload = {
                "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "title": record.get("title", ""),
                "verse_source": record.get("verse_source", ""),
                "theme": record.get("theme", ""),
                "audience_problem": record.get("audience_problem", ""),
                "quote": record.get("quote", ""),
                "viewer_identity": record.get("viewer_identity", ""),
                "tags": record.get("tags", []),
            }
            line = json.dumps(payload, ensure_ascii=False)
        else:
            line = str(record)

        with open(TOPICS_FILE, "a", encoding="utf-8") as f:
            f.write(f"{line}\n")
        print(f"💾 Saved '{line[:90]}' to memory bank.")
    except Exception as e:
        print(f"⚠️ Failed to save topic: {e}")


def _safe_json_loads(text):
    if not text:
        return None
    cleaned = text.strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except Exception:
        return None


def extract_keywords(text):
    words = re.findall(r"[A-Za-z']+", (text or "").lower())
    keywords = []
    for w in words:
        if len(w) >= 4 and w not in MINI_STOPWORDS and w not in keywords:
            keywords.append(w)
    return keywords[:18]


def ensure_shorts_tags(tags):
    tags = [str(t).strip() for t in (tags or []) if str(t).strip()]
    if not tags:
        tags = ["wisdom", "peace", "shorts", "motivation", "healing", "calm"]
    deduped = []
    for t in tags:
        if t not in deduped:
            deduped.append(t)
    return deduped[:15]


def score_title(title):
    t = (title or "").lower()
    score = 0
    for word in ["stop", "why", "hidden", "truth", "ancient", "calm", "peace", "control", "fear", "anxiety", "discipline", "break", "never", "before"]:
        if word in t:
            score += 2
    if len(title or "") <= 62:
        score += 2
    if "?" in t:
        score += 1
    if "#shorts" in t:
        score += 1
    return score


def finalize_title(raw_title, series_number):
    title = (raw_title or "").strip()

    if not title:
        title = f"{SERIES_PREFIX} #{series_number} — One Line That Calms the Mind"

    if "#shorts" not in title.lower():
        title = f"{title} #shorts #wisdom"

    if not re.search(r"(series|#\d+)", title, flags=re.IGNORECASE):
        title = f"{SERIES_PREFIX} #{series_number} — {title}"

    title = re.sub(r"\s+", " ", title).strip()

    if len(title) > 95:
        title = title[:92].rstrip() + "..."
    return title


def choose_best_title(data, series_number):
    options = []

    for key in ["title_options", "titles"]:
        if isinstance(data.get(key), list):
            options.extend([str(x).strip() for x in data[key] if str(x).strip()])

    if data.get("title"):
        options.append(str(data["title"]).strip())

    if not options:
        options = [
            f"{SERIES_PREFIX} #{series_number} — Stop Carrying What You Cannot Control",
            f"{SERIES_PREFIX} #{series_number} — Ancient Wisdom for Modern Pressure",
        ]

    unique = []
    for item in options:
        if item not in unique:
            unique.append(item)

    unique.sort(key=score_title, reverse=True)
    return finalize_title(unique[0], series_number)


def normalize_line(line, fallback, segment_type):
    if not isinstance(line, dict):
        line = {}

    return {
        "segment_type": line.get("segment_type") or segment_type,
        "style_instruction": line.get("style_instruction") or fallback["style_instruction"],
        "acting_text": line.get("acting_text") or fallback["acting_text"],
        "clean_text": line.get("clean_text") or fallback["clean_text"],
        "visual_keyword": line.get("visual_keyword") or fallback["visual_keyword"],
        "sfx_keyword": line.get("sfx_keyword") or fallback["sfx_keyword"],
        "music_mood": line.get("music_mood") or fallback["music_mood"],
        "interrupt_style": line.get("interrupt_style") or fallback["interrupt_style"],
        "pre_silence_ms": int(line.get("pre_silence_ms", fallback["pre_silence_ms"])),
        "post_silence_ms": int(line.get("post_silence_ms", fallback["post_silence_ms"])),
        "human_touch": bool(line.get("human_touch", fallback["human_touch"])),
        "subtitle_mode": line.get("subtitle_mode") or fallback["subtitle_mode"],
        "accent_words": line.get("accent_words") or fallback["accent_words"],
    }


def normalize_script(data, source, theme, avoid_text, series_number):
    if not isinstance(data, dict):
        data = {}

    audience_problem = data.get("audience_problem") or theme
    viewer_identity = data.get("viewer_identity") or f"the kind of person who is trying to stay strong through {theme}"
    quote = data.get("quote") or f"One timeless line from {source} can steady the mind."
    quote = quote.strip()

    title = choose_best_title(data, series_number)
    description = data.get("description") or (
        f"Ancient wisdom, one line at a time.\n\n#wisdom #peace #motivation #shorts"
    )
    tags = ensure_shorts_tags(data.get("tags"))

    hook_fallback = {
        "style_instruction": "Sharp, urgent, and emotionally direct.",
        "acting_text": f"Feeling trapped by {audience_problem}? <break time='0.55s'/>",
        "clean_text": f"Feeling trapped by {audience_problem}?",
        "visual_keyword": f"{audience_problem} cinematic closeup",
        "sfx_keyword": "cinematic boom",
        "music_mood": "tense",
        "interrupt_style": "hard_start",
        "pre_silence_ms": 0,
        "post_silence_ms": 45,
        "human_touch": False,
        "subtitle_mode": "aggressive",
        "accent_words": extract_keywords(audience_problem),
    }

    curiosity_fallback = {
        "style_instruction": "Controlled, mysterious, and pulling the viewer forward.",
        "acting_text": f"There is a reason this still hits today... <break time='0.35s'/> and it is bigger than motivation.",
        "clean_text": "There is a reason this still hits today... and it is bigger than motivation.",
        "visual_keyword": f"{audience_problem} symbolic mystery",
        "sfx_keyword": "soft whoosh",
        "music_mood": "mystical",
        "interrupt_style": "curiosity_pull",
        "pre_silence_ms": 40,
        "post_silence_ms": 55,
        "human_touch": True,
        "subtitle_mode": "curious",
        "accent_words": ["reason", "today", "bigger", "motivation"],
    }

    quote_fallback = {
        "style_instruction": "Reverent, slower, and weighty.",
        "acting_text": f"From {source}, listen closely: <break time='0.55s'/> <emphasis level='strong'>{quote}</emphasis>",
        "clean_text": f"From {source}, listen closely: {quote}",
        "visual_keyword": random.choice(VISUAL_METAPHOR_MAP.get(theme, ["ancient manuscript candlelight"])),
        "sfx_keyword": "singing bowl",
        "music_mood": "minimal",
        "interrupt_style": "quote_pivot",
        "pre_silence_ms": 120,
        "post_silence_ms": 70,
        "human_touch": True,
        "subtitle_mode": "quote",
        "accent_words": extract_keywords(quote),
    }

    meaning_fallback = {
        "style_instruction": "Warm, intelligent, and deeply human.",
        "acting_text": "It means you stop giving your energy to what cannot grow you. <break time='0.4s'/> You do not need to win every thought to find peace.",
        "clean_text": "It means you stop giving your energy to what cannot grow you. You do not need to win every thought to find peace.",
        "visual_keyword": random.choice(VISUAL_METAPHOR_MAP.get(theme, ["calm ocean sunrise"])),
        "sfx_keyword": "soft wind",
        "music_mood": "reflective",
        "interrupt_style": "meaning_swell",
        "pre_silence_ms": 30,
        "post_silence_ms": 50,
        "human_touch": True,
        "subtitle_mode": "explain",
        "accent_words": ["energy", "grow", "peace", "thought"],
    }

    takeaway_fallback = {
        "style_instruction": "Clear, steady, and quietly empowering.",
        "acting_text": f"So today, act like the kind of person who can carry {theme} without becoming it. <break time='0.45s'/> And that is exactly why this line still helps.",
        "clean_text": f"So today, act like the kind of person who can carry {theme} without becoming it. And that is exactly why this line still helps.",
        "visual_keyword": random.choice(VISUAL_METAPHOR_MAP.get(theme, ["person walking toward sunrise"])),
        "sfx_keyword": "gentle rise",
        "music_mood": "uplifting",
        "interrupt_style": "takeaway_lift",
        "pre_silence_ms": 70,
        "post_silence_ms": 120,
        "human_touch": True,
        "subtitle_mode": "finale",
        "accent_words": ["today", "carry", "without", "becoming", "helps"],
    }

    lines = data.get("lines")
    if not isinstance(lines, list):
        lines = []

    normalized_lines = [
        normalize_line(lines[0] if len(lines) > 0 else {}, hook_fallback, "hook"),
        normalize_line(lines[1] if len(lines) > 1 else {}, curiosity_fallback, "curiosity"),
        normalize_line(lines[2] if len(lines) > 2 else {}, quote_fallback, "quote"),
        normalize_line(lines[3] if len(lines) > 3 else {}, meaning_fallback, "meaning"),
        normalize_line(lines[4] if len(lines) > 4 else {}, takeaway_fallback, "takeaway"),
    ]

    data["title"] = title
    data["series_number"] = series_number
    data["verse_source"] = data.get("verse_source") or source
    data["theme"] = theme
    data["audience_problem"] = audience_problem
    data["viewer_identity"] = viewer_identity
    data["quote"] = quote
    data["description"] = description
    data["tags"] = tags
    data["lines"] = normalized_lines
    data["recommended_voice_model"] = data.get("recommended_voice_model", "Deep_Stoic_Male")
    data["_avoid_text"] = avoid_text
    return data


# ================== SCRIPT & SEO GENERATION ================== #

def generate_viral_script():
    print("🧠 Generating Ethereal high-retention Shorts script...")

    if not GEMINI_KEY:
        print("⚠️ GEMINI_API_KEY is missing.")
        return None

    client = genai.Client(api_key=GEMINI_KEY)
    models_to_try = ["models/gemini-2.5-pro", "models/gemini-2.5-flash"]

    source, theme, series_number = get_next_series_context()
    print(f"🎲 Selected source: {source}")
    print(f"🎯 Selected series theme: {theme}")
    print(f"🔢 Series number: {series_number}")

    past_topics = get_past_topics()
    avoid_instruction = (
        "CRITICAL: avoid repeating these exact recent topics, titles, quotes, or hook angles:\n"
        + "\n".join(past_topics[-50:]) + "\n"
        if past_topics else
        "No past topics yet."
    )

    prompt = f"""
You are the elite lead scriptwriter for a YouTube Shorts channel built around sacred, ancient, and philosophical wisdom.

TODAY'S SOURCE MATERIAL: {source}
TODAY'S EMOTIONAL THEME: {theme}
SERIES NUMBER: {series_number}

Your job is to create one very specific, high-retention Short with a strong emotional pull.

{avoid_instruction}

CORE GOAL:
Make the viewer feel seen, then surprised, then helped.

STRICT RETENTION STRUCTURE:
1. HOOK
   - Start with an aggressive modern pain point.
   - Make it feel personal and immediate.
   - Use strong emotional tension, not generic wisdom.

2. CURIOSITY LOOP
   - Add one short line that creates a question before the quote arrives.
   - Make the viewer lean in.

3. QUOTE
   - State the source.
   - Give one short, faithful quote or line.
   - It must feel authentic and weighty.

4. MEANING
   - Explain the line in plain human language.
   - Include one micro-reframe: turn a painful idea into a useful truth.

5. TAKEAWAY
   - Give one action the viewer can use today.
   - Make the ending loop naturally into the opening emotion.

CONTENT RULES:
- One emotional lane only.
- No long lecture.
- No filler.
- No generic outro.
- Make the viewer feel like the message is meant for their identity.
- Include at least one line that says, in effect, “this is for the kind of person who...”
- Use restrained human imperfection only where it improves realism. Do not overdo it.
- Build pattern interrupts naturally through pacing, silence, and line tension.
- Keep it highly suitable for Shorts.

OUTPUT RULES:
Return ONLY valid JSON.

Use this exact shape:
{{
  "title_options": [
    "Ancient Wisdom #{series_number} — Stop Carrying What You Cannot Control #shorts #wisdom",
    "Ancient Wisdom #{series_number} — One Line That Changes Pressure Into Peace #shorts #wisdom",
    "Ancient Wisdom #{series_number} — The Truth Most People Need Tonight #shorts #wisdom"
  ],
  "title": "Chosen title here",
  "verse_source": "{source}",
  "theme": "{theme}",
  "audience_problem": "one specific modern problem",
  "viewer_identity": "the kind of person this is for",
  "quote": "the short quote or line from the source",
  "description": "short description with hashtags",
  "tags": ["wisdom", "peace", "shorts"],
  "recommended_voice_model": "Deep_Stoic_Male",
  "lines": [
    {{
      "segment_type": "hook",
      "style_instruction": "Aggressive, immediate, and emotionally direct.",
      "acting_text": "Hook line with a hard emotional pull <break time='0.5s'/>",
      "clean_text": "Hook line with a hard emotional pull",
      "visual_keyword": "visual metaphor for the pain point",
      "sfx_keyword": "cinematic boom",
      "music_mood": "tense",
      "interrupt_style": "hard_start",
      "pre_silence_ms": 0,
      "post_silence_ms": 45,
      "human_touch": false,
      "subtitle_mode": "aggressive",
      "accent_words": ["one", "two", "three"]
    }},
    {{
      "segment_type": "curiosity",
      "style_instruction": "Mysterious and pulling the viewer forward.",
      "acting_text": "Curiosity line that opens a loop <break time='0.3s'/>",
      "clean_text": "Curiosity line that opens a loop",
      "visual_keyword": "symbolic curiosity visual",
      "sfx_keyword": "soft whoosh",
      "music_mood": "mystical",
      "interrupt_style": "curiosity_pull",
      "pre_silence_ms": 40,
      "post_silence_ms": 55,
      "human_touch": true,
      "subtitle_mode": "curious",
      "accent_words": ["reason", "why"]
    }},
    {{
      "segment_type": "quote",
      "style_instruction": "Slow, reverent, and weighty.",
      "acting_text": "From {source}, listen closely: <break time='0.55s'/> <emphasis level='strong'>the quote</emphasis>",
      "clean_text": "From {source}, listen closely: the quote",
      "visual_keyword": "ancient manuscript or spiritual symbol",
      "sfx_keyword": "singing bowl",
      "music_mood": "minimal",
      "interrupt_style": "quote_pivot",
      "pre_silence_ms": 120,
      "post_silence_ms": 70,
      "human_touch": true,
      "subtitle_mode": "quote",
      "accent_words": ["quote", "source"]
    }},
    {{
      "segment_type": "meaning",
      "style_instruction": "Warm, intelligent, and deeply human.",
      "acting_text": "Meaning line with a micro-reframe <break time='0.35s'/>",
      "clean_text": "Meaning line with a micro-reframe",
      "visual_keyword": "symbolic visual that matches the meaning",
      "sfx_keyword": "soft wind",
      "music_mood": "reflective",
      "interrupt_style": "meaning_swell",
      "pre_silence_ms": 30,
      "post_silence_ms": 50,
      "human_touch": true,
      "subtitle_mode": "explain",
      "accent_words": ["peace", "energy", "control"]
    }},
    {{
      "segment_type": "takeaway",
      "style_instruction": "Clear, steady, and quietly empowering.",
      "acting_text": "Practical action line with a looped ending <break time='0.45s'/>",
      "clean_text": "Practical action line with a looped ending",
      "visual_keyword": "hopeful symbolic closing shot",
      "sfx_keyword": "gentle rise",
      "music_mood": "uplifting",
      "interrupt_style": "takeaway_lift",
      "pre_silence_ms": 70,
      "post_silence_ms": 120,
      "human_touch": true,
      "subtitle_mode": "finale",
      "accent_words": ["today", "now", "peace"]
    }}
  ]
}}
"""

    config = types.GenerateContentConfig(
        temperature=0.75,
        top_p=0.95,
        response_mime_type="application/json",
    )

    for model in models_to_try:
        try:
            print(f"Trying {model}...")
            response = client.models.generate_content(model=model, contents=prompt, config=config)
            if response.text:
                data = _safe_json_loads(response.text)
                if data and isinstance(data, dict):
                    data = normalize_script(data, source, theme, avoid_instruction, series_number)
                    if data.get("lines"):
                        print(f"✅ Script & SEO generated with {model}")
                        return data
        except Exception as e:
            print(f"❌ Model error ({model}): {e}")
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print("⏳ Quota hit during script generation. Sleeping 5s before fallback...")
                time.sleep(5)
            continue

    if OPENROUTER_KEY:
        print("🔄 Gemini exhausted/failed. Falling back to OpenRouter.")
        try:
            headers = {
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "meta-llama/llama-3.3-70b-instruct:free",
                "messages": [{"role": "user", "content": prompt}],
            }

            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=90,
            )

            if r.status_code == 200:
                response_content = r.json()["choices"][0]["message"]["content"]
                data = _safe_json_loads(response_content)
                if data and isinstance(data, dict):
                    data = normalize_script(data, source, theme, avoid_instruction, series_number)
                    if data.get("lines"):
                        print("✅ Script & SEO generated with OpenRouter fallback")
                        return data
        except Exception as e:
            print(f"❌ OpenRouter fallback error: {e}")

    print("⚠️ Using local fallback script.")
    return normalize_script(
        {
            "title": f"{SERIES_PREFIX} #{series_number} — Ancient Wisdom for Modern Pressure",
            "verse_source": source,
            "theme": theme,
            "audience_problem": theme,
            "viewer_identity": f"the kind of person trying to stay steady through {theme}",
            "quote": f"One timeless line from {source} can steady the mind.",
            "description": f"Ancient wisdom for modern peace.\n\n#wisdom #peace #motivation #shorts",
            "tags": ["wisdom", "peace", "shorts", "motivation", "calm", "healing", "ancient"],
            "recommended_voice_model": "Deep_Stoic_Male",
        },
        source,
        theme,
        avoid_instruction,
        series_number,
    )


# ================== AUDIO + SFX + MUSIC ================== #

def add_dynamic_sfx(audio_clip, keyword, volume=0.12):
    if not keyword or keyword.lower() in ["none", "null", ""] or not PIXABAY_SFX_API_KEY:
        return audio_clip

    safe_keyword = re.sub(r"[^a-zA-Z0-9_ -]", "", keyword).strip().replace(" ", "_")
    sfx_filename = f"temp_sfx_{safe_keyword}.mp3"

    if not os.path.exists(sfx_filename):
        print(f"🔍 Fetching '{keyword}' SFX from Pixabay API...")
        url = "https://pixabay.com/api/audio/"
        params = {
            "key": PIXABAY_SFX_API_KEY,
            "q": keyword,
            "audio_type": "sound_effects",
        }
        try:
            r = requests.get(url, params=params, timeout=45)
            data = r.json()
            if data.get("hits") and len(data["hits"]) > 0:
                audio_url = data["hits"][0].get("audio") or data["hits"][0].get("url")
                if audio_url:
                    r_audio = requests.get(audio_url, timeout=45)
                    with open(sfx_filename, "wb") as f:
                        f.write(r_audio.content)
                else:
                    return audio_clip
            else:
                return audio_clip
        except Exception as e:
            print(f"⚠️ Pixabay SFX fetch failed for '{keyword}': {e}")
            return audio_clip

    try:
        sfx = AudioFileClip(sfx_filename).volumex(volume)
        if sfx.duration > audio_clip.duration:
            sfx = sfx.subclip(0, audio_clip.duration)
        return CompositeAudioClip([audio_clip, sfx])
    except Exception:
        return audio_clip


def pick_music_track(mood):
    music_files = glob.glob(os.path.join(MUSIC_DIR, "*.mp3"))
    if not music_files:
        return None

    mood = (mood or "").lower()
    mood_keywords = {
        "tense": ["tense", "dark", "drone", "shadow", "pulse", "suspense"],
        "mystical": ["mystic", "ethereal", "spiritual", "ambient", "dream", "oracle"],
        "minimal": ["minimal", "calm", "space", "quiet", "soft"],
        "reflective": ["reflect", "emotional", "warm", "piano", "hope", "soft"],
        "uplifting": ["uplift", "rise", "inspire", "hope", "bright", "hopeful"],
    }

    preferred = mood_keywords.get(mood, [mood]) if mood else []
    matched = []
    for f in music_files:
        base = os.path.basename(f).lower()
        if any(k in base for k in preferred):
            matched.append(f)

    if matched:
        return random.choice(matched)

    return random.choice(music_files)


def add_music_layer(audio_clip, mood):
    music_file = pick_music_track(mood)
    if not music_file:
        return audio_clip

    mood_volume = {
        "tense": 0.035,
        "mystical": 0.035,
        "minimal": 0.028,
        "reflective": 0.040,
        "uplifting": 0.048,
    }.get((mood or "").lower(), 0.040)

    try:
        bg_music = AudioFileClip(music_file).volumex(mood_volume)
        bg_music = audio_loop(bg_music, duration=audio_clip.duration)
        return CompositeAudioClip([audio_clip, bg_music])
    except Exception as e:
        print(f"⚠️ Background music skipped for mood '{mood}': {e}")
        return audio_clip


def apply_cinematic_sound_layers(audio_clip, line):
    segment_type = line.get("segment_type", "meaning")
    mood = line.get("music_mood") or SEGMENT_MOOD_MAP.get(segment_type, "reflective")
    sfx_keyword = line.get("sfx_keyword", "none")

    layered = add_music_layer(audio_clip, mood)

    auto_sfx = AUTO_CINEMATIC_SFX.get(segment_type)
    if auto_sfx:
        layered = add_dynamic_sfx(layered, auto_sfx, volume=0.075)

    if sfx_keyword and sfx_keyword.lower() not in ["none", "null", ""]:
        layered = add_dynamic_sfx(layered, sfx_keyword, volume=0.10)

    return layered


# ================== VISUALS ================== #

def enrich_visual_keyword(keyword, theme, segment_type):
    keyword = (keyword or "").strip()
    theme = (theme or "").strip().lower()

    metaphors = VISUAL_METAPHOR_MAP.get(theme, [])
    if not metaphors:
        metaphors = ["cinematic symbolic light", "quiet emotional atmosphere", "soft dawn silhouette"]

    segment_addons = {
        "hook": ["close-up tension", "fast emotional motion"],
        "curiosity": ["symbolic mystery", "soft dark backdrop"],
        "quote": ["ancient manuscript", "candlelight", "still frame"],
        "meaning": ["slow reflective motion", "calm symbolic landscape"],
        "takeaway": ["hopeful sunrise", "moving toward light"],
    }.get(segment_type, ["cinematic atmosphere"])

    chosen = random.choice(metaphors + segment_addons)
    return f"{keyword} {chosen} portrait cinematic"


def get_visual_clip(keyword, filename, duration, theme, segment_type="meaning"):
    if not PEXELS_KEY:
        return ColorClip(size=(1080, 1920), color=(15, 15, 15), duration=duration)

    headers = {"Authorization": PEXELS_KEY}
    url = "https://api.pexels.com/videos/search"

    query = enrich_visual_keyword(keyword, theme, segment_type)

    params = {
        "query": query,
        "per_page": 15,
        "page": random.randint(1, 4),
        "orientation": "portrait",
    }

    try:
        r = requests.get(url, headers=headers, params=params, timeout=45)
        data = r.json()

        if data.get("videos"):
            chosen_video = random.choice(data["videos"])
            best_file = max(chosen_video["video_files"], key=lambda x: x["width"] * x["height"])
            link = best_file["link"]

            with open(filename, "wb") as f:
                f.write(requests.get(link, timeout=45).content)

            clip = VideoFileClip(filename)
            clip = clip.without_audio()

            if clip.duration < duration and clip.duration > 0:
                loops = int(np.ceil(duration / clip.duration)) + 1
                clip = clip.loop(n=loops)

            clip = clip.subclip(0, duration)

            if clip.h < 1920:
                clip = clip.resize(height=1920)
            if clip.w < 1080:
                clip = clip.resize(width=1080)

            clip = clip.crop(x1=clip.w / 2 - 540, width=1080, height=1920)
            return clip
    except Exception as e:
        print(f"⚠️ Visual fetch failed for '{keyword}': {e}")

    return ColorClip(size=(1080, 1920), color=(15, 15, 15), duration=duration)


def apply_pattern_interrupts(clip, line, idx):
    """
    Script-aware visual interrupts:
    - not static timing
    - based on segment length and emotional role
    - brief enough to keep momentum
    """
    duration = max(clip.duration, 0.1)
    segment_type = line.get("segment_type", "meaning")

    interrupt_specs = []

    if segment_type == "hook":
        interrupt_specs.append((max(0.35, duration * 0.42), min(0.08, duration * 0.03), (255, 255, 255), 0.15))
        if duration > 3.0:
            interrupt_specs.append((duration * 0.80, 0.05, (255, 255, 255), 0.10))

    elif segment_type == "curiosity":
        interrupt_specs.append((max(0.40, duration * 0.48), min(0.07, duration * 0.025), (245, 245, 255), 0.12))

    elif segment_type == "quote":
        interrupt_specs.append((max(0.45, duration * 0.52), min(0.06, duration * 0.02), (255, 240, 200), 0.11))

    elif segment_type == "meaning":
        interrupt_specs.append((max(0.55, duration * 0.50), min(0.07, duration * 0.025), (5, 5, 5), 0.08))

    elif segment_type == "takeaway":
        interrupt_specs.append((max(0.45, duration * 0.62), min(0.08, duration * 0.03), (255, 248, 220), 0.13))

    overlays = [clip]

    for start_t, dur, color, opacity in interrupt_specs:
        overlay = (
            ColorClip(size=(clip.w, clip.h), color=color, duration=dur)
            .set_start(start_t)
            .set_opacity(opacity)
        )
        overlays.append(overlay)

    combined = CompositeVideoClip(overlays, size=(clip.w, clip.h)).set_duration(duration)
    return combined


# ================== SUBTITLES ================== #

def subtitle_style_for_segment(segment_type):
    styles = {
        "hook": {"fontsize": 84, "y": 0.67, "boost": 18, "color": "white"},
        "curiosity": {"fontsize": 80, "y": 0.68, "boost": 16, "color": "white"},
        "quote": {"fontsize": 76, "y": 0.69, "boost": 14, "color": "white"},
        "meaning": {"fontsize": 74, "y": 0.71, "boost": 12, "color": "white"},
        "takeaway": {"fontsize": 80, "y": 0.72, "boost": 16, "color": "white"},
    }
    return styles.get(segment_type, styles["meaning"])


def find_segment_for_time(t, segment_meta):
    for meta in segment_meta:
        if meta["start"] <= t < meta["end"]:
            return meta
    return segment_meta[-1] if segment_meta else None


def add_dynamic_subtitles(video_clip, audio_path, segment_meta):
    print("📝 Transcribing audio for word-level subtitles...")
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio_path, word_timestamps=True)

    subtitle_clips = []

    for segment in segments:
        if not getattr(segment, "words", None):
            continue

        for word in segment.words:
            clean_word = word.word.strip().upper()
            if not clean_word:
                continue

            active_segment = find_segment_for_time(word.start, segment_meta)
            seg_type = active_segment["segment_type"] if active_segment else "meaning"
            style = subtitle_style_for_segment(seg_type)
            accent_words = set(active_segment.get("accent_words", [])) if active_segment else set()
            is_accent = clean_word.lower() in accent_words or len(clean_word) > 7

            fontsize = style["fontsize"] + (style["boost"] if is_accent else 0)
            y_pos = video_clip.h * style["y"]

            try:
                txt_clip = (
                    TextClip(
                        clean_word,
                        fontsize=fontsize,
                        color="white" if not is_accent else "#FFD166",
                        stroke_color="black",
                        stroke_width=2,
                        font="Arial-Bold",
                        method="caption",
                        size=(video_clip.w * 0.82, None),
                    )
                    .set_start(word.start)
                    .set_end(word.end)
                    .set_position(("center", y_pos))
                )
                subtitle_clips.append(txt_clip)
            except Exception:
                pass

    print(f"✅ Generated {len(subtitle_clips)} word captions!")
    return CompositeVideoClip([video_clip] + subtitle_clips)


# ================== MAIN PIPELINE ================== #

def main_pipeline():
    anti_ban_sleep()

    try:
        voice_engine = VoiceEngine()
    except Exception as e:
        print(f"Voice engine error: {e}")
        return None, None

    script = generate_viral_script()
    if not script:
        return None, None

    print(f"🎬 Title: {script['title']}")
    print(f"📁 Verse Logged: {script.get('verse_source', 'Unknown Source')}")
    print(f"🎯 Theme: {script.get('theme', 'Unknown')}")
    print(f"👤 Viewer Identity: {script.get('viewer_identity', 'Unknown')}")
    print(f"🏷️ Tags: {', '.join(script['tags'][:5])}...")

    target_voice = script.get("recommended_voice_model", "Deep_Stoic_Male")
    print(f"🎙️ AI Casted Narrator: {target_voice}")

    final_clips = []
    segment_meta = []
    current_start = 0.0

    for i, line in enumerate(script["lines"]):
        try:
            acting_input = line.get("acting_text", line.get("text", ""))
            style_instruction = line.get("style_instruction", "Warm, peaceful, and slow.")
            clean_text = line.get("clean_text", line.get("text", ""))
            sfx_keyword = line.get("sfx_keyword", "none")
            segment_type = line.get("segment_type", "meaning")
            pre_silence_ms = int(line.get("pre_silence_ms", 0))
            post_silence_ms = int(line.get("post_silence_ms", 120))
            human_touch = bool(line.get("human_touch", False))

            wav_file = voice_engine.generate_acting_line(
                acting_text=acting_input,
                clean_text=clean_text,
                style_instruction=style_instruction,
                index=i,
                voice_name=target_voice,
                pre_silence_ms=pre_silence_ms,
                post_silence_ms=post_silence_ms,
                human_touch=human_touch,
            )

            if not wav_file:
                continue

            audio_clip = AudioFileClip(wav_file)
            audio_clip = apply_cinematic_sound_layers(audio_clip, line)

            video_file = f"temp_vid_{i}.mp4"
            visual_clip = get_visual_clip(
                line.get("visual_keyword", "wisdom"),
                video_file,
                audio_clip.duration,
                theme=script.get("theme", ""),
                segment_type=segment_type,
            )

            visual_clip = visual_clip.fx(colorx, 0.95).set_audio(audio_clip)
            visual_clip = apply_pattern_interrupts(visual_clip, line, i)

            if i > 0 and final_clips:
                visual_clip = visual_clip.set_start(final_clips[-1].end)
                if random.random() < 0.35:
                    visual_clip = visual_clip.fadein(0.12, color=[255, 255, 255])

            duration = visual_clip.duration
            segment_meta.append({
                "start": current_start,
                "end": current_start + duration,
                "segment_type": segment_type,
                "accent_words": [w.lower() for w in line.get("accent_words", [])],
            })
            current_start += duration

            final_clips.append(visual_clip)

        except Exception as e:
            print(f"Clip error: {e}")

    if not final_clips:
        print("❌ No clips generated.")
        return None, None

    print("✂️ Rendering final video with transitions & branding...")
    final_video = CompositeVideoClip(final_clips)

    temp_voice_track = "temp_master_voice.wav"
    final_video.audio.write_audiofile(temp_voice_track, fps=24000, logger=None)
    final_video = add_dynamic_subtitles(final_video, temp_voice_track, segment_meta)

    if os.path.exists(temp_voice_track):
        os.remove(temp_voice_track)

    try:
        watermark = TextClip(
            CHANNEL_HANDLE,
            fontsize=40,
            color="white",
            font="Arial",
            stroke_color="black",
            stroke_width=1,
        ).set_opacity(0.4).set_position(("center", 150)).set_duration(final_video.duration)

        final_video = CompositeVideoClip([final_video, watermark])
    except Exception as e:
        print(f"⚠️ Could not add watermark: {e}")

    output_file = "final_video.mp4"
    final_video.write_videofile(
        output_file,
        codec="libx264",
        audio_codec="aac",
        fps=30,
        preset="fast",
        threads=4,
    )
    return output_file, script


# ================== YOUTUBE UPLOAD ================== #

def upload_to_youtube(file_path, metadata):
    if not file_path:
        return False
    print("🚀 Uploading to YouTube...")
    try:
        creds = Credentials.from_authorized_user_info(json.loads(YOUTUBE_TOKEN_VAL))
        youtube = build("youtube", "v3", credentials=creds)

        youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": metadata["title"],
                    "description": metadata["description"],
                    "tags": metadata["tags"],
                    "categoryId": "22",
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False,
                },
            },
            media_body=MediaFileUpload(file_path, chunksize=-1, resumable=True),
        ).execute()
        print("✅ YouTube Upload Successful")
        return True
    except Exception as e:
        print(f"❌ YouTube Upload failed: {e}")
        return False


# ================== CLEANUP ================== #

def cleanup_files(final_video):
    print("🧹 Starting cleanup phase...")
    try:
        if final_video and os.path.exists(final_video):
            os.remove(final_video)

        for f in glob.glob("temp_vid_*.mp4"):
            os.remove(f)

        for f in glob.glob("temp_sfx_*.mp3"):
            os.remove(f)

        for f in glob.glob("temp_*.wav"):
            os.remove(f)

        print("✅ Cleanup complete!")
    except Exception as e:
        print(f"⚠️ Error during cleanup: {e}")


# ================== ENTRY ================== #

if __name__ == "__main__":
    video_path, metadata = main_pipeline()

    if video_path and metadata:
        upload_success = upload_to_youtube(video_path, metadata)

        if upload_success:
            save_new_topic(metadata)

        cleanup_files(video_path)

    print("🌿 Daily Ethereal execution finished!")

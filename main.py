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
from moviepy.video.fx.all import colorx
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
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY")
YOUTUBE_TOKEN_VAL = os.environ.get("YOUTUBE_TOKEN_JSON")

CHANNEL_HANDLE = "@EtherealDaily"
TOPICS_FILE = "topics.txt"
SOURCES_FILE = "sources.txt"

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

# Pillow compatibility for older MoviePy versions
if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS


# ================== HELPERS ================== #

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


def load_topic_memory(limit=120):
    if not os.path.exists(TOPICS_FILE):
        return []
    with open(TOPICS_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    return lines[-limit:]


def save_new_topic(record):
    """
    Saves a JSON line when possible, while keeping backward compatibility with the old plain-text file.
    """
    try:
        if isinstance(record, dict):
            payload = {
                "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "title": record.get("title", ""),
                "verse_source": record.get("verse_source", ""),
                "theme": record.get("theme", ""),
                "hook": record.get("audience_problem", ""),
                "quote": record.get("quote", ""),
                "tags": record.get("tags", []),
            }
            line = json.dumps(payload, ensure_ascii=False)
        else:
            line = str(record)

        with open(TOPICS_FILE, "a", encoding="utf-8") as f:
            f.write(f"{line}\n")
        print(f"💾 Saved '{line[:80]}' to memory bank.")
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


def _score_title(title):
    title = title or ""
    score = 0
    power_words = [
        "stop", "why", "before", "never", "truth", "hidden", "ancient",
        "poison", "calm", "break", "heal", "peace", "power", "wise", "real",
        "control", "fear", "burnout", "anxiety", "anger", "overthinking",
    ]
    for word in power_words:
        if word.lower() in title.lower():
            score += 2
    if len(title) <= 58:
        score += 2
    if "?" in title:
        score += 1
    if "#" in title:
        score += 1
    if len(title) < 35:
        score -= 1
    return score


def choose_best_title(data):
    options = []

    if isinstance(data.get("title_options"), list):
        options.extend([str(x).strip() for x in data["title_options"] if str(x).strip()])
    if isinstance(data.get("titles"), list):
        options.extend([str(x).strip() for x in data["titles"] if str(x).strip()])
    if data.get("title"):
        options.append(str(data["title"]).strip())

    if not options:
        return "Ancient wisdom for modern peace 🌿 #shorts #wisdom"

    unique = []
    for item in options:
        if item not in unique:
            unique.append(item)

    unique.sort(key=lambda t: _score_title(t), reverse=True)
    return unique[0]


def normalize_script(data, niche, avoid_text):
    """
    Hardens model output so the pipeline keeps running even if the model misses a field.
    """
    if not isinstance(data, dict):
        data = {}

    theme = data.get("theme") or random.choice(THEME_BUCKETS)
    verse_source = data.get("verse_source") or niche
    title = choose_best_title(data)

    quote = data.get("quote")
    audience_problem = data.get("audience_problem") or theme

    lines = data.get("lines")
    if not isinstance(lines, list) or len(lines) == 0:
        lines = []

    # Force a clean 4-part Shorts arc.
    fallback_lines = [
        {
            "segment_type": "hook",
            "style_instruction": "Sharp, intimate, and immediately attention-grabbing.",
            "acting_text": f"Feeling overwhelmed by {audience_problem}? <break time='0.8s'/>",
            "clean_text": f"Feeling overwhelmed by {audience_problem}?",
            "visual_keyword": f"{audience_problem} stormy atmosphere portrait",
            "sfx_keyword": "soft wind",
        },
        {
            "segment_type": "quote",
            "style_instruction": "Slow, grounded, and reverent.",
            "acting_text": f"From {verse_source}, this line matters: <break time='0.6s'/> <emphasis level='strong'>{quote or 'One timeless line teaches you to stay steady.'}</emphasis>",
            "clean_text": f"From {verse_source}, this line matters: {quote or 'One timeless line teaches you to stay steady.'}",
            "visual_keyword": "ancient manuscript candlelight",
            "sfx_keyword": "singing bowl",
        },
        {
            "segment_type": "meaning",
            "style_instruction": "Warm, reassuring, and thoughtful.",
            "acting_text": "It is saying that peace does not come from controlling everything. <break time='0.7s'/> It comes from knowing what deserves your energy.",
            "clean_text": "It is saying that peace does not come from controlling everything. It comes from knowing what deserves your energy.",
            "visual_keyword": "calm ocean waves at sunrise",
            "sfx_keyword": "soft ambient pad",
        },
        {
            "segment_type": "takeaway",
            "style_instruction": "Encouraging, steady, and memorable.",
            "acting_text": "So today, release one thing you cannot fix. <break time='0.7s'/> And that is exactly why this wisdom still helps right now.",
            "clean_text": "So today, release one thing you cannot fix. And that is exactly why this wisdom still helps right now.",
            "visual_keyword": "person walking toward sunrise",
            "sfx_keyword": "gentle wind",
        },
    ]

    if len(lines) < 4:
        lines = (lines + fallback_lines)[:4]

    cleaned_lines = []
    for idx, line in enumerate(lines[:4]):
        if not isinstance(line, dict):
            line = {}

        cleaned_lines.append({
            "segment_type": line.get("segment_type") or fallback_lines[idx]["segment_type"],
            "style_instruction": line.get("style_instruction") or fallback_lines[idx]["style_instruction"],
            "acting_text": line.get("acting_text") or fallback_lines[idx]["acting_text"],
            "clean_text": line.get("clean_text") or fallback_lines[idx]["clean_text"],
            "visual_keyword": line.get("visual_keyword") or fallback_lines[idx]["visual_keyword"],
            "sfx_keyword": line.get("sfx_keyword") or fallback_lines[idx]["sfx_keyword"],
        })

    description = data.get("description") or (
        f"One short line of wisdom for modern pressure.\n\n#wisdom #peace #motivation #shorts"
    )
    tags = data.get("tags")
    if not isinstance(tags, list) or not tags:
        tags = ["wisdom", "peace", "shorts", "motivation", "healing", "stoicism", "calm"]

    # Remove duplicates while preserving order
    deduped_tags = []
    for tag in tags:
        tag = str(tag).strip()
        if tag and tag not in deduped_tags:
            deduped_tags.append(tag)

    data["title"] = title
    data["verse_source"] = verse_source
    data["theme"] = theme
    data["audience_problem"] = audience_problem
    data["quote"] = quote or ""
    data["description"] = description
    data["tags"] = deduped_tags[:15]
    data["lines"] = cleaned_lines
    data["recommended_voice_model"] = data.get("recommended_voice_model", "Deep_Stoic_Male")

    # Keep the avoid text available if needed later.
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

    content_pool = load_sources()
    niche = random.choice(content_pool)
    print(f"🎲 Selected source for today: {niche}")

    past_topics = load_topic_memory()
    avoid_instruction = (
        "CRITICAL: avoid repeating these exact recent topics, titles, quotes, or hook angles:\n"
        + "\n".join(past_topics[-40:]) + "\n"
        if past_topics else
        "No past topics yet."
    )

    theme_focus = random.choice(THEME_BUCKETS)

    prompt = f"""
You are the elite lead scriptwriter for a YouTube Shorts channel about sacred, philosophical, and ancient wisdom.

TODAY'S SOURCE MATERIAL: {niche}
TODAY'S EMOTIONAL FOCUS: {theme_focus}

Your goal is NOT to sound generic.
Your goal is to create one very specific short that speaks to one real human problem, then answers it with one exact line of wisdom.

{avoid_instruction}

STRICT STRUCTURE:
Return ONLY valid JSON.

The video must follow this exact arc:
1. HOOK: start with a modern pain point in one sharp sentence.
2. QUOTE: state the source and the quote cleanly.
3. MEANING: explain what the line actually means in plain language.
4. TAKEAWAY: give one small action the viewer can use today.

IMPORTANT RULES:
- Keep the whole piece tight and Shorts-friendly.
- Do not write a long lecture.
- Do not mention subscribe, like, or generic outro language.
- End with a line that naturally loops back to the opening emotion.
- The quote should feel real, short, and relevant to the source.
- Make the title highly clickable but still respectful.
- Generate 3 title options in a field named title_options, then also pick one title.
- Use one voice style that fits the emotional tone.
- Use SSML tags in acting_text only, never in clean_text.
- Keep each line under ~2 spoken sentences.
- The final result should feel like a complete micro-story.

Return JSON in this shape:
{{
  "title_options": [
    "Example title 1",
    "Example title 2",
    "Example title 3"
  ],
  "title": "Chosen title",
  "verse_source": "{niche}",
  "theme": "{theme_focus}",
  "audience_problem": "one specific modern problem",
  "quote": "the actual quote or a very short faithful line from the source",
  "description": "Short description with relevant hashtags",
  "tags": ["wisdom", "peace", "shorts"],
  "recommended_voice_model": "Deep_Stoic_Male",
  "lines": [
    {{
      "segment_type": "hook",
      "style_instruction": "Sharp and immediate.",
      "acting_text": "Hook with a modern pain point <break time='0.6s'/>",
      "clean_text": "Hook with a modern pain point",
      "visual_keyword": "visual that matches the pain point",
      "sfx_keyword": "subtle sound"
    }},
    {{
      "segment_type": "quote",
      "style_instruction": "Calm and reverent.",
      "acting_text": "From {niche}, this line says: <break time='0.5s'/> <emphasis level='strong'>your quote here</emphasis>",
      "clean_text": "From {niche}, this line says: your quote here",
      "visual_keyword": "ancient manuscript",
      "sfx_keyword": "singing bowl"
    }},
    {{
      "segment_type": "meaning",
      "style_instruction": "Warm and insightful.",
      "acting_text": "Explain the meaning in simple human words.",
      "clean_text": "Explain the meaning in simple human words.",
      "visual_keyword": "calm reflective scenery",
      "sfx_keyword": "soft wind"
    }},
    {{
      "segment_type": "takeaway",
      "style_instruction": "Encouraging and memorable.",
      "acting_text": "End with one practical action that helps today.",
      "clean_text": "End with one practical action that helps today.",
      "visual_keyword": "person walking toward light",
      "sfx_keyword": "gentle rise"
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
                    data = normalize_script(data, niche, avoid_instruction)
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
                    data = normalize_script(data, niche, avoid_instruction)
                    if data.get("lines"):
                        print("✅ Script & SEO generated with OpenRouter fallback")
                        return data
        except Exception as e:
            print(f"❌ OpenRouter fallback error: {e}")

    # Final local fallback so the pipeline keeps working.
    print("⚠️ Using local fallback script.")
    local_fallback = normalize_script(
        {
            "title_options": [
                f"When {theme_focus} gets heavy, read this 🌿 #shorts #wisdom",
                f"One line that helps with {theme_focus} 🌿 #shorts #wisdom",
                f"Ancient wisdom for modern {theme_focus} 🌿 #shorts #wisdom",
            ],
            "title": f"Ancient wisdom for modern {theme_focus} 🌿 #shorts #wisdom",
            "verse_source": niche,
            "theme": theme_focus,
            "audience_problem": theme_focus,
            "quote": f"One timeless line from {niche} can steady the mind.",
            "description": f"Ancient wisdom for modern peace.\n\n#wisdom #peace #motivation #shorts",
            "tags": ["wisdom", "peace", "shorts", "motivation", "calm", "healing", "ancient"],
            "recommended_voice_model": "Deep_Stoic_Male",
        },
        niche,
        avoid_instruction,
    )
    return local_fallback


# ================== DYNAMIC PIXABAY SFX ================== #

def add_dynamic_sfx(audio_clip, keyword):
    if not keyword or keyword.lower() in ["none", "null", ""] or not PIXABAY_API_KEY:
        return audio_clip

    sfx_filename = f"temp_sfx_{keyword.replace(' ', '_')}.mp3"

    if not os.path.exists(sfx_filename):
        print(f"🔍 Fetching '{keyword}' SFX from Pixabay API...")
        url = "https://pixabay.com/api/audio/"
        params = {
            "key": PIXABAY_API_KEY,
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
        sfx = AudioFileClip(sfx_filename).volumex(0.12)
        if sfx.duration > audio_clip.duration:
            sfx = sfx.subclip(0, audio_clip.duration)
        return CompositeAudioClip([audio_clip, sfx])
    except Exception:
        return audio_clip


# ================== VISUAL FETCH ================== #

def get_visual_clip(keyword, filename, duration, segment_type="hook"):
    if not PEXELS_KEY:
        return ColorClip(size=(1080, 1920), color=(15, 15, 15), duration=duration)

    headers = {"Authorization": PEXELS_KEY}
    url = "https://api.pexels.com/videos/search"

    # Make the visual search reflect the emotional moment rather than always defaulting to nature.
    query_parts = [keyword, segment_type, "cinematic", "vertical"]
    query = " ".join([part for part in query_parts if part]).strip()

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
            clip = clip.without_audio()  # Prevents background Pexels noise from bleeding through

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


# ================== SUBTITLES ================== #

def add_dynamic_subtitles(video_clip, audio_path):
    print("📝 Transcribing audio for word-level subtitles...")
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio_path, word_timestamps=True)

    subtitle_clips = []

    for segment in segments:
        for word in segment.words:
            clean_word = word.word.strip().upper()
            if not clean_word:
                continue

            try:
                txt_clip = TextClip(
                    clean_word,
                    fontsize=80,
                    color="white",
                    stroke_color="black",
                    stroke_width=1,
                    font="Arial-Bold",
                    method="caption",
                    size=(video_clip.w * 0.8, None),
                ).set_start(word.start).set_end(word.end).set_position(("center", video_clip.h * 0.70))

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
    print(f"🏷️ Tags: {', '.join(script['tags'][:5])}...")
    print(f"🎯 Theme: {script.get('theme', 'Unknown')}")
    print(f"💡 Hook: {script.get('audience_problem', 'Unknown')}")

    target_voice = script.get("recommended_voice_model", "Deep_Stoic_Male")
    print(f"🎙️ AI Casted Narrator: {target_voice}")

    final_clips = []

    for i, line in enumerate(script["lines"]):
        try:
            acting_input = line.get("acting_text", line.get("text", ""))
            style_instruction = line.get("style_instruction", "Warm, peaceful, and slow.")
            clean_text = line.get("clean_text", line.get("text", ""))
            sfx_keyword = line.get("sfx_keyword", "none")
            segment_type = line.get("segment_type", "segment")

            wav_file = voice_engine.generate_acting_line(
                acting_text=acting_input,
                clean_text=clean_text,
                style_instruction=style_instruction,
                index=i,
                voice_name=target_voice,
            )

            if not wav_file:
                continue

            audio_clip = AudioFileClip(wav_file)
            audio_clip = add_dynamic_sfx(audio_clip, sfx_keyword)

            video_file = f"temp_vid_{i}.mp4"
            clip = get_visual_clip(
                line.get("visual_keyword", "wisdom"),
                video_file,
                audio_clip.duration,
                segment_type=segment_type,
            )

            clip = clip.fx(colorx, 0.95).set_audio(audio_clip)

            if i > 0 and final_clips:
                # Forces the clips to play sequentially.
                clip = clip.set_start(final_clips[-1].end)
                if random.random() < 0.3:
                    clip = clip.fadein(0.5, color=[255, 255, 255])

            final_clips.append(clip)

        except Exception as e:
            print(f"Clip error: {e}")

    if not final_clips:
        print("❌ No clips generated.")
        return None, None

    print("✂️ Rendering final video with transitions & branding...")
    final_video = CompositeVideoClip(final_clips)

    temp_voice_track = "temp_master_voice.wav"
    final_video.audio.write_audiofile(temp_voice_track, fps=24000, logger=None)
    final_video = add_dynamic_subtitles(final_video, temp_voice_track)

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

    print("🎵 Adding background music...")
    music_files = glob.glob("music/track*.mp3")

    if music_files:
        chosen_track = random.choice(music_files)
        try:
            bg_music = AudioFileClip(chosen_track).volumex(0.05)
            bg_music = audio_loop(bg_music, duration=final_video.duration)
            final_audio = CompositeAudioClip([final_video.audio, bg_music])
            final_video = final_video.set_audio(final_audio)
        except Exception as e:
            print(f"⚠️ Background music skipped: {e}")

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

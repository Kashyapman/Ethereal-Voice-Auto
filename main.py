import os
import random
import time
import json
import glob
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

# Pillow compatibility for older MoviePy versions
if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# ================== ANTI BAN ================== #

def anti_ban_sleep():
    if os.environ.get("GITHUB_ACTIONS") == "true":
        sleep_seconds = random.randint(120, 600) 
        print(f"🕵️ Anti-Ban Sleep: {sleep_seconds//60} minutes")
        time.sleep(sleep_seconds)

# ================== MEMORY SYSTEM ================== #

def get_past_topics():
    if not os.path.exists(TOPICS_FILE):
        return ""
    with open(TOPICS_FILE, "r", encoding="utf-8") as f:
        topics = f.read().splitlines()
    return "\n".join(topics[-100:])

def save_new_topic(case_name):
    try:
        with open(TOPICS_FILE, "a", encoding="utf-8") as f:
            f.write(f"{case_name}\n")
        print(f"💾 Saved '{case_name}' to memory bank.")
    except Exception as e:
        print(f"⚠️ Failed to save topic: {e}")

# ================== SCRIPT & SEO GENERATION ================== #

def generate_viral_script():
    print("🧠 Generating Ethereal High-Retention Loop Script...")

    client = genai.Client(api_key=GEMINI_KEY)
    models_to_try = ["models/gemini-2.5-pro", "models/gemini-2.5-flash"]
    
    if os.path.exists(SOURCES_FILE):
        with open(SOURCES_FILE, "r", encoding="utf-8") as f:
            content_pool = [line.strip() for line in f if line.strip()]
    else:
        print("⚠️ sources.txt not found! Using default fallback list.")
        content_pool = [
            "The Bhagavad Gita", "The Book of Proverbs", "The Quran", 
            "The Tao Te Ching", "The Dhammapada", "Meditations by Marcus Aurelius"
        ]
        
    niche = random.choice(content_pool)
    print(f"🎲 Selected Source for Today: {niche}")
    
    past_topics = get_past_topics()
    avoid_instruction = f"CRITICAL: Do NOT use these exact verses, we have already covered them:\n{past_topics}\n" if past_topics else "No past topics yet."

    prompt = f"""
You are the elite lead scriptwriter and Master Voice Director for "Ethereal", a massively successful YouTube Shorts channel. 

TODAY'S SOURCE MATERIAL: {niche}

Your task is to select one powerful, uplifting verse or quote from this exact source and write a highly engaging, high-retention script optimized for the YouTube Shorts algorithm.

{avoid_instruction}

STRICT HIGH-RETENTION STORYTELLING STRUCTURE:
1. THE PAIN POINT HOOK: Start IMMEDIATELY with a sharp, relatable modern problem (e.g. "Feeling crushed by the weight of others' opinions?", "Constantly worrying about tomorrow?"). Get straight to the point.
2. THE SOURCE & THE VERSE: You MUST explicitly state the source and read the actual quote. (e.g., "The ancient wisdom of the Tao Te Ching reminds us: [Quote]"). Do not skip the quote or the source!
3. THE PROPER EXPLANATION: Provide a deep, insightful explanation of what the verse means and how it applies to the pain point mentioned in the hook. Make the viewer understand and feel the impact.
4. THE INVISIBLE LOOP: End the script with a connective phrase like "And so...", "Which is why...", or "And that is exactly why..." so it grammatically flows PERFECTLY back into the very first line of your Pain Point hook, creating an endless seamless loop. Do NOT say "subscribe", "save this video", or do a traditional outro.

VOICE ACTING & EXPRESSION DIRECTION (CRITICAL FOR REALISM):
- recommended_voice_model: Choose the best fit from our 9 core archetypes: "Deep_Stoic_Male", "Firm_Motivational_Female", "Upbeat_Storyteller_Male", "Ethereal_Wisdom_Female", "Calm_Parable_Male", "Wise_Elder_Male", "Gentle_Guide_Female", "Authoritative_Narrator_Male", or "Bright_Inspirational_Female".
- style_instruction: A short note on the vibe (e.g., "Warm, peaceful, and slow.")
- EXPRESSION TAGS: Instead of robotic SSML, you MUST use natural paralinguistic tags placed directly in the `acting_text`.
- Allowed tags: [sigh], [pause], [chuckle], [clears throat], [laugh].
- Example: "Feeling crushed by things you cannot control? [pause] The Stoic philosopher Epictetus reminds us... [sigh]"
- Keep the `clean_text` completely free of these bracketed tags.

VISUALS & SFX:
- visual_keyword: Use ultra-specific, peaceful visual prompts (e.g., "macro shot of dew on a green leaf", "slow golden hour light through forest", "calm ocean waves crashing slowly").
- sfx_keyword: Choose subtle sounds from Pixabay (e.g., "wind chime", "soft wind", "singing bowl").

YOUTUBE SEO:
- title: An uplifting, highly engaging title. End with #shorts #wisdom.
- verse_source: The EXACT book and verse (e.g., "Tao Te Ching Chapter 8") so we can log it and never repeat it.

Return ONLY valid JSON in this format:
{{
  "title": "Let go of what you can't control 🌿 #shorts #wisdom",
  "verse_source": "Epictetus, Enchiridion 1",
  "description": "Ancient wisdom for modern peace.\\n\\n#wisdom #peace #motivation #stoicism",
  "tags": ["wisdom", "peace", "shorts", "motivation", "stoicism", "calm", "healing"],
  "recommended_voice_model": "Deep_Stoic_Male",
  "lines": [
    {{
      "style_instruction": "Captivating, wise, and profoundly comforting. Speak with momentum and clarity.",
      "acting_text": "Feeling crushed by things you cannot control? [pause] The Stoic philosopher Epictetus reminds us...",
      "clean_text": "Feeling crushed by things you cannot control? The Stoic philosopher Epictetus reminds us...",
      "visual_keyword": "slow clouds passing over mountain",
      "sfx_keyword": "soft wind"
    }},
    {{
      "style_instruction": "Deep resonance, authoritative.",
      "acting_text": "'Some things are in our control and others not.' [pause]",
      "clean_text": "'Some things are in our control and others not.'",
      "visual_keyword": "calm ocean waves crashing slowly",
      "sfx_keyword": "singing bowl"
    }},
    {{
      "style_instruction": "Comforting and impactful, slightly faster pace.",
      "acting_text": "[sigh] Your anxiety comes from carrying the weight of the entire world, instead of focusing on your own actions. When you let go of what isn't yours to carry, you find true freedom. [chuckle] And that is exactly why you might be...",
      "clean_text": "Your anxiety comes from carrying the weight of the entire world, instead of focusing on your own actions. When you let go of what isn't yours to carry, you find true freedom. And that is exactly why you might be...",
      "visual_keyword": "sunlight breaking through dark clouds",
      "sfx_keyword": "wind chime"
    }}
  ]
}}
"""

    config = types.GenerateContentConfig(
        temperature=0.8,
        top_p=0.95,
        response_mime_type="application/json"
    )

    for model in models_to_try:
        try:
            print(f"Trying {model}...")
            response = client.models.generate_content(model=model, contents=prompt, config=config)
            if response.text:
                data = json.loads(response.text)
                if "lines" in data and len(data["lines"]) > 0:
                    print(f"✅ Script & SEO generated with {model}")
                    return data
        except Exception as e:
            print(f"❌ Model error ({model}): {e}")
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print("⏳ Quota hit during script generation. Sleeping 5s before fallback...")
                time.sleep(5)
            continue

    if OPENROUTER_KEY:
        print("🔄 Gemini exhausted/failed. Falling back to OpenRouter (Llama 3.3 70B)...")
        try:
            headers = {
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "meta-llama/llama-3.3-70b-instruct:free",
                "messages": [{"role": "user", "content": prompt}]
            }
            
            r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
            
            if r.status_code == 200:
                response_content = r.json()['choices'][0]['message']['content']
                cleaned_content = response_content.replace("```json", "").replace("```", "").strip()
                data = json.loads(cleaned_content)
                
                if "lines" in data and len(data["lines"]) > 0:
                    print("✅ Script & SEO generated with OpenRouter Fallback")
                    return data
        except Exception as e:
            print(f"❌ OpenRouter Fallback error: {e}")

    return None

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
            "audio_type": "sound_effects"
        }
        try:
            r = requests.get(url, params=params)
            data = r.json()
            if data.get("hits") and len(data["hits"]) > 0:
                audio_url = data["hits"][0].get("audio") or data["hits"][0].get("url")
                
                if audio_url:
                    r_audio = requests.get(audio_url)
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
    except:
        return audio_clip

# ================== VISUAL FETCH ================== #

def get_visual_clip(keyword, filename, duration):
    headers = {"Authorization": PEXELS_KEY}
    url = "https://api.pexels.com/videos/search"
    
    params = {
        "query": f"{keyword} cinematic peaceful slow nature", 
        "per_page": 15, 
        "page": random.randint(1, 4), 
        "orientation": "portrait"
    }
    
    try:
        r = requests.get(url, headers=headers, params=params)
        data = r.json()
        
        if data.get("videos"):
            chosen_video = random.choice(data["videos"])
            best_file = max(chosen_video["video_files"], key=lambda x: x["width"] * x["height"])
            link = best_file["link"]
            
            with open(filename, "wb") as f:
                f.write(requests.get(link).content)

            clip = VideoFileClip(filename)
            if clip.duration < duration:
                loops = int(np.ceil(duration / clip.duration)) + 1
                clip = clip.loop(n=loops)
            clip = clip.subclip(0, duration)

            if clip.h < 1920: clip = clip.resize(height=1920)
            if clip.w < 1080: clip = clip.resize(width=1080)
            clip = clip.crop(x1=clip.w/2 - 540, width=1080, height=1920)
            return clip
    except Exception as e:
        pass
        
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
                    color='white',
                    stroke_color='black',
                    stroke_width=1,
                    font='Arial-Bold',
                    method='caption',
                    size=(video_clip.w * 0.8, None)
                ).set_start(word.start).set_end(word.end).set_position(('center', video_clip.h * 0.70))
                
                subtitle_clips.append(txt_clip)
            except Exception as e:
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
    
    target_voice = script.get("recommended_voice_model", "Deep_Stoic_Male")
    print(f"🎙️ AI Casted Narrator: {target_voice}")
    
    final_clips = []

    for i, line in enumerate(script["lines"]):
        try:
            acting_input = line.get("acting_text", line.get("text"))
            style_instruction = line.get("style_instruction", "Warm, peaceful, and slow.")
            clean_text = line.get("clean_text", line.get("text", ""))
            sfx_keyword = line.get("sfx_keyword", "none")

            wav_file = voice_engine.generate_acting_line(
                acting_text=acting_input, 
                clean_text=clean_text,
                style_instruction=style_instruction,
                index=i, 
                voice_name=target_voice
            )

            if not wav_file:
                continue

            audio_clip = AudioFileClip(wav_file)
            
            audio_clip = add_dynamic_sfx(audio_clip, sfx_keyword)

            video_file = f"temp_vid_{i}.mp4"
            clip = get_visual_clip(line["visual_keyword"], video_file, audio_clip.duration)

            clip = clip.fx(colorx, 0.95).set_audio(audio_clip)

            if i > 0:
                # FIXED: This forces the clips to play sequentially, preventing the 7-second cutoff!
                clip = clip.set_start(final_clips[-1].end)
                
                if random.random() < 0.3:
                    clip = clip.fadein(0.5, color=[255,255,255]) 
            
            final_clips.append(clip)

        except Exception as e:
            print(f"Clip error: {e}")

    if not final_clips:
        print("❌ No clips generated.")
        return None, None

    print("✂️ Rendering Final Video with Transitions & Branding...")
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
            color='white', 
            font='Arial', 
            stroke_color='black', 
            stroke_width=1
        ).set_opacity(0.4).set_position(('center', 150)).set_duration(final_video.duration)
        final_video = CompositeVideoClip([final_video, watermark])
    except Exception as e:
        print(f"⚠️ Could not add watermark: {e}")

    print("🎵 Adding Background Music...")
    music_files = glob.glob("music/track*.mp3")
    
    if music_files:
        chosen_track = random.choice(music_files)
        try:
            bg_music = AudioFileClip(chosen_track).volumex(0.05)
            bg_music = audio_loop(bg_music, duration=final_video.duration)
            final_audio = CompositeAudioClip([final_video.audio, bg_music])
            final_video = final_video.set_audio(final_audio)
        except Exception as e:
            pass

    output_file = "final_video.mp4"
    final_video.write_videofile(
        output_file,
        codec="libx264",
        audio_codec="aac",
        fps=30,
        preset="fast",
        threads=4 
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
                    "categoryId": "22" 
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False
                }
            },
            media_body=MediaFileUpload(file_path, chunksize=-1, resumable=True)
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
            case_to_save = metadata.get('verse_source', metadata['title'])
            save_new_topic(case_to_save)
        
        cleanup_files(video_path)
        
    print("🌿 Daily Ethereal execution finished!")

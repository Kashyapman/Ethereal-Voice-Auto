import os
import PIL.Image

# --- FIX FOR PILLOW ERROR ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
# ----------------------------

import random
import requests
import json
import re
import asyncio
import soundfile as sf
import numpy as np
from kokoro_onnx import Kokoro
from moviepy.editor import *
from moviepy.audio.fx.all import audio_loop
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- CONFIGURATION ---
GEMINI_KEY = os.environ["GEMINI_API_KEY"]
PEXELS_KEY = os.environ["PEXELS_API_KEY"]
YOUTUBE_TOKEN_VAL = os.environ["YOUTUBE_TOKEN_JSON"]
MODE = os.environ.get("VIDEO_MODE", "Short")

# --- GOD VOICE SETTINGS ---
# 'bm_lewis' is deep and calm. At 0.85 speed, it sounds very authoritative.
VOICE_ID = "bm_lewis" 

# --- FILES ---
TOPICS_FILE = "topics.txt"
LONG_QUEUE_FILE = "long_form_queue.txt"

def download_kokoro_model():
    print("🧠 Downloading Kokoro AI Model...")
    files = {
        "kokoro-v0_19.onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0_19.onnx",
        "voices.json": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.json"
    }
    for filename, url in files.items():
        if not os.path.exists(filename):
            print(f"   Downloading {filename}...")
            r = requests.get(url, stream=True)
            with open(filename, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
    print("✅ Model Ready.")

def get_dynamic_model_url():
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    try:
        response = requests.get(list_url)
        if response.status_code == 200:
            data = response.json()
            for model in data.get('models', []):
                if "generateContent" in model.get('supportedGenerationMethods', []):
                    return f"https://generativelanguage.googleapis.com/v1beta/{model['name']}:generateContent?key={GEMINI_KEY}"
    except: pass
    return f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_KEY}"

def generate_script(topic):
    print(f"Asking The Universe about: {topic} ({MODE} Mode)...")
    url = get_dynamic_model_url()
    headers = {'Content-Type': 'application/json'}
    
    # --- GOD MODE PROMPT ---
    if MODE == "Short":
        prompt_text = f"""
        Act as 'The Universe' or a Divine Consciousness speaking directly to a human soul. 
        Write a script for a YouTube Short based on: '{topic}'.
        
        RULES:
        1. Start with a direct address (e.g., "My child...", "Listen closely...", "You, who are weary...").
        2. Deliver the wisdom from the holy text naturally, not like a lecture. Make it feel like personal advice from God.
        3. Tone: Deep, Ancient, Infinite Love, Authoritative.
        4. Ending: A short command of peace (e.g., "Be still.", "I am with you.").
        
        FORMAT:
        - Plain text only.
        - Use '...' frequently to force the AI voice to pause and breathe.
        - Max 110 words.
        """
    else:
        # LONG FORM (Sermon Style)
        prompt_text = f"""
        Act as 'The Universe' or a Divine Consciousness. Write a FULL VIDEO SCRIPT on: '{topic}'.
        
        STRUCTURE:
        1. The Address: Acknowledge the user's pain or struggle related to the topic.
        2. The Ancient Word: Quote the holy text (Gita/Bible/Quran) clearly.
        3. The Wisdom: Explain why this truth matters now, in 2026.
        4. The Promise: End with a divine promise of hope.
        
        Tone: Epic, Cinematic, Healing, God-like.
        Max 350 words.
        Plain text only. Use '...' for dramatic pauses.
        """
    
    data = { "contents": [{ "parts": [{"text": prompt_text}] }] }
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result:
                raw = result['candidates'][0]['content']['parts'][0]['text']
                return raw.replace("*", "").strip()
    except Exception as e:
        print(f"Gemini Error: {e}")
    return None

def manage_topics():
    selected_topic = None
    if not os.path.exists(TOPICS_FILE): open(TOPICS_FILE, 'w').close()
    if not os.path.exists(LONG_QUEUE_FILE): open(LONG_QUEUE_FILE, 'w').close()

    if MODE == "Long":
        with open(LONG_QUEUE_FILE, 'r') as f:
            long_candidates = [l.strip() for l in f.readlines() if l.strip()]
        if long_candidates:
            selected_topic = long_candidates[0]
            with open(LONG_QUEUE_FILE, 'w') as f:
                for t in long_candidates[1:]: f.write(t + "\n")
            print(f"✅ Found topic in Long Queue: {selected_topic}")
            return selected_topic
            
    with open(TOPICS_FILE, 'r') as f:
        new_candidates = [l.strip() for l in f.readlines() if l.strip()]
    if new_candidates:
        selected_topic = new_candidates[0]
        with open(TOPICS_FILE, 'w') as f:
            for t in new_candidates[1:]: f.write(t + "\n")
        if MODE == "Short":
            with open(LONG_QUEUE_FILE, 'a') as f:
                f.write(selected_topic + "\n")
        return selected_topic

    return "Finding Peace in Chaos"

async def main_pipeline():
    download_kokoro_model()
    kokoro = Kokoro("kokoro-v0_19.onnx", "voices.json")

    # 1. TOPIC
    current_topic = manage_topics()
    print(f"🕊️ Processing: {current_topic}")

    # 2. SCRIPT
    script_text = generate_script(current_topic)
    if not script_text: script_text = f"My child... peace be with you regarding {current_topic}..."
    print(f"📝 Script Preview: {script_text[:50]}...")
    
    # 3. VOICE (GOD SPEED SETTINGS)
    print(f"🎙️ Generating Voice ({VOICE_ID})...")
    try:
        # Speed 0.85 = The "Morgan Freeman" effect. Slow, deep, heavy.
        samples, sample_rate = kokoro.create(
            script_text, voice=VOICE_ID, speed=0.85, lang="en-us"
        )
        sf.write("voice.wav", samples, sample_rate)
    except Exception as e:
        print(f"❌ Kokoro Failed: {e}")
        return None, None, None
    
    # 4. VISUALS (ETHEREAL)
    print("🎬 Downloading Video...")
    # Search for "Godly" visuals
    search_query = "sun rays clouds, galaxy universe, cinematic nature, light beams, slow motion water"
    headers = {"Authorization": PEXELS_KEY}
    orientation = 'portrait' if MODE == 'Short' else 'landscape'
    clip_count = 3 if MODE == 'Short' else 6
    url = f"https://api.pexels.com/videos/search?query={search_query}&per_page={clip_count}&orientation={orientation}"
    
    r = requests.get(url, headers=headers)
    video_clips = []
    if r.status_code == 200:
        video_data = r.json()
        if video_data.get('videos'):
            for i, video in enumerate(video_data['videos']):
                target = video['video_files'][0]
                with open(f"temp_{i}.mp4", "wb") as f:
                    f.write(requests.get(target['link']).content)
                try: video_clips.append(VideoFileClip(f"temp_{i}.mp4"))
                except: pass

    if not video_clips: return None, None, None

    # 5. MIXING
    print("✂️ Mixing Audio Layers...")
    try:
        voice_clip = AudioFileClip("voice.wav")
        
        music_folder = "music"
        music_files = []
        if os.path.exists(music_folder):
            music_files = [f for f in os.listdir(music_folder) if f.endswith(".mp3")]
        
        audio_layers = [voice_clip]
        if music_files:
            music_path = os.path.join(music_folder, random.choice(music_files))
            music_clip = AudioFileClip(music_path)
            if music_clip.duration < voice_clip.duration:
                music_clip = audio_loop(music_clip, duration=voice_clip.duration + 2)
            # Volume 0.20 - Enough to feel the atmosphere, but voice is dominant
            music_clip = music_clip.subclip(0, voice_clip.duration).volumex(0.20)
            audio_layers.append(music_clip)
            
        final_audio = CompositeAudioClip(audio_layers)

        final_clips = []
        current_duration = 0
        while current_duration < voice_clip.duration:
            for clip in video_clips:
                if current_duration >= voice_clip.duration: break
                
                if MODE == "Short":
                    w, h = clip.size
                    if w > h: clip = clip.crop(x1=w/2 - h*(9/16)/2, width=h*(9/16), height=h)
                    clip = clip.resize(height=1920)
                    clip = clip.resize(width=1080)
                else:
                    clip = clip.resize(height=1080)
                    w, h = clip.size
                    if w/h != 16/9:
                         clip = clip.crop(x1=w/2 - (h*16/9)/2, width=h*16/9, height=h)
                
                # SLOW FADE TRANSITIONS (Cinematic)
                if len(final_clips) > 0:
                    clip = clip.crossfadein(1.5) # 1.5s slow fade
                final_clips.append(clip)
                current_duration += clip.duration
        
        # padding=-1 removes negative audio glitch in MoviePy
        final_video = concatenate_videoclips(final_clips, method="compose", padding=-1)
        final_video = final_video.set_audio(final_audio)
        final_video = final_video.subclip(0, voice_clip.duration)
        
        output_file = "final_video.mp4"
        final_video.write_videofile(output_file, codec="libx264", audio_codec="aac", fps=24, preset="medium")
        
        voice_clip.close()
        for clip in video_clips: clip.close()
        for i in range(len(video_clips)): 
            if os.path.exists(f"temp_{i}.mp4"): os.remove(f"temp_{i}.mp4")
            
        return output_file, current_topic, f"A message for you: {current_topic}"
        
    except Exception as e:
        print(f"❌ Editing Failed: {e}")
        return None, None, None

def upload_to_youtube(file_path, title, description):
    if not file_path: return
    print("🚀 Uploading to YouTube...")
    try:
        creds_dict = json.loads(YOUTUBE_TOKEN_VAL)
        creds = Credentials.from_authorized_user_info(creds_dict)
        youtube = build('youtube', 'v3', credentials=creds)
        tags = ["shorts", "god", "universe", "manifestation", "peace", "prayer"]
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title[:100], "description": description[:4500],
                    "tags": tags, "categoryId": "27" 
                },
                "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
            },
            media_body=MediaFileUpload(file_path, chunksize=-1, resumable=True)
        )
        response = request.execute()
        print(f"✅ Uploaded! Video ID: {response.get('id')}")
    except Exception as e:
        print(f"❌ Upload failed: {str(e)}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        video_path, topic, desc = loop.run_until_complete(main_pipeline())
        final_title = f"{topic} #shorts" if MODE == "Short" else topic
        if video_path: upload_to_youtube(video_path, final_title, desc)
    except Exception as e:
        print(f"Critical Error: {e}")

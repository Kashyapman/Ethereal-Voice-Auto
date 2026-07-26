import os
import time
import wave
import random
from google import genai
from google.genai import types
from pydub import AudioSegment
from pydub.effects import compress_dynamic_range, normalize

# ============================================================
# ETHEREAL VOICE MAP & ROLE DIRECTIVES
# ============================================================
GEMINI_WISDOM_VOICES = {
    "Deep_Stoic_Male": "Charon",
    "Firm_Motivational_Female": "Kore",
    "Upbeat_Storyteller_Male": "Puck",
    "Ethereal_Wisdom_Female": "Aoede",
    "Calm_Parable_Male": "Fenrir",
    "Wise_Elder_Male": "Umbriel",
    "Gentle_Guide_Female": "Vindemiatrix",
    "Authoritative_Narrator_Male": "Zubenelgenubi",
    "Bright_Inspirational_Female": "Zephyr",
}

WISDOM_ROLE_PROMPTS = {
    "Deep_Stoic_Male": (
        "You are a timeless Stoic philosopher and elder mentor. Your voice is deep, "
        "grounded, quiet, and resonant, carrying unflinching strength and peace."
    ),
    "Ethereal_Wisdom_Female": (
        "You are a serene, compassionate celestial guide. Your voice is soft, warm, "
        "atmospheric, and comforting, delivering profound spiritual truth."
    ),
    "Wise_Elder_Male": (
        "You are an ancient scholar reading sacred scriptures. Your vocal delivery is "
        "reverent, slow, heavy with conviction, and deeply authoritative."
    ),
    "Gentle_Guide_Female": (
        "You are a calm meditation master speaking to someone who is hurting. Your tone is "
        "gentle, patient, breathy, and emotionally steady."
    )
}


class VoiceEngine:
    def __init__(self):
        print("🎚️ Initializing Gemini Ethereal Master-Director Engine v3.7...")
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        self.client = genai.Client(api_key=self.api_key)

    def _ethereal_mastering(self, sound: AudioSegment) -> AudioSegment:
        """Clean, warm, massive mastering optimized for spiritual clarity."""
        sound = sound.high_pass_filter(70)
        sound = sound.low_pass_filter(13000)
        sound = compress_dynamic_range(
            sound,
            threshold=-15.0,
            ratio=3.8,
            attack=6.0,
            release=55.0,
        )
        sound = normalize(sound, headroom=0.2)
        return sound

    def generate_acting_line(
        self,
        acting_text: str,
        clean_text: str,
        style_instruction: str,
        index: int,
        voice_name: str = "Deep_Stoic_Male",
        pre_silence_ms: int = 0,
        post_silence_ms: int = 120,
        human_touch: bool = False,
    ) -> str | None:
        filename = f"temp_voice_{index}.wav"
        gemini_voice = GEMINI_WISDOM_VOICES.get(voice_name, "Charon")
        role_directive = WISDOM_ROLE_PROMPTS.get(voice_name, WISDOM_ROLE_PROMPTS["Deep_Stoic_Male"])

        print(f"🎙️ Gemini Studio TTS [{gemini_voice} | Persona: {voice_name}] | Style: {style_instruction[:35]}...")

        config = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=gemini_voice)
                )
            ),
        )

        if human_touch:
            pre_silence_ms = max(0, pre_silence_ms + random.randint(0, 30))
            post_silence_ms = max(0, post_silence_ms + random.randint(0, 45))

        prompt = f"""{role_directive}

YOUR SPECIFIC VOCAL STYLE FOR THIS EXACT LINE: "{style_instruction}"

PERFORMANCE INSTRUCTIONS:
1. Execute SSML tags (pauses, emphasis, rate shifts) as natural stage directions.
2. DO NOT speak SSML tags, prompt directions, or stage brackets out loud.
3. Keep the pacing measured, intentional, and spiritually resonant.

SCRIPT:
{acting_text}"""

        models_to_try = ["gemini-2.5-flash-preview-tts", "gemini-2.5-pro"]

        for model_name in models_to_try:
            for attempt in range(3):
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=config,
                    )

                    audio_bytes = None
                    if response.candidates and response.candidates[0].content.parts:
                        for part in response.candidates[0].content.parts:
                            if part.inline_data:
                                audio_bytes = part.inline_data.data
                                break

                    if not audio_bytes:
                        continue

                    temp_raw = f"temp_raw_{index}.wav"
                    with wave.open(temp_raw, "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(24000)
                        wf.writeframes(audio_bytes)

                    sound = AudioSegment.from_file(temp_raw)
                    sound = self._ethereal_mastering(sound)

                    if pre_silence_ms > 0:
                        sound = AudioSegment.silent(duration=pre_silence_ms) + sound
                    if post_silence_ms > 0:
                        sound = sound + AudioSegment.silent(duration=post_silence_ms)

                    if human_touch:
                        sound = sound.fade_in(8).fade_out(15)

                    sound.export(filename, format="wav")

                    if os.path.exists(temp_raw):
                        os.remove(temp_raw)

                    return filename

                except Exception as e:
                    if "429" in str(e) or "503" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        time.sleep(15 + (attempt * 10))
                    else:
                        break

        return None

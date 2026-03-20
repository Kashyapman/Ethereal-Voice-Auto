import os
import wave
import time
from google import genai
from google.genai import types
from pydub import AudioSegment
from pydub.effects import compress_dynamic_range, normalize

class VoiceEngine:
    def __init__(self):
        print("🎚️ Initializing Ethereal Voice Engine...")
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        self.client = genai.Client(api_key=self.api_key)

    def _ethereal_mastering(self, sound):
        """Clean, warm, massive mastering—but optimized for Shorts retention."""
        sound = compress_dynamic_range(sound, threshold=-15.0, ratio=4.0, attack=5.0, release=50.0)
        sound = normalize(sound, headroom=0.2) 
        
        # FIXED: Reduced pause from 600ms to 150ms to keep the Shorts algorithm happy. 
        # No dead air! Keep the viewer hooked.
        silence = AudioSegment.silent(duration=150)
        sound = sound + silence
        
        return sound

    def generate_acting_line(self, acting_text, style_instruction, index, voice_name="Charon"):
        filename = f"temp_voice_{index}.wav"
        print(f"🎙️ Rendering [{voice_name}] | Vibe: {style_instruction}")

        config = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            )
        )

        prompt = f"""You are a captivating, celestial narrator delivering ancient wisdom. 

YOUR VOCAL STYLE/EMOTION FOR THIS LINE: 
"{style_instruction}"

CRITICAL INSTRUCTIONS:
Process the following SSML markup exactly. Speak with deep resonance, but maintain strong MOMENTUM. Do not drag your words. This is for short-form video, so pacing must be engaging and continuous to maintain viewer retention.

<speak>
{acting_text}
</speak>"""

        models_to_try = ["gemini-2.5-flash-preview-tts", "gemini-2.5-pro"]

        for model_name in models_to_try:
            for attempt in range(3):
                try:
                    response = self.client.models.generate_content(
                        model=model_name, contents=prompt, config=config
                    )

                    audio_bytes = None
                    if response.candidates and response.candidates[0].content.parts:
                        for part in response.candidates[0].content.parts:
                            if part.inline_data:
                                audio_bytes = part.inline_data.data
                                break

                    if not audio_bytes: continue 

                    temp_raw = f"temp_raw_{index}.wav"
                    with wave.open(temp_raw, "wb") as wf:
                        wf.setnchannels(1) 
                        wf.setsampwidth(2) 
                        wf.setframerate(24000) 
                        wf.writeframes(audio_bytes)

                    sound = AudioSegment.from_file(temp_raw)
                    sound = self._ethereal_mastering(sound)
                    sound.export(filename, format="wav")
                    
                    if os.path.exists(temp_raw): 
                        os.remove(temp_raw)

                    return filename

                except Exception as e:
                    if "429" in str(e) or "503" in str(e): 
                        time.sleep(35 + (attempt * 10))
                    else: 
                        break 
        return None

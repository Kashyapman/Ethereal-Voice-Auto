import os
import wave
import time
from google import genai
from google.genai import types
from pydub import AudioSegment
from pydub.effects import normalize

class VoiceEngine:
    def __init__(self):
        print("🎚️ Initializing Ethereal Voice Engine...")
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        self.client = genai.Client(api_key=self.api_key)

    def _podcast_mastering(self, sound):
        """Clean, warm, and resonant mastering for spiritual content."""
        # Removed the low_pass_filter to keep the voice crisp and airy
        sound = normalize(sound, headroom=0.5) 
        
        # Add a 600ms peaceful pause buffer so the listener can absorb the words
        silence = AudioSegment.silent(duration=600)
        sound = sound + silence
        
        return sound

    def generate_acting_line(self, acting_text, style_instruction, index, voice_name="Aoede"):
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

        prompt = f"""You are a calm, enlightened, and uplifting narrator. 

YOUR VOCAL STYLE/EMOTION: 
"{style_instruction}"

CRITICAL INSTRUCTIONS:
Process the following SSML markup. Speak slowly, clearly, and with deep empathy. Pay strict attention to <break> tags to let the wisdom breathe.

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
                    sound = self._podcast_mastering(sound)
                    sound.export(filename, format="wav")
                    if os.path.exists(temp_raw): os.remove(temp_raw)

                    return filename

                except Exception as e:
                    if "429" in str(e) or "503" in str(e): time.sleep(35 + (attempt * 10))
                    else: break 
        return None

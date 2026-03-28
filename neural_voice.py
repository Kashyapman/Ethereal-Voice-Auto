import os
import wave
import time
import torchaudio as ta
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

        # Safely try to initialize Chatterbox on CPU
        try:
            from chatterbox.tts_turbo import ChatterboxTurboTTS
            print("🧠 Loading Chatterbox Turbo on CPU...")
            self.chatterbox = ChatterboxTurboTTS.from_pretrained(device="cpu")
        except Exception as e:
            print(f"⚠️ Chatterbox initialization failed: {e}. Will use Gemini TTS fallback.")
            self.chatterbox = None

    def _ethereal_mastering(self, sound):
        """Clean, warm, massive mastering—optimized for Shorts retention."""
        sound = compress_dynamic_range(sound, threshold=-15.0, ratio=4.0, attack=5.0, release=50.0)
        sound = normalize(sound, headroom=0.2) 
        silence = AudioSegment.silent(duration=150)
        sound = sound + silence
        return sound

    def generate_acting_line(self, acting_text, clean_text, style_instruction, index, voice_name="Deep_Stoic_Male"):
        filename = f"temp_voice_{index}.wav"
        print(f"🎙️ Rendering [{voice_name}] | Vibe: {style_instruction}")

        # ==========================================
        # ATTEMPT 1: CHATTERBOX TURBO (Expressive Cloning)
        # ==========================================
        if self.chatterbox:
            try:
                # 1. Point to the specific cloned voice file based on the script's recommendation
                voice_path = f"voices/{voice_name}.wav"
                
                # 2. Check if the file exists to prevent crashes
                if os.path.exists(voice_path):
                    wav = self.chatterbox.generate(acting_text, audio_prompt_path=voice_path)
                else:
                    print(f"⚠️ Warning: {voice_path} not found. Using default base voice.")
                    wav = self.chatterbox.generate(acting_text)
                
                temp_raw = f"temp_raw_cb_{index}.wav"
                ta.save(temp_raw, wav, self.chatterbox.sr)
                
                sound = AudioSegment.from_file(temp_raw)
                sound = self._ethereal_mastering(sound)
                sound.export(filename, format="wav")
                
                if os.path.exists(temp_raw): 
                    os.remove(temp_raw)
                    
                return filename
            except Exception as e:
                print(f"⚠️ Chatterbox failed for line {index}: {e}. Falling back to Gemini TTS.")

        # ==========================================
        # ATTEMPT 2: GEMINI TTS FALLBACK (Safe)
        # ==========================================
        print("🔄 Using Gemini TTS Fallback...")
        
        # Exact mapping back to Gemini prebuilt voices for perfect fallbacks
        fallback_map = {
            "Deep_Stoic_Male": "Charon",
            "Firm_Motivational_Female": "Kore",
            "Upbeat_Storyteller_Male": "Puck",
            "Ethereal_Wisdom_Female": "Aoede",
            "Calm_Parable_Male": "Fenrir",
            "Wise_Elder_Male": "Umbriel",
            "Gentle_Guide_Female": "Vindemiatrix",
            "Authoritative_Narrator_Male": "Zubenelgenubi",
            "Bright_Inspirational_Female": "Zephyr"
        }
        
        gemini_voice = fallback_map.get(voice_name, "Charon")

        config = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=gemini_voice)
                )
            )
        )

        prompt = f"""You are a captivating, celestial narrator. Read this exactly, with a vibe of: {style_instruction}\n\n{clean_text}"""

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

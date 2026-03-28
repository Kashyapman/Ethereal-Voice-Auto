import os
import wave
from google import genai
from google.genai import types

# Ensure your API key is set in your terminal: export GEMINI_API_KEY="your_key"
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("Please set your GEMINI_API_KEY environment variable.")

client = genai.Client(api_key=API_KEY)

# Ensure the voices directory exists
os.makedirs("voices", exist_ok=True)

# The reference text: 
# Neutral tone, clear pronunciation, ~7 seconds long.
REFERENCE_TEXT = "The path to inner peace begins with a single, mindful breath. By observing our thoughts without judgment, we create space for true understanding."

# The comprehensive Ethereal Voice Roster
VOICES_TO_GENERATE = {
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

def generate_reference_audio(archetype_name, gemini_voice_name):
    print(f"🎙️ Generating reference for: {archetype_name} (using {gemini_voice_name})...")
    
    config = types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=gemini_voice_name)
            )
        )
    )

    prompt = f"Read the following text clearly and naturally:\n\n{REFERENCE_TEXT}"

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts", 
            contents=prompt, 
            config=config
        )

        audio_bytes = None
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    audio_bytes = part.inline_data.data
                    break

        if audio_bytes:
            filepath = f"voices/{archetype_name}.wav"
            with wave.open(filepath, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(24000)
                wf.writeframes(audio_bytes)
            print(f"✅ Saved successfully to {filepath}\n")
        else:
            print(f"❌ Failed to extract audio bytes for {archetype_name}\n")

    except Exception as e:
        print(f"❌ API Error for {archetype_name}: {e}\n")

if __name__ == "__main__":
    print("🚀 Starting Ethereal Voice Cloning Generation...\n")
    for archetype, gemini_voice in VOICES_TO_GENERATE.items():
        generate_reference_audio(archetype, gemini_voice)
    print("🎉 All base voices generated! Commit the 'voices' folder to your GitHub repo.")

# Ethereal-Voice-Auto ✨🕊️

Ethereal-Voice-Auto is a fully automated content generation and publishing pipeline specifically designed to power the "Ethereal" motivational YouTube channel. Building upon a robust, hands-off automation architecture, this repository handles the end-to-end creation of uplifting, spiritually and philosophically grounded video content—from script generation based on sacred texts to final video rendering and uploading.

## 🌟 Key Features

* **Automated Motivational Content:** Autonomously generates positive, insightful explanations of verses from major religious and philosophical texts (e.g., Bhagavad Gita, Bible, Quran).
* **AI-Powered Scripting & Voice:** Uses advanced AI to select themes and craft scripts, paired with a custom neural voice engine (`neural_voice.py`) for a calm, ethereal, and engaging narration.
* **Smart Memory System:** Tracks previously used verses and themes in `topics.txt` and `sources.txt` to ensure fresh, non-repetitive content for the audience.
* **Integrated Audio Mixing:** Automatically overlays soothing background tracks from the `music/` directory and integrates sound effects to enhance the listening experience.
* **Hands-Free Orchestration:** Designed to run seamlessly via GitHub Actions (`.github/workflows`), automatically committing memory updates back to the repository after successful uploads.

## 📂 Repository Structure

* `.github/workflows/` - Contains the YAML configurations for scheduling and running the automated pipeline via GitHub Actions.
* `music/` - Directory for storing copyright-free, ambient background music (e.g., from the YouTube Audio Library).
* `main.py` - The central execution script that orchestrates the selection of verses, audio generation, video assembly, and uploading.
* `neural_voice.py` - The text-to-speech module configured for the specific pacing and tone of the Ethereal channel.
* `sources.txt` - A reference list of the philosophical and sacred texts the bot draws inspiration from.
* `topics.txt` - The channel's memory bank, logging completed verses to avoid duplicate uploads.
* `requirements.txt` - The required Python dependencies to execute the pipeline.

## 🚀 Setup & Installation

### Prerequisites
To run this pipeline locally or configure it for CI/CD, you need the appropriate API keys for content generation, media sourcing, and YouTube integration.

1.  Clone the repository:
    ```bash
    git clone [https://github.com/Kashyapman/Ethereal-Voice-Auto.git](https://github.com/Kashyapman/Ethereal-Voice-Auto.git)
    cd Ethereal-Voice-Auto
    ```

2.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Environment Variables & Secrets
For the automated pipeline to function securely via GitHub Actions, configure the following secrets in your repository settings:

* **AI & Content APIs:** Keys for your chosen LLM (e.g., Gemini/OpenRouter) to generate the motivational scripts.
* **YouTube OAuth:** `YOUTUBE_API_KEY` and `CLIENT_SECRETS` for automated channel uploads.
* **Media APIs:** Keys for sourcing background visuals (if utilizing external APIs like Pexels/Pixabay).
* **GitHub Token:** Ensure your Action's `GITHUB_TOKEN` is granted **Read & Write** permissions so the bot can update and commit to `topics.txt` and `sources.txt`.

## ⚙️ How It Works

1.  **Trigger:** The GitHub Action wakes up on its defined schedule.
2.  **Theme Selection:** `main.py` consults `sources.txt` and checks `topics.txt` to pick a new, uplifting verse or philosophical concept.
3.  **Content Creation:** An AI model generates a positive, detailed script explaining the verse, while `neural_voice.py` converts it into soothing audio.
4.  **Audio/Video Assembly:** The voiceover is mixed with tracks from the `music/` folder, and the final video asset is rendered.
5.  **Publishing & Logging:** The finished video is uploaded directly to the Ethereal YouTube channel. The bot then writes the newly used topic to `topics.txt` and commits the changes back to GitHub.

## 📝 License
This project is private and maintained exclusively for the automated management of the Ethereal YouTube channel.

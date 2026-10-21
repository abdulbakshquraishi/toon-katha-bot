import os
import json
import asyncio
import google.generativeai as genai
import edge_tts
from moviepy.editor import TextClip, AudioFileClip, ColorClip, CompositeVideoClip

# Gemini API Configure
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_KEY)

PROGRESS_FILE = "progress.json"

def get_current_progress():
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"story_title": "", "current_part": 1, "total_parts": 5}

def save_progress(progress):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=4, ensure_ascii=False)

def generate_episodic_story():
    progress = get_current_progress()
    current_part = progress.get("current_part", 1)
    total_parts = progress.get("total_parts", 5)
    story_title = progress.get("story_title", "")

    model = genai.GenerativeModel('gemini-flash-latest')

    if current_part == 1 or not story_title:
        prompt = (
            "Generate an engaging, trending moral or suspense story for kids/youth in 5 short parts. "
            "Write ONLY Part 1 of 5 as a 30-second YouTube Short narration script in simple Hindi. "
            "Start with 'Title: [Story Title]' at the top and end with a strong cliffhanger hook for Part 2. "
            "Do NOT include scene directions or brackets in speech text."
        )
    else:
        prompt = (
            f"We are continuing the Hindi story '{story_title}'. "
            f"Write ONLY Part {current_part} of {total_parts} as a 30-second YouTube Short narration script in simple Hindi. "
            f"Maintain high suspense and end with a hook for the next episode."
        )

    response = model.generate_content(prompt)
    story_text = response.text

    print(f"--- Episode {current_part}/{total_parts} Generated ---")
    print(story_text)

    # Extract title
    if current_part == 1:
        lines = story_text.splitlines()
        for line in lines:
            if "Title:" in line or "शीर्षक:" in line or "कहानी:" in line:
                story_title = line.replace("Title:", "").replace("शीर्षक:", "").replace("कहानी:", "").strip()
                break
        if not story_title:
            story_title = "Trending Toon Story"
        progress["story_title"] = story_title

    # Update progress counter
    if current_part >= total_parts:
        progress["current_part"] = 1
        progress["story_title"] = ""
    else:
        progress["current_part"] += 1

    save_progress(progress)
    return story_text, story_title, current_part

async def generate_voiceover(text, output_file="narration.mp3"):
    clean_text = "\n".join([line for line in text.splitlines() if not line.startswith("Title:") and not line.startswith("शीर्षक:")])
    communicate = edge_tts.Communicate(clean_text, voice="hi-IN-SwaraNeural")
    await communicate.save(output_file)
    print(f"Voiceover generated successfully: {output_file}")

def create_video(audio_file="narration.mp3", output_video="story_video.mp4"):
    print("Rendering YouTube Short Video...")
    # Load audio to get exact duration
    audio_clip = AudioFileClip(audio_file)
    duration = audio_clip.duration

    # Create a 9:16 vertical background (Dark Blue / Suspense theme)
    # Resolution for Shorts: 1080x1920
    bg_clip = ColorClip(size=(1080, 1920), color=(20, 24, 33), duration=duration)

    # Set audio to background clip
    video = bg_clip.set_audio(audio_clip)

    # Write final video file
    video.write_videofile(output_video, fps=24, codec="libx264", audio_codec="aac")
    print(f"Video rendered successfully: {output_video}")

if __name__ == "__main__":
    print("Starting ToonKatha Daily Episode Pipeline...")
    story_text, story_title, current_part = generate_episodic_story()
    
    print("Generating Hindi Voiceover...")
    asyncio.run(generate_voiceover(story_text))

    print("Creating Video...")
    create_video()

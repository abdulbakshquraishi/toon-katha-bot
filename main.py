import os
import json
import asyncio
import google.generativeai as genai
import edge_tts
from moviepy import AudioFileClip, ColorClip, CompositeVideoClip
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

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
            "Generate a highly engaging, super funny, and emotional Motu-Patlu / Chhota Bheem style Hindi 2D cartoon moral story for kids in 5 parts. "
            "Write Part 1 as a detailed 60-second YouTube Shorts narration script in simple Hindi. "
            "Start with 'Title: [Story Title]' at the top. Make it full of action, comedy, and end with an irresistible cliffhanger! "
            "Do NOT include scene directions or brackets in speech text."
        )
    else:
        prompt = (
            f"We are continuing the hit Hindi cartoon story '{story_title}'. "
            f"Write Part {current_part} of {total_parts} as a detailed 60-second YouTube Shorts narration script in simple Hindi. "
            f"Keep high excitement, funny cartoon dialogue, and strong moral value."
        )

    response = model.generate_content(prompt)
    story_text = response.text

    print(f"--- Episode {current_part}/{total_parts} Generated ---")
    print(story_text)

    if current_part == 1:
        lines = story_text.splitlines()
        for line in lines:
            if "Title:" in line or "शीर्षक:" in line or "कहानी:" in line:
                story_title = line.replace("Title:", "").replace("शीर्षक:", "").replace("कहानी:", "").strip()
                break
        if not story_title:
            story_title = "Majedar Cartoon Katha"
        progress["story_title"] = story_title

    if current_part >= total_parts:
        progress["current_part"] = 1
        progress["story_title"] = ""
    else:
        progress["current_part"] += 1

    save_progress(progress)
    return story_text, story_title, current_part

async def generate_voiceover(text, output_file="narration.mp3"):
    clean_lines = [line for line in text.splitlines() if not line.startswith("Title:") and not line.startswith("शीर्षक:")]
    clean_text = "\n".join(clean_lines)
    communicate = edge_tts.Communicate(clean_text, voice="hi-IN-SwaraNeural")
    await communicate.save(output_file)
    print(f"Voiceover generated successfully: {output_file}")

def create_video(story_title, audio_file="narration.mp3", output_video="story_video.mp4"):
    print("Rendering Clean Cartoon Video with Color Background...")
    audio_clip = AudioFileClip(audio_file)
    duration = audio_clip.duration

    # Creating a bright cartoon style background (Sky Blue color: RGB 135, 206, 235) for Shorts 1080x1920
    bg_clip = ColorClip(size=(1080, 1920), color=(135, 206, 235), duration=duration)

    video = CompositeVideoClip([bg_clip]).with_audio(audio_clip)
    video.write_videofile(output_video, fps=24, codec="libx264", audio_codec="aac")
    print(f"Video rendered successfully: {output_video}")

def upload_to_youtube(video_path, title):
    client_id = os.getenv("YOUTUBE_CLIENT_ID")
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        print("YouTube refresh token missing. Skipping auto upload for now.")
        return

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret
    )

    youtube = build("youtube", "v3", credentials=creds)

    request_body = {
        "snippet": {
            "title": f"{title} | Majedar Hindi Cartoon Story #Shorts",
            "description": "Dekhiye sabse majedar hindi cartoon moral stories! Subscribe for daily videos. #shorts #cartoon #motupatlu #moralstories",
            "tags": ["shorts", "hindi stories", "cartoon", "motu patlu", "chhota bheem", "puntoon kids"],
            "categoryId": "15"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": True
        }
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media
    )

    response = request.execute()
    print(f"Video uploaded successfully! Video ID: {response.get('id')}")

if __name__ == "__main__":
    print("Starting ToonKatha Pipeline...")
    story_text, story_title, current_part = generate_episodic_story()
    
    print("Generating Hindi Voiceover...")
    asyncio.run(generate_voiceover(story_text))

    print("Creating Animated Video...")
    create_video(story_title)

    print("Uploading to YouTube...")
    try:
        upload_to_youtube("story_video.mp4", story_title)
    except Exception as e:
        print(f"YouTube upload status: {e}")

import os
import json
import asyncio
import requests
import google.generativeai as genai
import edge_tts
from moviepy import AudioFileClip, ImageClip, CompositeVideoClip
from PIL import Image
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Gemini API Configuration
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
            "Generate a super funny, exciting and moral Hindi cartoon story for kids in 5 parts. "
            "Write Part 1 as a 40-second YouTube Shorts script in simple Hindi. "
            "Start with 'Title: [Story Title]' at the top. Make it very engaging!"
        )
    else:
        prompt = (
            f"Continue the hit Hindi cartoon story '{story_title}'. "
            f"Write Part {current_part} of {total_parts} as a 40-second YouTube Shorts script in simple Hindi with high energy."
        )

    response = model.generate_content(prompt)
    story_text = response.text

    if current_part == 1:
        for line in story_text.splitlines():
            if "Title:" in line or "शीर्षक:" in line:
                story_title = line.replace("Title:", "").replace("शीर्षक:", "").strip()
                break
        if not story_title:
            story_title = "Majedar Jungle Ki Kahani"
        progress["story_title"] = story_title

    if current_part >= total_parts:
        progress["current_part"] = 1
        progress["story_title"] = ""
    else:
        progress["current_part"] += 1

    save_progress(progress)
    return story_text, story_title

async def generate_voiceover(text, output_file="narration.mp3"):
    clean_lines = [line for line in text.splitlines() if not line.startswith("Title:") and not line.startswith("शीर्षक:")]
    clean_text = "\n".join(clean_lines)
    communicate = edge_tts.Communicate(clean_text, voice="hi-IN-SwaraNeural")
    await communicate.save(output_file)
    print("Voiceover generated successfully!")

def create_video(audio_file="narration.mp3", output_video="story_video.mp4"):
    print("Rendering High-Quality Cartoon Video...")
    audio_clip = AudioFileClip(audio_file)
    duration = audio_clip.duration

    # Reliable high-resolution cartoon background asset
    img_url = "https://img.freepik.com/free-vector/cartoon-park-landscape-with-green-grass-trees-hills_107791-16781.jpg"
    res = requests.get(img_url)
    with open("bg.jpg", "wb") as f:
        f.write(res.content)
    
    img = Image.open("bg.jpg").resize((1080, 1920))
    img.save("bg.jpg")

    bg_clip = ImageClip("bg.jpg").with_duration(duration)
    video = CompositeVideoClip([bg_clip]).with_audio(audio_clip)
    
    # Bulletproof rendering settings for mobile compatibility (Zero Black Screen)
    video.write_videofile(
        output_video, 
        fps=24, 
        codec="libx264", 
        audio_codec="aac", 
        preset="medium", 
        ffmpeg_params=["-pix_fmt", "yuv420p"]
    )
    print("Video rendered successfully without errors!")

def upload_to_youtube(video_path, title):
    client_id = os.getenv("YOUTUBE_CLIENT_ID")
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        print("YouTube credentials missing. Skipping upload for now.")
        return

    creds = Credentials(None, refresh_token=refresh_token, token_uri="https://oauth2.googleapis.com/token", client_id=client_id, client_secret=client_secret)
    youtube = build("youtube", "v3", credentials=creds)

    request_body = {
        "snippet": {
            "title": f"{title} | Hindi Cartoon Story #Shorts",
            "description": "Dekhiye sabse majedar hindi cartoon moral stories! Subscribe for daily fun. #shorts #cartoon #moralstories",
            "tags": ["shorts", "hindi stories", "cartoon", "moral story", "kids animation"],
            "categoryId": "15"
        },
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": True}
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
    request.execute()
    print("Uploaded to YouTube successfully!")

if __name__ == "__main__":
    print("Starting AI Toon Pipeline...")
    story_text, story_title = generate_episodic_story()
    asyncio.run(generate_voiceover(story_text))
    create_video()
    try:
        upload_to_youtube("story_video.mp4", story_title)
    except Exception as e:
        print(f"Upload status note: {e}")

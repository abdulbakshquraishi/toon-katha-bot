import os
import json
import asyncio
import requests
import google.generativeai as genai
import edge_tts
from moviepy import AudioFileClip, VideoFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips
from PIL import Image
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
            "Generate an engaging, trending Hindi cartoon moral story for kids in 5 parts. "
            "Write Part 1 as a detailed 45-60 second YouTube Shorts narration script in simple Hindi. "
            "Start with 'Title: [Story Title]' at the top. Make it funny, exciting, and end with a strong cliffhanger hook. "
            "Do NOT include scene directions or brackets in speech text."
        )
    else:
        prompt = (
            f"We are continuing the Hindi cartoon story '{story_title}'. "
            f"Write Part {current_part} of {total_parts} as a detailed 45-60 second YouTube Shorts narration script in simple Hindi. "
            f"Keep high engagement, bright cartoon mood, and moral value."
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
            story_title = "PunToon Kids Story"
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

def download_cartoon_visuals(duration_needed, output_video="bg_clip.mp4"):
    # Fetching cartoon animation loop clip
    video_urls = [
        "https://assets.mixkit.co/videos/preview/mixkit-cartoon-forest-landscape-42861-large.mp4",
        "https://assets.mixkit.co/videos/preview/mixkit-2d-animation-of-a-jungle-41584-large.mp4"
    ]
    
    for url in video_urls:
        try:
            res = requests.get(url, stream=True, timeout=10)
            if res.status_code == 200:
                with open(output_video, "wb") as f:
                    for chunk in res.iter_content(chunk_size=1024*1024):
                        f.write(chunk)
                print("Downloaded dynamic animated cartoon clip!")
                return True
        except Exception as e:
            print(f"Video download attempt failed: {e}")

    # Fallback to styled image if video fetch fails
    img_url = "https://img.freepik.com/free-vector/cartoon-park-landscape-with-green-grass-trees-hills_107791-16781.jpg"
    res = requests.get(img_url)
    if res.status_code == 200:
        with open("bg.jpg", "wb") as f:
            f.write(res.content)
        img = Image.open("bg.jpg").resize((1080, 1920))
        img.save("bg.jpg")
    return False

def create_video(story_title, audio_file="narration.mp3", output_video="story_video.mp4"):
    print("Rendering Animated Cartoon Video...")
    audio_clip = AudioFileClip(audio_file)
    duration = audio_clip.duration

    has_video = download_cartoon_visuals(duration)

    if has_video and os.path.exists("bg_clip.mp4"):
        clip = VideoFileClip("bg_clip.mp4")
        if clip.duration < duration:
            # Loop clip to match audio length
            loop_count = int(duration / clip.duration) + 1
            clip = concatenate_videoclips([clip] * loop_count)
        clip = clip.subclipped(0, duration).resized((1080, 1920))
    else:
        clip = ImageClip("bg.jpg").with_duration(duration)

    video = CompositeVideoClip([clip]).with_audio(audio_clip)
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
            "title": f"{title} | Animated Hindi Story #Shorts",
            "description": "Watch full animated Hindi cartoon story! #shorts #cartoon #moralstories",
            "tags": ["shorts", "hindi stories", "cartoon", "puntoon kids", "moral story"],
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

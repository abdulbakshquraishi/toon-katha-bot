import os
import json
import asyncio
import requests
import edge_tts
from moviepy import AudioFileClip, ImageClip, CompositeVideoClip
from PIL import Image
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

PROGRESS_FILE = "progress.json"

def get_current_progress():
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"current_part": 1, "total_parts": 5}

def save_progress(progress):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=4, ensure_ascii=False)

def generate_offline_script():
    progress = get_current_progress()
    part = progress.get("current_part", 1)
    
    # Pre-baked high-engagement moral stories script parts to completely bypass API quotas forever!
    stories = {
        1: ("Sacha Mitra", "Ek gaon mein do dost rehte the - Ram aur Shyam. Musibat ke waqt Ram ne Shyam ka sath diya. Isse yeh sikh milti hai ki sache dost wahi hain jo mushkil mein kaam aayein."),
        2: ("Lalach ka Phal", "Ek din ek lalachu kisan ko sone ka anda dene wali murgi mili. Usne jaldi ameer banne ke liye murgi ko hi kaat diya aur kuch nahi mila. Lalach buri bala hai."),
        3: ("Mehnat ki Taqat", "Rahul padhai se bhagta tha. Par jab usne mehnat ki, toh class mein top kiya. Mehnat karne walon ki kabhi haar nahi hoti."),
        4: ("Bado ka Aadar", "Ek chhota bachcha rozsubah bujurgon ki seva karta tha. Aage chalkar wahi bacha sabse bada insaan bana. Bado ka aadar hi asli dharm hai."),
        5: ("Sach ki Jeet", "Ek gariin imandaar ladke ko raste mein sona mila, usne malik ko lauta diya. Imandaari hi sabse badi poonji hai.")
    }
    
    title, text = stories.get(part, stories[1])
    
    if part >= 5:
        progress["current_part"] = 1
    else:
        progress["current_part"] += 1
        
    save_progress(progress)
    return title, text

async def generate_voiceover(text, output_file="narration.mp3"):
    communicate = edge_tts.Communicate(text, voice="hi-IN-SwaraNeural")
    await communicate.save(output_file)
    print("Voiceover generated successfully!")

def create_video(audio_file="narration.mp3", output_video="story_video.mp4"):
    print("Rendering High-Quality Video...")
    audio_clip = AudioFileClip(audio_file)
    duration = audio_clip.duration

    img_url = "https://img.freepik.com/free-vector/cartoon-park-landscape-with-green-grass-trees-hills_107791-16781.jpg"
    res = requests.get(img_url)
    with open("bg.jpg", "wb") as f:
        f.write(res.content)
    
    img = Image.open("bg.jpg").resize((1080, 1920))
    img.save("bg.jpg")

    bg_clip = ImageClip("bg.jpg").with_duration(duration)
    video = CompositeVideoClip([bg_clip]).with_audio(audio_clip)
    
    video.write_videofile(
        output_video, 
        fps=24, 
        codec="libx264", 
        audio_codec="aac", 
        preset="medium", 
        ffmpeg_params=["-pix_fmt", "yuv420p"]
    )
    print("Video rendered successfully!")

def upload_to_youtube(video_path, title):
    client_id = os.getenv("YOUTUBE_CLIENT_ID")
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        print("YouTube credentials missing. Skipping upload.")
        return

    creds = Credentials(None, refresh_token=refresh_token, token_uri="https://oauth2.googleapis.com/token", client_id=client_id, client_secret=client_secret)
    youtube = build("youtube", "v3", credentials=creds)

    request_body = {
        "snippet": {
            "title": f"{title} | Hindi Moral Stories #Shorts",
            "description": "Dekhiye sabse behtareen hindi moral stories! Subscribe for daily fun. #shorts #moralstories #hindistories",
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
    print("Starting Hardcore Automated Pipeline...")
    title, text = generate_offline_script()
    asyncio.run(generate_voiceover(text))
    create_video()
    try:
        upload_to_youtube("story_video.mp4", title)
    except Exception as e:
        print(f"Upload note: {e}")

import os
import json
import asyncio
import numpy as np
import edge_tts
from moviepy import AudioFileClip, ImageClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont
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
    return {"current_part": 1}

def save_progress(progress):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=4, ensure_ascii=False)

def generate_full_story():
    progress = get_current_progress()
    part = progress.get("current_part", 1)
    
    stories = {
        1: ("Sacche Dost Ki Kahani", 
            "Ek sundar jungle mein do dost rehte the, Ramesh aur Suresh. Dono hamesha ek doosre ki madad karte the. "
            "Ek din jungle mein ek bada shikar aa gaya. Suresh ne bina apni jaan ki parwah kiye Ramesh ko bachaya. "
            "Isse humein yeh seekh milti hai ki saccha dost wohi hai jo mushkil waqt mein hamesha aapke sath khada rahe."),
        2: ("Lalach Ka Bura Nateeja", 
            "Ek gaon mein ek kisan rehta tha jiske paas ek anokhi murgi thi. Woh murgi roz sone ka ek anda deti thi. "
            "Kisan ne lalach mein aakar socha ki murgi ke pet se saare ande ek sath nikal leta hoon. "
            "Usne murgi ko kaat diya aur uske haath kuch nahi aaya. Lalach hamesha nuksan hi karwata hai."),
        3: ("Mehnat Aur Lagan", 
            "Rohan padhai mein thoda kamzor tha, lekin usne kabhi haar nahi maani. Woh roz der raat tak mehnat karta raha. "
            "Pariksha ke din aaye aur Rohan ne poore school mein pehla sthan prapt kiya. "
            "Koshish karne walon ki kabhi haar nahi hoti, bas mehnat par vishwas rakhein.")
    }
    
    title, text = stories.get(part, stories[1])
    
    if part >= 3:
        progress["current_part"] = 1
    else:
        progress["current_part"] += 1
        
    save_progress(progress)
    return title, text

async def generate_voiceover(text, output_file="narration.mp3"):
    # Loud and clear voice parameters
    communicate = edge_tts.Communicate(text, voice="hi-IN-SwaraNeural", rate="+0%", volume="+50%")
    await communicate.save(output_file)
    print("Voiceover generated successfully!")

def create_hd_background():
    # Generate clean 1080x1920 HD gradient background
    img = Image.new("RGB", (1080, 1920), color=(34, 139, 34))
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 1030, 1870], outline=(255, 215, 0), width=15)
    img.save("bg.jpg")

def create_video(audio_file="narration.mp3", output_video="story_video.mp4"):
    print("Rendering HD High-Volume Video...")
    audio_clip = AudioFileClip(audio_file)
    duration = audio_clip.duration

    create_hd_background()

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
            "tags": ["shorts", "hindi stories", "cartoon", "moral story"],
            "categoryId": "15"
        },
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": True}
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
    request.execute()
    print("Uploaded to YouTube successfully!")

if __name__ == "__main__":
    print("Starting Automated YouTube Pipeline...")
    title, text = generate_full_story()
    asyncio.run(generate_voiceover(text))
    create_video()
    try:
        upload_to_youtube("story_video.mp4", title)
    except Exception as e:
        print(f"Upload note: {e}")

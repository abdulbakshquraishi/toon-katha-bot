import os
import json
import asyncio
import requests
import edge_tts
from moviepy import AudioFileClip, ImageClip, TextClip, CompositeVideoClip
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
        1: ("Sacche Dost Ki Anokhi Kahani", 
            "Ek ghane jungle mein do sacche dost Ramesh aur Suresh rehte the. Dono hamesha ek doosre ki madad karte the. "
            "Ek din jab unpar ek bada sankat aaya, toh Suresh ne apni jaan par khel kar Ramesh ko bachaya. "
            "Dosto, isse humein yeh seekh milti hai ki saccha dost wohi hai jo har musibat mein aapka sath de!"),
        2: ("Lalach Ka Bura Nateeja", 
            "Ek gaon mein ek lalachu kisan ke paas ek anokhi murgi thi jo roz sone ka anda deti thi. "
            "Kisan ne socha ki ek hi baar mein saare ande nikal kar ameer ban jau. "
            "Usne murgi ko kaat diya aur uske haath kuch nahi aaya. Lalach hamesha nuksan hi karwata hai."),
        3: ("Mehnat Se Hi Jeet Hai", 
            "Rohan padhai mein kamzor tha par usne kabhi koshish karna nahi chhoda. Woh roz din-raat mehnat karta raha. "
            "Jab pariksha ka result aaya toh Rohan ne poore district mein top kiya. "
            "Mehnat karne walon ki kabhi haar nahi hoti, bas apne sapno par vishwas rakhein.")
    }
    
    title, text = stories.get(part, stories[1])
    
    if part >= 3:
        progress["current_part"] = 1
    else:
        progress["current_part"] += 1
        
    save_progress(progress)
    return title, text

async def generate_voiceover(text, output_file="narration.mp3"):
    communicate = edge_tts.Communicate(text, voice="hi-IN-SwaraNeural", rate="-5%", volume="+50%")
    await communicate.save(output_file)
    print("Voiceover generated successfully!")

def fetch_cartoon_image():
    print("Fetching High-Quality Cartoon Image...")
    prompt = "cartoon style cute jungle animation story scene for kids, 8k resolution, vibrant colors"
    url = f"https://image.pollinations.ai/prompt/{prompt}?width=1080&height=1920&nologo=true"
    res = requests.get(url)
    with open("bg.jpg", "wb") as f:
        f.write(res.content)
    print("Cartoon image fetched successfully!")

def create_video(title, audio_file="narration.mp3", output_video="story_video.mp4"):
    print("Rendering Next-Level Video...")
    audio_clip = AudioFileClip(audio_file)
    duration = audio_clip.duration

    fetch_cartoon_image()

    bg_clip = ImageClip("bg.jpg").with_duration(duration)
    
    # Subtitle Overlay
    try:
        txt_clip = TextClip(
            text=f"✨ {title} ✨", 
            font_size=50, 
            color='yellow', 
            bg_color='black',
            size=(1000, None), 
            method='caption'
        ).with_position(('center', 200)).with_duration(duration)
        video = CompositeVideoClip([bg_clip, txt_clip]).with_audio(audio_clip)
    except Exception as e:
        print(f"Subtitle note: {e}, rendering basic visual.")
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
    create_video(title)
    try:
        upload_to_youtube("story_video.mp4", title)
    except Exception as e:
        print(f"Upload note: {e}")

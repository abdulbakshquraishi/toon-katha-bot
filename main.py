import os
import json
import asyncio
import requests
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
        1: ("Sher Aur Chuhiya", 
            "Ek din jungle mein ek bada sher so raha tha. Ek choti chuhiya ne uski peeth par koodna shuru kiya. "
            "Sher ki neend khul gayi aur usne chuhiya ko pakad liya. Chuhiya boli, 'Mujhe chhod do, kabhi main bhi kaam aaungi.' "
            "Kuch din baad sher shikaari ke jaal mein fas gaya. Chuhiya ne aakar jaal kaat diya aur sher ki jaan bachai. "
            "Sikh: Har choti cheez ka apna bada mahatva hota hai!"),
        2: ("Chatur Khargosh", 
            "Jungle ka ek ghamandi sher roz be-wajah janwaro ko marta tha. Sabhi ne milkar tay kiya ki roz ek janwar khud sher ke paas jayega. "
            "Ek din chatur khargosh ki baari aayi. Woh der se sher ke paas gaya aur bola, 'Raja ji, raste mein ek aur sher mil gaya tha.' "
            "Gusse mein sher kuye ke paas gaya aur apni hi parchhai dekh kar kuye mein kood gaya. "
            "Sikh: Bal se nahi, buddhi se jeet milti hai!"),
        3: ("Jadui Murgi", 
            "Ek kisan ke paas ek aisi murgi thi jo roz sone ka anda deti thi. Kisan roz us ande ko bechkar ameer banta ja raha tha. "
            "Lekin kisan ke dil mein lalach aa gaya ki woh ek hi baar mein saare ande nikal lega. "
            "Usne murgi ko kaat diya aur uske haath kuch nahi laga. "
            "Sikh: Lalach karne walon ka hamesha nuksan hota hai!")
    }
    
    title, text = stories.get(part, stories[1])
    
    if part >= 3:
        progress["current_part"] = 1
    else:
        progress["current_part"] += 1
        
    save_progress(progress)
    return title, text

async def generate_voiceover(text, output_file="narration.mp3"):
    communicate = edge_tts.Communicate(text, voice="hi-IN-SwaraNeural", rate="+5%", volume="+60%")
    await communicate.save(output_file)
    print("Voiceover generated successfully!")

def fetch_multiple_cartoon_images():
    print("Fetching Multiple 3D Animated Scenes...")
    prompts = [
        "Cute 3D Pixar style giant lion sleeping in magical jungle, vibrant colors, 8k vertical",
        "Cute tiny cartoon mouse talking to big friendly lion in bright forest, 3d animation",
        "Happy cartoon animals celebrating together in magical glowing jungle, 3d pixar style"
    ]
    
    for i, prompt in enumerate(prompts):
        url = f"https://image.pollinations.ai/prompt/{prompt}?width=1080&height=1920&nologo=true"
        res = requests.get(url)
        with open(f"bg_{i+1}.jpg", "wb") as f:
            f.write(res.content)
    print("All 3D cartoon scenes fetched successfully!")

def create_video(title, audio_file="narration.mp3", output_video="story_video.mp4"):
    print("Rendering Multi-Scene Dynamic Video...")
    audio_clip = AudioFileClip(audio_file)
    duration = audio_clip.duration

    fetch_multiple_cartoon_images()

    # Split total duration across 3 clips for changing scenes
    clip_duration = duration / 3.0

    img1 = ImageClip("bg_1.jpg").with_duration(clip_duration)
    img2 = ImageClip("bg_2.jpg").with_duration(clip_duration)
    img3 = ImageClip("bg_3.jpg").with_duration(duration - (clip_duration * 2))

    from moviepy import concatenate_videoclips
    background_sequence = concatenate_videoclips([img1, img2, img3])

    video = background_sequence.with_audio(audio_clip)
    
    video.write_videofile(
        output_video, 
        fps=24, 
        codec="libx264", 
        audio_codec="aac", 
        preset="medium", 
        ffmpeg_params=["-pix_fmt", "yuv420p"]
    )
    print("Multi-scene video rendered successfully!")

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
            "description": "Dekhiye sabse behtareen 3D animated kahaniyan! Subscribe for more. #shorts #moralstories #cartoon",
            "tags": ["shorts", "hindi stories", "cartoon", "moral story", "3d animation"],
            "categoryId": "15"
        },
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": True}
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
    request.execute()
    print("Uploaded to YouTube successfully!")

if __name__ == "__main__":
    print("Starting Multi-Scene Automated Pipeline...")
    title, text = generate_full_story()
    asyncio.run(generate_voiceover(text))
    create_video(title)
    try:
        upload_to_youtube("story_video.mp4", title)
    except Exception as e:
        print(f"Upload note: {e}")

import os
import json
import asyncio
import requests
import edge_tts
from moviepy import AudioFileClip, ImageClip, CompositeVideoClip
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
    
    # 50-60 seconds detailed stories for high kid engagement
    stories = {
        1: ("Sher Aur Choti Chuhiya Ki Kahani", 
            "Ek bada aur shaktishali sher jungle mein gehri neend mein so raha tha. "
            "Tabhi ek choti si natkhat chuhiya wahan aayi aur sher ki peeth par koodne lagi. "
            "Sher gusse mein jaag gaya aur usne chuhiya ko apne panje mein pakad liya. "
            "Chuhiya ne rokar kaha, 'Mera yakin karo maharaj, ek din main aapki madad karungi.' "
            "Sher ko hansi aayi par usne chuhiya ko chhod diya. "
            "Khabar faili ki kuch dino baad sher ek shikari ke jaal mein fas gaya. "
            "Chuhiya ne apne teez daanto se jaal ko kaat diya aur sher ki jaan bachaye. "
            "Dosto, isse seekh milti hai ki koi chota ho ya bada, har kisi ka apna ek mahatva hota hai!"),
        2: ("Chatur Khargosh Aur Bada Sher", 
            "Jungle ka raja sher roz bina wajah kayi janwaro ka shikar karta tha. "
            "Sabhi janwaro ne milkar fasla kiya ki roz ek janwar sher ke paas bhojan ban kar jayega. "
            "Ek din ek chatur khargosh ki baari aayi. Khargosh jaankarloot kar der se gaya. "
            "Sher gusse mein garja, 'Itni der kyun ki?' "
            "Khargosh ne kaha, 'Raja sahab, raste mein dusre sher ne mujhe rok liya tha.' "
            "Sher gusse mein us kuye ke paas gaya aur kuye mein apni hi parchhai dekh kar kood gaya. "
            "Sikh: Dosto, buddhi ki taqat sabse badi hoti hai!"),
        3: ("Jadui Murgi Aur Lalach", 
            "Ek garib kisan ke paas ek anokhi murgi thi jo roz subah sone ka ek anda deti thi. "
            "Kisan roz us ande ko bechkar aaram se apna guzara karta tha. "
            "Par ek din kisan ke dimaag mein lalach aa gaya. "
            "Usne socha ki agar murgi ke pet ko kaat doon toh saare sone ke ande ek sath mil jayenge. "
            "Usne murgi ko kaat diya par andar kuch nahi tha. "
            "Sikh: Lalach karna sabse bura hota hai, jo paas hai usme khush rahein.")
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
    print("Long clear voiceover generated successfully!")

def fetch_cartoon_image():
    print("Fetching Vibrant 3D Animated Visual...")
    # Ultra High Quality 3D Pixar Style Cartoon Prompt for kids
    prompt = "Cute 3D Pixar animation style lion and mouse story scene in magical vibrant colorful jungle, 8k vertical shorts wallpaper, hyper detailed, trending on artstation"
    url = f"https://image.pollinations.ai/prompt/{prompt}?width=1080&height=1920&nologo=true"
    res = requests.get(url)
    with open("bg.jpg", "wb") as f:
        f.write(res.content)
    print("3D visual fetched successfully!")

def create_video(title, audio_file="narration.mp3", output_video="story_video.mp4"):
    print("Rendering Full Length Cartoon Video...")
    audio_clip = AudioFileClip(audio_file)
    duration = audio_clip.duration

    fetch_cartoon_image()

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
    print(f"Video rendered successfully! Total Duration: {duration} seconds.")

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
            "title": f"{title} | 3D Hindi Moral Stories #Shorts",
            "description": "Dekhiye sabse majedar 3D cartoon kahaniyan! Channel ko subscribe karein. #shorts #moralstories #cartoon #kids",
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
    print("Starting Automated YouTube Pipeline...")
    title, text = generate_full_story()
    asyncio.run(generate_voiceover(text))
    create_video(title)
    try:
        upload_to_youtube("story_video.mp4", title)
    except Exception as e:
        print(f"Upload note: {e}")

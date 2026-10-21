import os
import json
import google.generativeai as genai

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
            "Generate an engaging, high-hook moral or suspense story outline for kids/youth in 5 short parts. "
            "Now write ONLY Part 1 of 5 as a 30-second YouTube Short script in simple Hindi. "
            "Start with 'Title: [Story Title]' at the top and end with a strong cliffhanger hook for Part 2."
        )
    else:
        prompt = (
            f"We are continuing the Hindi story '{story_title}'. "
            f"Write ONLY Part {current_part} of {total_parts} as a 30-second YouTube Short script in simple Hindi. "
            f"Maintain high suspense and end with a hook for the next episode."
        )

    response = model.generate_content(prompt)
    story_text = response.text

    print(f"--- Episode {current_part}/{total_parts} Generated ---")
    print(story_text)

    # Extract title if Part 1
    if current_part == 1:
        lines = story_text.splitlines()
        for line in lines:
            if "Title:" in line or "शीर्षक:" in line or "कहानी:" in line:
                story_title = line.replace("Title:", "").replace("शीर्षक:", "").replace("कहानी:", "").strip()
                break
        if not story_title:
            story_title = "Trending Katha Series"
        progress["story_title"] = story_title

    # Update Part progress
    if current_part >= total_parts:
        progress["current_part"] = 1
        progress["story_title"] = ""
    else:
        progress["current_part"] += 1

    save_progress(progress)

if __name__ == "__main__":
    print("Starting ToonKatha Daily Episode Pipeline...")
    generate_episodic_story()

import os
import google.generativeai as genai

# Gemini API Configure
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_KEY)

def generate_kids_story():
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = "Write a short 30-second moral story for kids in simple Hindi. Include 3 visual scene descriptions."
    response = model.generate_content(prompt)
    print("--- Generated Story ---")
    print(response.text)

if __name__ == "__main__":
    print("Starting ToonKatha Automation Pipeline...")
    generate_kids_story()
  

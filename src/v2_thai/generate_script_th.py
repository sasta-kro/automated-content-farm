import asyncio # for async functions

from dotenv import load_dotenv # to load env variables
import os # also to load the api key

from google import genai # import gemini
from google.genai import types  # thinking mode and extra ai features
from pydantic import BaseModel, Field

import json  # to parse json from gemini response



# Load API Key
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

# Define the output schema using Pydantic for strict typing (New SDK feature)
class ThaiScriptOutput(BaseModel):
    title_thai: str = Field(description="A catchy, clickbait title in Thai for the video cover")
    script_thai: str = Field(description="The viral short story script in Thai, slang allowed")
    gender: str = Field(description="The gender of the narrator: 'M' or 'F'")

async def generate_thai_script(
        topic: str = "spicy cheating story that got karma",
        time_length: str = "30-45"):
    """
    Generates a viral-style Thai short-form script using Gemini.
    Returns: JSON with title_thai, script_thai, and gender.
    """
    print(f"1. 🇹🇭 Asking Gemini to cook up a '{topic}' story script in Thai...")

    if not gemini_api_key:
        raise ValueError("❌ Error: GEMINI_API_KEY not found in .env file")

    client = genai.Client(api_key=gemini_api_key)

    # System Instruction: The "Persona"
    # We tell Gemini it is a famous Thai TikTok/Pantip storyteller.
    system_instruction = f"""
    You are a famous Thai TikTok/Reels storyteller (นักเล่าเรื่องในโซเชียล). 
    Your style is:
    - Tone: Gossip (เม้าท์มอย), Exciting (ตื่นเต้น), and Dramatic (ดราม่า).
    - Language: Use natural Thai internet slang (e.g., แก, คือแบบ, พีคมาก, แม่เจ้า, สรุปนะ).
    - NO formal language (ห้ามใช้ภาษาทางการ).
    - The story must be narrated in the First Person POV ("ฉัน" or "ผม").
    - Structure:
        1. HOOK (0-3s): Shocking statement to stop scrolling.
        2. BODY: Fast-paced storytelling, keep it juicy.
        3. PLOT TWIST/ENDING: Unexpected or funny conclusion.
    
    Target length: {time_length} seconds spoken 
    """
    # (approx 300-400 Thai characters for 40-60 secs)

    # User Prompt
    prompt = f"""
    Generate a script for a short video about: "{topic}".
    If the topic is "random", invent a viral-worthy story (e.g., cheating, office drama, lottery, ghost, revenge).
    
    Determine the most appropriate gender for the narrator based on the story (e.g., cheating boyfriend story -> Female narrator).
    
    OUTPUT FORMAT:
    Return strictly raw JSON. Do not use Markdown code blocks.
    {{
        "title_thai": "Catchy headline in Thai for the cover",
        "script_thai": "The full spoken script in Thai...",
        "gender": "F"
    }}
    """

    try:
        # Using the new google-genai SDK with structured output
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json", # Forces JSON output
                response_schema=ThaiScriptOutput, # Enforces the Pydantic schema
                temperature=1.2, # High temperature = more creative/drama
            ),
            contents=prompt
        )
        # The SDK might return a parsed object or text depending on the version.
        # We handle the text parsing to be safe with the 'response_mime_type' enforcement

        # Parse JSON
        raw_json = response.text
        data = json.loads(raw_json)

        print(f"Title: {data.get('title_thai')}")
        print(f"Gender: {data.get('gender')}")
        print(f"Full Script: {data.get('script_thai')}...")

        return data

    except Exception as e:
        print(f"❌ Error generating script: {e}")
        # Return a dummy fallback for testing if API fails
        return None

if __name__ == "__main__":
    # Test the function
    # Example topics: "catfish date", "office horror story", "winning lottery", "mother-in-law horror"
    # Use "random viral story" to let Gemini be creative
    result = asyncio.run(
        generate_thai_script(
            topic="caught boyfriend cheating with my mother",
            time_length="30-45"
            )
    )

    if result:
        # Save to a file to verify output
        with open("current_script.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        print("\nSaved full result to 'current_script.json'")
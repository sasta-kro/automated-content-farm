import asyncio # for async functions

from dotenv import load_dotenv # to load env variables
import os # also to load the api key

from google import genai # import gemini
from google.genai import types  # thinking mode and extra ai features
from pydantic import BaseModel, Field

import json  # to parse json from gemini response

from src.v2_thai.Util_functions import save_json_file

# Load API Key
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

# Define the output schema using Pydantic for strict typing (New SDK feature)
class ThaiScriptOutput(BaseModel):
    title_thai: str = Field(description="A catchy, clickbait title in Thai for the video cover")
    script_thai: str = Field(description="The viral short story script in Thai, slang allowed")
    gender: str = Field(description="The gender of the narrator: 'M' or 'F'")

async def generate_thai_script_data(
        topic: str = "spicy cheating story that got karma",
        time_length: str = "30-45", # default param
        output_folder_path: str = ""
):
    """
    Generates a viral-style Thai short-form script using Gemini.
    WARNING: `time_length` is not very accurate, it returns something longer

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

    # User Prompt
    prompt = f"""
    Generate a script for a short video about: "{topic}".
    If the topic is "random", invent a viral-worthy story (e.g., cheating, office drama, lottery, ghost, revenge).
    
    Determine the most appropriate gender for the narrator based on the story 
    (e.g., cheating boyfriend story -> Female narrator 'F', going to brothel and ended up with ladyboy -> Male narrator 'M').
    
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
            contents=prompt,

            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json", # Forces JSON output
                response_schema=ThaiScriptOutput, # Enforces the Pydantic schema
                temperature=1.25, # High temperature = more creative/drama
            ),
        )
        # The SDK might return a parsed object or text depending on the version.
        # We handle the text parsing to be safe with the 'response_mime_type' enforcement

        # Parse JSON
        raw_json = response.text
        data = json.loads(raw_json)

        print(f"Title: {data.get('title_thai')}")
        print(f"Gender: {data.get('gender')}")
        print(f"Full Script ('script_thai'): {data.get('script_thai')}...")

        # Save to a JSON file for inspection
        output_json_file_name = "original_script_data_th.json"
        full_json_save_location = os.path.join(output_folder_path, output_json_file_name)
        save_json_file(data, full_json_save_location)

        return data

    except Exception as e:
        print(f"❌ Error generating script: {e}")
        raise e
        # Return a dummy fallback for testing if API fails


# for translation
async def translate_thai_content_to_eng(thai_content):
    """
    Translates Thai social media content to English with full cultural nuance.

    Args:
        thai_content (dict): A dictionary containing 'title_thai', 'script_thai', and 'gender'.
    """
    print(" 🇬🇧 Translating the Thai content to English...")
    client = genai.Client(api_key=gemini_api_key)


    prompt = f"""
    You are an expert Localization Specialist and Translator who specializes in Thai Social Media Culture and English Gen Z/Internet Slang.

    YOUR TASK:
    Translate the following Thai content into English.
    
    INPUT DATA:
    {thai_content}
    
    CRITICAL INSTRUCTIONS:
    1. The translation must match the energy of the source. If the Thai text is gossipy ("Mao Moi"), dramatic, or uses slang (e.g., "Gae", "Pirood", "Peak"), the English must use equivalent Internet slang) 
    2. Pay attention to the 'gender' field. If 'F', use feminine/bestie slang if appropriate. If 'M', adjust accordingly.
    3. No Censorship of Vibe: Keep exclamation marks, caps, and the chaotic energy of the original post.
    4. Do not output conversational filler.
    """

    response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=prompt,
    config=types.GenerateContentConfig(
        # This enables the thinking capability
        thinking_config=types.ThinkingConfig(
            # include_thoughts=True, # Returns the 'thoughts' in the response
            thinking_budget=3000   # Token budget for thinking (1024 is a good start)
        )
    )
)
    raw_text = response.text.strip()
    print(raw_text)
    print("-----Translation finished----\n")
    return raw_text



if __name__ == "__main__":
    # Test the function
    # Example topics: "catfish date", "office horror story", "winning lottery", "mother-in-law horror"
    # Use "random viral story" to let Gemini be creative
    result = asyncio.run(
        generate_thai_script_data(
            topic=  "guy discovers my sister working in a brothel", #"caught boyfriend cheating with my mother",
            time_length="30-45"
            )
    )

    # translate to English so that I can understand
    if result is not None:
        asyncio.run(
            translate_thai_content_to_eng(result)
        )

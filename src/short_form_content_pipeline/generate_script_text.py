import asyncio # for async functions
import os # to manage paths
import json  # to parse json from gemini response
from google import genai # import gemini
from google.genai import types  # thinking mode and extra ai features
from pydantic import BaseModel, Field # to use the settings from config file


# utils
from src.short_form_content_pipeline.Util_functions import save_json_file, set_debug_dir_for_module_of_pipeline

# Import constants that are in another file
from src.short_form_content_pipeline._CONSTANTS import (
    SCRIPT_GEN_SYSTEM_INSTRUCTION,
    SCRIPT_GEN_USER_PROMPT,
    SCRIPT_TRANSLATION_PROMPT
)

async def generate_script_data_json(
        # default arguments are removed to reduce Order of Operation complications.
        # now arguments MUST be passed

        language: str,
        topic: str,
        time_length: str,
        gemini_model_id: str,
        gemini_api_key: str,
        temperature: float,
        output_folder_path: str,
):
    """
    Generates a viral-style Thai short-form script using Gemini.
    WARNING: `time_length` is not very accurate, it returns something longer like about 1.3 to 1.4 times
    Uses settings from src.config.SETTINGS (loaded from YAML).

    Returns: JSON with title_text, script_text, and gender
    """

    # Defining the output schema using Pydantic for strict typing
    # (inside the function so that it gets the `language` argument
    class ScriptOutputData(BaseModel):
        title_text: str = Field(description=f"A catchy, clickbait title in {language} for the video cover")
        script_text: str = Field(description=f"The viral short story script in {language}, slang allowed")
        gender: str = Field(description="The gender of the narrator: 'M' or 'F'")


    print(f"1. 🇹🇭 Asking {gemini_model_id} to cook up a '{topic}' story script in {language}...")

    # Initialize Client with Global Settings (stored in config)
    if not gemini_api_key:
        raise ValueError("❌ Error: GEMINI_API_KEY is missing in Settings!")

    client = genai.Client(api_key=gemini_api_key)

    # Construct prompts using Constants + Config injection


    # System Instruction: The "Persona"
    # We tell Gemini it is a famous Thai TikTok/Reel storyteller.
    system_instruction = SCRIPT_GEN_SYSTEM_INSTRUCTION.format(
        language=language,
        time_length=time_length,
    )


    # User Prompt
    prompt = SCRIPT_GEN_USER_PROMPT.format(
        topic=topic,
        language=language
    )

    try:
        # Using the new google-genai SDK with structured output
        response = client.models.generate_content(
            model=gemini_model_id,
            contents=prompt,

            # The SDK might return a parsed object or text depending on the version.
            # We handle the text parsing to be safe with the 'response_mime_type' enforcement
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",  # Forces JSON output
                response_schema=ScriptOutputData,   # Enforces the Pydantic schema
                temperature=temperature,
            ),
        )
        if response: print("    (response received)")
        # if it crashes after receiving response, it means the data returned by the AI is not in the right format


        # Parse JSON
        raw_json = response.text
        data = json.loads(raw_json)

        print(f"Title: {data.get('title_text')}")
        print(f"Gender: {data.get('gender')}")
        print(f"Full Script ('script_text'): {data.get('script_text')}...")

        # Save to a JSON file for inspection
        output_json_file_name = "original_script_data.json"
        full_json_save_location = os.path.join(output_folder_path, output_json_file_name)
        save_json_file(data, full_json_save_location)

        print(" ")

        return data

    except Exception as e:
        print(f"❌ Error generating script: {e}")
        raise e


# for translation
async def translate_text_to_eng(
        non_english_content,
        language: str,
        gemini_api_key: str,
        gemini_model_id: str,
):
    """
    Translates non-english to English with full cultural nuance.

    non_english_content (dict): A dictionary containing 'title_text', 'script_text', and 'gender'.
    """
    print(f" 🇬🇧 Translating the {language} content to English...")
    client = genai.Client(api_key=gemini_api_key)


    # Use the constant template
    prompt = SCRIPT_TRANSLATION_PROMPT.format(
        language=language,
        content_data=non_english_content
    )

    response = client.models.generate_content(
    model=gemini_model_id,
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
    # Import config, settngs, and constants
    # IMPORTANT: settings are not imported at the start of the files
    # because Python works in a way where it causes undefined errors
    from src.short_form_content_pipeline._CONFIG import SETTINGS
    SETTINGS.load_profile("thai_funny_story.yaml")

    sub_debug_dir = "_d_script_generation"
    full_debug_dir = set_debug_dir_for_module_of_pipeline(sub_debug_dir)


    result = asyncio.run(
        generate_script_data_json(
            language="Thai",
            topic=  "tripped and fell onto dog poop", #"caught boyfriend cheating with my mother",
            time_length="30-45",
            gemini_model_id="gemini-2.5-pro",
            gemini_api_key= SETTINGS.GEMINI_API_KEY,
            temperature=SETTINGS.script_generation_temperature,
            output_folder_path=full_debug_dir
            )
    )

    # translate to English so that I can understand
    if result is not None:
        asyncio.run(
            translate_text_to_eng(
                non_english_content=result,
                language="Thai",
                gemini_api_key=SETTINGS.GEMINI_API_KEY,
                gemini_model_id="gemini-2.5-pro",
            )
        )

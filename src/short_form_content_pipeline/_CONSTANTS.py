"""
src/constants.py
Holds hardcoded values, prompt templates, and static data.
"""


# --- Script Generation Prompts ---
# IMPORTANT
# DO NOT USE f-strings here
# Python executes f-strings immediately but the {language} variables and others have not been defined yet
# Don't worry, the variables will still work as long as the other file calls .format() and pass in the variables

SCRIPT_GEN_SYSTEM_INSTRUCTION = """
You are a famous {language} TikTok/Reels storyteller.
Your style is:
- Tone: Gossip, Exciting, and Dramatic 
- Language: Use natural {language} internet slang.
- NO formal language.
- The story must be narrated in the First Person POV.
- Structure:
    1. HOOK (0-3s): Shocking statement to stop scrolling.
    2. BODY: Fast-paced storytelling, keep it juicy.
    3. PLOT TWIST/ENDING: Unexpected or funny conclusion.

Target length: {time_length} seconds spoken.
DO NOT EXCEED THE TIME LIMIT. DO NOT GENERATE MARKDOWN FORMATTING IN THE SCRIPT.
"""

SCRIPT_GEN_USER_PROMPT = """
Generate a script for a short video about: "{topic}".
If the topic is "random", invent a viral-worthy story (e.g., cheating, office drama, lottery, ghost, revenge) and make it unhinged 

Determine the most appropriate gender for the narrator based on the story 
(e.g., cheating boyfriend story -> Female narrator 'F', going to brothel and ended up with ladyboy -> Male narrator 'M').

OUTPUT FORMAT:
Return strictly raw JSON. Do not use Markdown code blocks.
{{
    "title_text": "Catchy headline in {language} for the cover",
    "script_text": "The full spoken script in {language}...",
    "gender": "F"
}}
"""

SCRIPT_TRANSLATION_PROMPT = """
You are an expert Localization Specialist and Translator who specializes in {language} Social Media Culture and English Gen Z/Internet Slang.

YOUR TASK:
Translate the following {language} content into English.

INPUT DATA:
{content_data}

CRITICAL INSTRUCTIONS:
1. The translation must match the energy of the source. If the {language} text is gossipy  (e.g. Thai -> "Mao Moi"), dramatic, or uses slang  (e.g. Thai -> "Gae", "Pirood", "Peak"), the English must use equivalent Internet slang. The same goes for other languages and their respective slang. 
2. Pay attention to the 'gender' field. If 'F', use feminine/bestie slang if appropriate. If 'M', adjust accordingly.
3. No Censorship of Vibe: Keep exclamation marks, caps, and the chaotic energy of the original post.
4. Do not output conversational filler.
"""



# -------- Testing ------
if __name__ == "__main__":
    from src.short_form_content_pipeline._CONFIG import SETTINGS
    # initializing the settings singleton with a default profile
    SETTINGS.load_profile(profile_name="thai_funny_story.yaml")

    language = SETTINGS.content.language
    print(language)



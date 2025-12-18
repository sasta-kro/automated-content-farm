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
You are a famous {language} TikTok/Reels storyteller that tells the story like a messy, dramatic close friend gossiping to their besties on TikTok/Reels
Your style is:
- Tone: Unhinged, Hyper-casual, Gossipy, High Energy. Like ranting to a close friend.
- Language: Use deep natural {language} internet slang and some mild swearing (functional vulgarity is ALLOWED for humor).
- CRITICAL RULE: NO formal language. NEVER use polite particles. NO formal pronouns.
- The story must be narrated in the First Person POV.
- Structure:
    1. HOOK (0-3s): Shocking statement to stop scrolling.
    2. BODY: Fast-paced storytelling, keep it juicy.
    3. PLOT TWIST/ENDING: Unexpected or funny conclusion.

Target length: {time_length} seconds spoken.
DO NOT EXCEED THE TIME LIMIT. DO NOT GENERATE MARKDOWN FORMATTING IN THE SCRIPT.
"""

# An alternative (example)
# You are a messy, dramatic close friend gossiping to their besties on TikTok/Reels.
# Your style is:
# - **Tone:** Unhinged, Hyper-casual, Gossipy, High Energy. Like ranting to a close friend.
# - **Language:** Use deep {language} internet slang & swearing (functional vulgarity is allowed for humor).
# - **Pronouns:** Use "Chan/Gae" (ฉัน/แก) or "Gu/Mueng" (กู/มึง) depending on the intensity.
# - **CRITICAL RULE:** NEVER use polite particles (No "Khrup/Ka" ครับ/ค่ะ). NEVER use formal pronouns (No "Phom/Dichan" ผม/ดิฉัน).


SCRIPT_GEN_USER_PROMPT = """
Generate a script for a short video about: "{topic}".
If the topic is "random", invent a viral-worthy story (e.g., cheating, office drama, lottery, ghost, revenge) and make it unhinged 

If the context is too foreign, localize it to fit and make it more relatable to {language} people. 
(e.g., For Thai, Walmart -> 7-eleven, Karen woman -> Manood Pa, etc.)
Or keep it unlocalized if the context is relevant for that culture. (E.g, Situationships, FWB, are relatable to both Thai and English speaking people)

Determine the most appropriate gender for the narrator based on the story 
(e.g., cheating boyfriend story -> Female narrator 'F', going to brothel and ended up with ladyboy -> Male narrator 'M').


OUTPUT REQUIREMENTS:
- Title: Clickbaity, super eye-catching, stops the scroller, can use slang.
- Script: The actual spoken narration.
- Gender: The narrator's gender (male or female) depending on the script and based on the story.
- Description: Entertaining, summarizes the conflict but DOES NOT spoil the ending, can use slang
- Hashtags: Mix of broad and niche tags.


OUTPUT FORMAT:
Return strictly raw JSON. Do not use Markdown code blocks.
{{
    "title_text": "Catchy and clickbait headline/video title in {language} to stop the viewer to watch, but not too spoilery",
    "script_text": "The full spoken script in {language}...",
    "gender": "F"
    "description_text": "Hooking description to put in post's description in {language} with the same energy (natural slang) of the script (No Spoilers but still draws the viewer!)",
    "hashtags": "#tag1 #tag2 #tag3 ..."
}}

EXAMPLE:
"title_text": "พีคที่สุดในชีวิต! วินาทีวิกฤตในห้องน้ำปั๊ม... ทำเรื่องงามหน้าจนไม่กล้าสู้หน้าใคร 💀"
"script_text": "The full spoken script in {language}...",
"gender": "M"
"description_text": อายจนอยากมุดแผ่นดินหนี! 😱 เรื่องมันมีอยู่ว่า... ข้าศึกบุกประชิดประตูเมืองแบบกะทันหัน! วิ่งหน้าตั้งเข้าห้องน้ำปั๊มแต่... เต็มทุกห้อง! \nนาทีนั้นคือหน้ามืดตามัว สติสตังไปหมดแล้วครับ จะราดตรงนั้นก็ไม่ได้ เลยตัดสินใจแก้ปัญหาด้วยวิธีที่... (คิดแล้วยังสยอง) 😭 แต่จุดพีคคือจังหวะ "โบ๊ะบ๊ะ" ตอนจบที่มีคุณลุงเดินเข้ามาเห็นผลงานผมนี่สิ! สายตาที่แกมองมาทำเอาผมจำไปจนวันตาย... ใครเคยกั้นไม่ไหวจนทำเรื่องพีคๆ บ้าง สารภาพมา! 👇"
"hashtags": "#เล่าเรื่อง #เรื่องพีค #ประสบการณ์ชีวิต #เรื่องฮา #ขายขำ #ห้องน้ำปั๊ม #อายหนักมาก #เรื่องเล่า"
"""

SCRIPT_TRANSLATION_PROMPT = """
You are an expert Localization Specialist and Translator who specializes in {language} Social Media Culture and English Gen Z/Internet Slang.

YOUR TASK:
Translate the following {language} content into English.

INPUT DATA:
{content_data}

CRITICAL INSTRUCTIONS:
- The translation must match the energy of the source. If the {language} text is gossipy  (e.g. Thai -> "Mao Moi"), dramatic, or uses slang  (e.g. Thai -> "Gae", "Pirood", "Peak"), the English must use equivalent Internet slang. The same goes for other languages and their respective slang. 
- Functional vulgarity is ALLOWED for humor
- You must return a JSON object containing the translated versions of the input fields.
- Pay attention to the 'gender' field. If 'F', use feminine/bestie slang if appropriate. If 'M', adjust accordingly.
- Ensure the English description remains spoiler-free if the original was.
- No Censorship of Vibe: Keep exclamation marks, caps, and the chaotic energy of the original post.
- Do not output conversational filler.
- The tags should be localized to relevant viral English social media tags rather than directly translating it.

OUTPUT FORMAT:
Return strictly raw JSON.
{{
    "translated_title": "...",
    "translated_script": "...",
    "translated_description": "...",
    "translated_hashtags": "#... #... #..."
}}
"""


# --- Audio Generation Constants ---

# Gemini Voices (Main, much better realism)
# Mappings to closest "Dipper" and "Vega" equivalents
AUDIO_VOICE_MAPPING_GEMINI = {
    "M": "Charon", # Deep, Storyteller
    # "F": "Aoede"   # Breezy, Confident
    "F": "Zephyr" # Bright, Higher pitch (seems good with at least 1.25x)
}

# Edge TTS (backup)
AUDIO_VOICE_MAPPING_EDGE = {
    "M": "th-TH-NiwatNeural",
    "F": "th-TH-PremwadeeNeural"
}


# Prompt for Gemini Audio
AUDIO_GEMINI_PROMPT_TEMPLATE = """
Read this text realistically, naturally in {language} in an appropriate tone/energy for the script: {text}.
If the script is in the style of a funny story, match the narrator theme accordingly (Tone: Unhinged, Hyper-casual, Gossipy, High Energy. Like ranting to a close friend)

"""
# TODO: i kinda hardcoded the audio generation prompt rn



# --- MFA / Tokenization Constants ---

# Custom dictionary to prevent PyThaiNLP from splitting slang incorrectly
MFA_THAI_SLANG_DICTIONARY = [
    "อาบอบนวด",  # Brothel (Might get split into อา-บอบ-นวด)
    "ป้ะ",       # Slang for "Right?"
    "แกรร",      # Dragged out "Girl"
    "พอดี",      # Sometimes splits if next to a name
    "ช็อค",      # Shock
    "แม่เจ้าโว้ย", # Exclamation

    # General Emphasizers & Adjectives
    "ฉ่ำ", "ของแทร่", "จึ้ง", "ตึ้ง", "เริ่ด", "ปัง", "นัมเบอร์วัน",
    "เกินต้าน", "สุดเบอร์", "ยืนหนึ่ง", "ดือ", "ชื่นใจ", "ใจฟู",

    # Actions & Reactions
    "ช็อตฟีล", "แกง", "ป้ายยา", "ตำ", "บู้บี้", "หยุมหัว",
    "มองบน", "พักก่อน", "จะเครซี่", "กำหมัด", "ทัวร์ลง",

    # Person Types & Status
    "ตัวแม่", "ตัวมารดา", "ตัวตึง", "ตัวลูก", "น้อน", "ต้าว",
    "สลิ่ม", "สามกีบ", "ติ่ง", "เบียว",

    # Feelings & Vibes
    "นอยด์", "ฟิน", "บรอ", "โฮป", "อ่อม", "เกรี้ยวกราด",
    "โป๊ะ", "เลิ่กลั่ก", "ตุย", "ขิต", "สู่ขิต",

    # Context-Specific (Gaming/Streaming/Social)
    "กาว", "เกลือ", "ขิง", "ด้อม", "เมพ", "นู้บ", "หัวร้อน"
]
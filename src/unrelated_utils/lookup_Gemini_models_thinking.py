import os

from dotenv import load_dotenv
from google import genai

# Initialize the client (assumes GOOGLE_API_KEY is set in environment)
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client()

print(f"{'Model ID':<40} | {'Thinking Supported?'}")
print("-" * 60)

for m in client.models.list():
    # The 'thinking' attribute is a boolean in the new Model object
    # Some older or specific models might not have the attribute set, so we default to False
    supports_thinking = getattr(m, 'thinking', False)

    # Filter to show only models that generate content (exclude embeddings/etc if desired)
    if "generateContent" in m.supported_actions:
        print(f"{m.name:<40} | {supports_thinking}")
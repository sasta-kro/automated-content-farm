from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get('GEMINI_API_KEY')
client = genai.Client(api_key=api_key)

def test_gemini():
    print("Testing Gemini API...")

    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents="Explain how AI works in one sentence. This is a test to see if the API key works.",
    )

    if response: print("\nSuccess! Response:")
    print("-" * 30)
    print(response.text)
    print("-" * 30)


test_gemini()
from google import genai
import os

# 1. Set your API Key (Replace with your actual key for testing)
# In the future, use os.environ["GEMINI_API_KEY"] for safety
client = genai.Client(api_key="test")

prompt = "Generate a 1-sentence history fact about Ancient Rome in the tone of Patrick from Spongebob."

response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=prompt
)

print(response.text)
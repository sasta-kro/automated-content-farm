from google import genai
from dotenv import load_dotenv
import os


# getting the api key
load_dotenv() # Loads variables from .env

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("Key not found")

# starting the program
client = genai.Client(api_key=api_key)

prompt = "Generate a 1-sentence fun fact about biology in the tone of Patrick from Spongebob."

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt
)

print(response.text)
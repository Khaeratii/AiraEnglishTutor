import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# Daftar model yang tersedia
print("Daftar model yang tersedia:")
for model in client.models.list():
    print(f"- {model.name}")
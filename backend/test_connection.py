# backend/test_connection.py
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv('ONT_TOKEN_API_KEY')
print(f"API Key: {api_key[:20]}..." if api_key else "❌ API Key not found!")

client = OpenAI(
    base_url="https://api.ontoken.id/v1",
    api_key=api_key,
)

# Test model gratis
models_to_test = [
    'gemini-3.8-flash-free',
    'hy3-free',
    'glm-5.3-free'
]

for model in models_to_test:
    try:
        print(f"\n🔄 Testing model: {model}")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say 'Hello' in one word."}],
            max_tokens=10,
        )
        print(f"✅ {model} works: {response.choices[0].message.content}")
    except Exception as e:
        print(f"❌ {model} failed: {e}")
# backend/check_models.py
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

API_KEY = os.getenv('GEMINI_API_KEY')
client = genai.Client(api_key=API_KEY)

print("🔍 Checking available Gemini models...\n")

try:
    models = client.models.list()
    
    print("✅ Models available for your API key:")
    print("=" * 60)
    
    for model in models:
        # Filter models that support generateContent
        if hasattr(model, 'supported_generation_methods'):
            if 'generateContent' in model.supported_generation_methods:
                print(f"  📌 {model.name}")
        else:
            print(f"  📌 {model.name}")
    
    print("=" * 60)
    print("\n💡 Recommended models for chat:")
    print("  - gemini-2.5-flash (stable, fast)")
    print("  - gemini-2.5-flash-lite (fastest, cheapest)")
    print("  - gemini-2.5-pro (most capable)")
    
except Exception as e:
    print(f"❌ Error: {e}")
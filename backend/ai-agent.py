import os
import re
import time
import pandas as pd
from datetime import datetime
import speech_recognition as sr
from dotenv import load_dotenv
from google import genai
from google.genai import types
from gtts import gTTS
import pygame
import tempfile

# ============================================
# IMPOR KONFIGURASI DARI config.py
# ============================================
from .config import (
    MODEL_NAME,
    LANGUAGE,
    LEVEL,
    SAVE_HISTORY,
    HISTORY_FILE,
    SYSTEM_INSTRUCTIONS,
    MAX_REQUESTS_PER_SESSION
)

# ============================================
# SETUP API
# ============================================
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# ============================================
# VARIABEL GLOBAL
# ============================================
conversation_history = []
chat_count = 0

# ============================================
# FUNGSI TEXT CLEANING
# ============================================
def clean_text_for_tts(text):
    """Membersihkan teks dari format markdown dan karakter khusus."""
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'~~(.*?)~~', r'\1', text)
    text = re.sub(r'#{1,6}\s*', '', text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text

# ============================================
# FUNGSI ANALISIS GRAMMAR MENDALAM
# ============================================
def show_final_analysis(history):
    """Menampilkan analisis mendalam setelah percakapan selesai."""
    if not history:
        print("\n📝 No conversation to analyze.")
        return
    
    speak("Now I'm analyzing your English. This will take just a moment...")
    print("\n" + "="*60)
    print("🔍 GENERATING ANALYSIS...")
    print("="*60)
    
    # Gabungkan semua user input
    user_texts = [entry['user'] for entry in history]
    full_text = " ".join(user_texts)
    
    # Buat prompt analisis
    analysis_prompt = f"""You are Aira, and now it's time for the final grammar analysis.

The user has just finished a conversation. Here is everything they said:

{full_text}

Please provide a comprehensive English analysis following this exact format:

🌟 Aira's English Feedback

### 1. Overall Impression
[Give a short, encouraging assessment of the user's English. Mention communication ability, fluency, confidence, general level, and most noticeable strengths.]

### 2. Grammar Patterns to Improve
[Identify the user's most important recurring grammar patterns. Use a table with columns: Pattern | What You Did | Better Version | Why]

### 3. Sentence Structure
[Show 3-5 examples from the conversation. Format: You said: "..." More natural: "..." Why: ...]

### 4. Natural American English
[Show expressions that could sound more natural. Format: Instead of: "..." Try: "..." Why: ...]

### 5. Vocabulary
[Identify useful vocabulary improvements. Include words the user overused, better alternatives, and useful phrases.]

### 6. Your Strengths 💪
[Highlight 3-5 things the user did well.]

### 7. Your Top 3 Priorities
[Give exactly three things the user should focus on next.]

### 8. Aira's Challenge 🎯
[Give a short practice challenge based on their specific mistakes.]

Remember: Be honest but encouraging. Focus on recurring patterns, not every tiny mistake. Help the user sound natural, clear, and grammatically correct in American English."""

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=analysis_prompt
        )
        analysis = response.text
        
        # Tampilkan di console
        print("\n" + analysis)
        
        # Aira membacakan ringkasan
        speak("Analysis complete! Check the console for detailed feedback.")
        
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            print(f"\n⚠️ Quota exceeded for analysis. Please try again later.")
            speak("Sorry, I've reached my limit for today. Check the console for what we discussed!")
        else:
            print(f"⚠️ Error generating analysis: {e}")
            speak("Sorry, I couldn't analyze your English right now.")

# ============================================
# FUNGSI HISTORI
# ============================================
def init_history():
    """Inisialisasi file history jika belum ada."""
    if SAVE_HISTORY and not os.path.exists(HISTORY_FILE):
        pd.DataFrame(columns=['timestamp', 'level', 'user', 'ai']).to_csv(HISTORY_FILE, index=False)

def save_conversation(user_msg, ai_msg):
    """Simpan percakapan ke CSV dan memory."""
    global conversation_history
    conversation_history.append({'user': user_msg, 'ai': ai_msg})
    
    if SAVE_HISTORY:
        new_data = pd.DataFrame({
            'timestamp': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            'level': [LEVEL],
            'user': [user_msg],
            'ai': [ai_msg]
        })
        new_data.to_csv(HISTORY_FILE, mode='a', header=False, index=False)

def show_progress():
    """Menampilkan statistik perkembangan."""
    if not os.path.exists(HISTORY_FILE):
        print("\n📊 No practice data yet.")
        return
    
    df = pd.read_csv(HISTORY_FILE)
    total_chats = len(df)
    
    print("\n" + "="*50)
    print("📊 PROGRESS STATISTICS")
    print("="*50)
    print(f"📝 Total conversations: {total_chats}")
    print(f"📈 Current level: {LEVEL}")
    
    if total_chats > 0:
        avg_user_len = df['user'].str.len().mean()
        avg_ai_len = df['ai'].str.len().mean()
        print(f"📏 Average user input: {avg_user_len:.0f} characters")
        print(f"📏 Average AI response: {avg_ai_len:.0f} characters")
    print("="*50)

# ============================================
# FUNGSI TTS (TEXT-TO-SPEECH)
# ============================================
def speak(text):
    """Mengubah teks menjadi suara dengan pembersihan format."""
    clean_text = clean_text_for_tts(text)
    print(f"\n🤖 Aira: {clean_text}")
    
    try:
        tts = gTTS(text=clean_text, lang='en', slow=False)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
            tts.save(fp.name)
            temp_file = fp.name
        
        pygame.mixer.init()
        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()
        
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        
        try:
            os.unlink(temp_file)
        except:
            pass
            
    except Exception as e:
        print(f"⚠️ Error TTS: {e}")

# ============================================
# FUNGSI STT (SPEECH-TO-TEXT)
# ============================================
def listen():
    """Mendengarkan suara dari mikrofon dan mengubahnya menjadi teks."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("\n🎤 Say something...")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            text = recognizer.recognize_google(audio, language='en-US')
            print(f"👤 You: {text}")
            return text
        except sr.WaitTimeoutError:
            print("⏰ No sound detected. Try again...")
            return ""
        except sr.UnknownValueError:
            print("🔇 Sorry, I couldn't hear clearly.")
            return ""
        except sr.RequestError:
            print("🌐 Sorry, speech recognition service is having issues.")
            return ""

# ============================================
# FUNGSI UTAMA
# ============================================
def main():
    global chat_count, conversation_history
    
    # Inisialisasi
    conversation_history = []
    init_history()
    
    # Tampilkan progress
    show_progress()
    
    # Sapa user
    speak("Hello! I'm Aira, your English conversation partner. Let's start speaking!")
    
    # Buat chat dengan system instruction
    system_instruction = SYSTEM_INSTRUCTIONS.get(LEVEL, SYSTEM_INSTRUCTIONS["beginner"])
    
    chat = client.chats.create(
        model=MODEL_NAME,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction
        )
    )
    
    chat_count = 0
    conversation_active = True
    
    while conversation_active:
        user_input = listen()
        
        # PERINTAH UNTUK ANALISIS MENDALAM
        if user_input.lower() in ["stop", "stop the conversation", "finish", "end", "analysis", "done"]:
            conversation_active = False
            break
            
        # PERINTAH KELUAR LANGSUNG (tanpa analisis)
        if user_input.lower() in ["exit", "quit", "bye", "goodbye"]:
            speak("Goodbye! Keep practicing your English! 👋")
            print("\n👋 Session ended. Keep practicing your English!")
            return
            
        if user_input:
            try:
                # Kirim ke AI
                response = chat.send_message(user_input)
                ai_response = response.text
                
                # Simpan ke history
                save_conversation(user_input, ai_response)
                chat_count += 1
                
                # Baca respons AI
                speak(ai_response)
                
                # Cek limit request
                if chat_count >= MAX_REQUESTS_PER_SESSION:
                    speak("We've had a great session! Let's continue tomorrow to save your quota. 😊")
                    conversation_active = False
                    break
                
            except Exception as e:
                error_msg = str(e)
                
                # Handling quota exceeded
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    print(f"⚠️ Quota exceeded: {e}")
                    speak("Sorry, I've reached my daily limit. Let's continue tomorrow! 😊")
                    conversation_active = False
                    break
                else:
                    print(f"⚠️ Error: {e}")
                    speak("Sorry, something went wrong. Please try again.")
    
    # ============================================
    # TAMPILKAN ANALISIS AKHIR (jika ada percakapan)
    # ============================================
    if conversation_history:
        show_final_analysis(conversation_history)
    else:
        speak("We didn't have a conversation to analyze. Try speaking more next time!")
    
    print("\n" + "="*60)
    print("👋 Session ended. Keep practicing your English!")
    print("="*60)

# ============================================
# JALANKAN PROGRAM
# ============================================
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Program stopped. Keep practicing your English!")
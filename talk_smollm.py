#!/usr/bin/env python3
"""Voice+Text Chatbot with Whisper & Ollama(smollm2) + TTS with Enter Key Interrupt"""
import sys
import threading
import time
import select
import sounddevice as sd
import scipy.io.wavfile as wav
import numpy as np
import whisper
import ollama  # pip install ollama
import pyttsx3  # pip install pyttsx3

# Configuration
SAMPLE_RATE = 16000
CHANNELS = 1
OUTPUT_FILE = "recorded_audio.wav"
recording = []

# Global variables for interrupt control
stop_speaking = False
tts_engine = None

def audio_callback(indata, frames, time_info, status):
    recording.append(indata.copy())

def record_audio():
    global recording
    recording = []
    print("🎙️  Recording... (Press Enter to stop)")
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=audio_callback):
        input()
    audio_data = np.concatenate(recording, axis=0)
    wav.write(OUTPUT_FILE, SAMPLE_RATE, audio_data)
    print(f"✅ Audio saved: {OUTPUT_FILE}")

def transcribe_audio():
    print("📝 Transcribing audio...")
    model = whisper.load_model("base")
    result = model.transcribe(OUTPUT_FILE, fp16=False)
    text = result["text"].strip()
    print(f"💬 You (voice): {text}")
    return text

def init_tts_engine():
    """Initialize TTS engine once"""
    global tts_engine
    if tts_engine is None:
        tts_engine = pyttsx3.init()
        tts_engine.setProperty('rate', 150)
        tts_engine.setProperty('volume', 0.9)

def input_listener():
    """Listen for Enter key press to interrupt speech"""
    global stop_speaking
    try:
        input()  # Wait for Enter key
        stop_speaking = True
        print("\n⏹️  Speech interrupted!")
    except:
        pass

def speak_with_interrupt(text):
    """Convert text to speech with Enter key interrupt capability"""
    global stop_speaking, tts_engine
    
    init_tts_engine()
    stop_speaking = False
    
    print("💡 Press ENTER to interrupt speech")
    
    # Start input listener in a separate thread
    listener_thread = threading.Thread(target=input_listener, daemon=True)
    listener_thread.start()
    
    # Split text into smaller chunks for more responsive interruption
    words = text.split()
    chunk_size = 10  # Speak 10 words at a time
    
    for i in range(0, len(words), chunk_size):
        if stop_speaking:
            break
        
        chunk = ' '.join(words[i:i+chunk_size])
        tts_engine.say(chunk)
        tts_engine.runAndWait()
        
        # Small delay to check for interruption
        time.sleep(0.1)
    
    if stop_speaking:
        tts_engine.stop()

def chat_with_ollama(message, model="smollm2"):
    # def chat_with_ollama(message, model="phi4-mini"):
    print("🤖 AI: ", end='', flush=True)
    full_response = []
    
    try:
        stream = ollama.chat(
            model=model,
            messages=[{'role': 'user', 'content': message}],
            stream=True,
        )
        
        for chunk in stream:
            content = chunk['message']['content']
            print(content, end='', flush=True)
            full_response.append(content)
        
        print()  # New line after streaming
        
        # Speak the full response with interrupt capability
        response_text = ''.join(full_response)
        if response_text.strip():
            speak_with_interrupt(response_text)
            
    except Exception as e:
        print(f"\n❌ Error with Ollama: {e}")

def main():
    print("🤖 Voice+Text smollm2 Chatbot (Ctrl+C to exit)")
    print("💡 Press ENTER during AI speech to interrupt")
    print("-" * 50)
    
    try:
        while True:
            mode = input("\n[1] Voice input  [2] Text input  [q] Quit > ").strip().lower()
            
            if mode == '1':
                record_audio()
                message = transcribe_audio()
                if message:
                    chat_with_ollama(message)
                    
            elif mode == '2':
                message = input("💬 You: ").strip()
                if message:
                    chat_with_ollama(message)
                    
            elif mode == 'q':
                print("👋 Goodbye!")
                break
                
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    finally:
        # Clean up TTS engine
        global tts_engine
        if tts_engine:
            tts_engine.stop()

if __name__ == "__main__":
    main()

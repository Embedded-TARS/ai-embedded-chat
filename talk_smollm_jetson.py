#!/usr/bin/env python3
"""Voice+Text Chatbot with Whisper & Ollama(smollm2) + TTS"""
import sys
import sounddevice as sd
import scipy.io.wavfile as wav
import numpy as np
import whisper
import ollama  # pip install ollama
import pyttsx3  # pip install pyttsx3
import warnings
import os

# Suppress future warnings from whisper/torch
warnings.filterwarnings("ignore", category=FutureWarning, module="whisper")

# Redirect stderr temporarily to suppress pyttsx3 errors
class SuppressTTSErrors:
    def __enter__(self):
        self.old_stderr = sys.stderr
        sys.stderr = open(os.devnull, 'w')
        return self
    
    def __exit__(self, type, value, traceback):
        sys.stderr.close()
        sys.stderr = self.old_stderr

# Configuration
SAMPLE_RATE = 16000
CHANNELS = 1
OUTPUT_FILE = "recorded_audio.wav"
recording = []

# Global TTS engine
tts_engine = None

def init_tts():
    """Initialize TTS engine once"""
    global tts_engine
    if tts_engine is None:
        try:
            tts_engine = pyttsx3.init()
            tts_engine.setProperty('rate', 150)
            tts_engine.setProperty('volume', 0.9)
            # Optionally, change voice:
            # voices = tts_engine.getProperty('voices')
            # if voices:
            #     tts_engine.setProperty('voice', voices[0].id)
        except Exception as e:
            print(f"TTS initialization error: {e}")
            tts_engine = False  # Mark as failed

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

def speak(text):
    """Convert text to speech using pyttsx3 with proper error handling"""
    if not text.strip():
        return
    
    try:
        init_tts()
        if tts_engine and tts_engine is not False:
            with SuppressTTSErrors():  # Suppress the callback errors
                tts_engine.say(text)
                tts_engine.runAndWait()
    except Exception as e:
        print(f"🔇 TTS Error: {e}")
        # Fallback: try system TTS if available
        try_system_tts(text)

def try_system_tts(text):
    """Fallback TTS using system commands"""
    try:
        import subprocess
        import platform
        
        system = platform.system()
        if system == "Linux":
            subprocess.run(["espeak", text], check=True, capture_output=True, stderr=subprocess.DEVNULL)
        elif system == "Darwin":  # macOS
            subprocess.run(["say", text], check=True)
        elif system == "Windows":
            subprocess.run([
                "powershell", "-Command", 
                f"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{text}')"
            ], check=True)
    except Exception:
        pass  # Silent fallback failure

def chat_with_ollama(message, model="smollm2"):
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
        
        # Speak the full response
        response_text = ''.join(full_response)
        if response_text.strip():
            speak(response_text)
            
    except Exception as e:
        error_msg = f"Error communicating with Ollama: {e}"
        print(error_msg)
        speak("Sorry, I encountered an error while processing your request.")

def cleanup():
    """Clean up resources"""
    global tts_engine
    if tts_engine and tts_engine is not False:
        try:
            tts_engine.stop()
        except:
            pass
        tts_engine = None

def main():
    print("🤖 Voice+Text smollm2 Chatbot (Ctrl+C to exit)")
    print("📋 Make sure Ollama is running and smollm2 model is installed")
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
            else:
                print("❌ Invalid option. Please choose 1, 2, or q")
                
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    finally:
        cleanup()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Voice+Text Chatbot with Whisper & Ollama(smollm2) + TTS, using ai_prompt.txt for the system prompt"""

import sys
import sounddevice as sd
import scipy.io.wavfile as wav
import numpy as np
import whisper
import ollama  # pip install ollama
import pyttsx3  # pip install pyttsx3
import os

# Configuration
SAMPLE_RATE = 16000
CHANNELS = 1
OUTPUT_FILE = "recorded_audio.wav"
recording = []

def load_system_prompt(filename="ai_prompt.txt"):
    """Load the system prompt from a text file."""
    if not os.path.exists(filename):
        print(f"❌ System prompt file '{filename}' not found.")
        sys.exit(1)
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()

SYSTEM_PROMPT = load_system_prompt()

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
    """Convert text to speech using pyttsx3"""
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)
    engine.setProperty('volume', 0.9)
    engine.say(text)
    engine.runAndWait()

def chat_with_ollama(message, model="smollm2"):
    print("🤖 AI: ", end='', flush=True)
    full_response = []
    # Use system prompt from file
    stream = ollama.chat(
        model=model,
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': message}
        ],
        stream=True,
    )
    for chunk in stream:
        content = chunk['message']['content']
        print(content, end='', flush=True)
        full_response.append(content)
    print()  # New line after streaming
    speak(''.join(full_response))

def main():
    print("🤖 Voice+Text smollm2 Chatbot (Ctrl+C to exit)")
    print("-" * 40)
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

if __name__ == "__main__":
    main()

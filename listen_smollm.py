#!/usr/bin/env python3
"""Voice+Text Chatbot with Whisper & Ollama(smollm2)"""

import sys
import sounddevice as sd
import scipy.io.wavfile as wav
import numpy as np
import whisper
import ollama  # pip install ollama

# Configuration
SAMPLE_RATE = 16000
CHANNELS = 1
OUTPUT_FILE = "recorded_audio.wav"
recording = []

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

def chat_with_ollama(message, model="smollm2"):
    print("🤖 AI: ", end='', flush=True)
    stream = ollama.chat(
        model=model,
        messages=[{'role': 'user', 'content': message}],
        stream=True,
    )
    for chunk in stream:
        print(chunk['message']['content'], end='', flush=True)
    print()

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

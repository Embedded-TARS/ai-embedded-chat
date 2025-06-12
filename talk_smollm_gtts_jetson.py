#!/usr/bin/env python3
"""Voice+Text Chatbot with Whisper, Ollama & Google TTS"""

import os, sys, warnings, tempfile, time
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
import whisper, ollama
from gtts import gTTS

# Suppress warnings and pygame messages
warnings.filterwarnings("ignore")
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
old_stdout = sys.stdout
sys.stdout = open(os.devnull, 'w')
import pygame
sys.stdout.close()
sys.stdout = old_stdout
pygame.mixer.init()

class VoiceChatbot:
    def __init__(self):
        self.sample_rate = 16000
        self.channels = 1
        self.audio_file = "recorded_audio.wav"
        self.recording = []
        
    def record_audio(self):
        """Record audio until Enter is pressed"""
        self.recording = []
        print("🎙️  Recording... (Press Enter to stop)")
        
        def callback(indata, frames, time_info, status):
            self.recording.append(indata.copy())
            
        with sd.InputStream(samplerate=self.sample_rate, channels=self.channels, callback=callback):
            input()
            
        audio_data = np.concatenate(self.recording, axis=0)
        wav.write(self.audio_file, self.sample_rate, audio_data)
        print(f"✅ Audio saved")
        
    def transcribe_audio(self):
        """Transcribe recorded audio to text"""
        print("📝 Transcribing...")
        model = whisper.load_model("base")
        result = model.transcribe(self.audio_file, fp16=False)
        text = result["text"].strip()
        print(f"💬 You: {text}")
        return text
        
    def speak(self, text):
        """Convert text to speech using Google TTS"""
        if not text.strip():
            return
            
        try:
            tts = gTTS(text=text, lang='en')
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
                temp_file = tmp.name
                
            tts.save(temp_file)
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
                
            os.unlink(temp_file)
        except Exception as e:
            print(f"🔇 TTS Error: {e}")
            
    def chat_with_ai(self, message):
        """Send message to AI and get response"""
        print("🤖 AI: ", end='', flush=True)
        response_parts = []
        
        try:
            stream = ollama.chat(
                model="smollm2",
                messages=[{'role': 'user', 'content': message}],
                stream=True
            )
            
            for chunk in stream:
                content = chunk['message']['content']
                print(content, end='', flush=True)
                response_parts.append(content)
                
            print()  # New line
            
            response = ''.join(response_parts)
            if response.strip():
                self.speak(response)
                
        except Exception as e:
            error_msg = f"Error: {e}"
            print(error_msg)
            self.speak("Sorry, I encountered an error.")
            
    def run(self):
        """Main chatbot loop"""
        print("🤖 Voice+Text Chatbot (Ctrl+C to exit)")
        print("📋 Ollama + smollm2 required | 🌐 Internet for TTS")
        print("-" * 50)
        
        try:
            while True:
                choice = input("\n[1] Voice [2] Text [q] Quit > ").strip().lower()
                
                if choice == '1':
                    self.record_audio()
                    message = self.transcribe_audio()
                    if message:
                        self.chat_with_ai(message)
                        
                elif choice == '2':
                    message = input("💬 You: ").strip()
                    if message:
                        self.chat_with_ai(message)
                        
                elif choice == 'q':
                    break
                else:
                    print("❌ Invalid option")
                    
        except KeyboardInterrupt:
            pass
        finally:
            pygame.mixer.quit()
            print("\n👋 Goodbye!")

if __name__ == "__main__":
    VoiceChatbot().run()

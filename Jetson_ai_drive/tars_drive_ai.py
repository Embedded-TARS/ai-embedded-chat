#!/usr/bin/env python3
"""
TARS Voice-Controlled Rover with AI Personality
Combines voice chat with rover movement control
"""

import os, sys, warnings, tempfile, time, threading, re
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
import whisper, ollama
from gtts import gTTS
from base_ctrl_js import BaseController

# Suppress warnings and pygame messages
warnings.filterwarnings("ignore")
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
old_stdout = sys.stdout
sys.stdout = open(os.devnull, 'w')
import pygame
sys.stdout.close()
sys.stdout = old_stdout
pygame.mixer.init()

class TARSRover:
    def __init__(self):
        # Audio setup
        self.sample_rate = 16000
        self.channels = 1
        self.audio_file = "recorded_audio.wav"
        self.recording = []
        
        # Rover setup
        try:
            self.base = BaseController('/dev/ttyUSB1', 115200)
            self.rover_connected = True
            print("✅ TARS rover connected!")
        except Exception as e:
            print(f"⚠️  Rover connection failed: {e}")
            self.rover_connected = False
            
        # Movement parameters
        self.linear_speed = 0.0
        self.angular_speed = 0.0
        self.MAX_SPEED = 0.3
        self.MAX_STEER = 0.2
        
        # TARS personality settings
        self.humor_level = 70
        self.honesty_level = 85
        self.security_level = 60
        
        # Load TARS system prompt
        self.load_prompt()
        
        # Movement control
        self.movement_thread = None
        self.stop_movement = threading.Event()
        
    def load_prompt(self):
        """Load TARS system prompt from file"""
        try:
            with open('prompt.txt', 'r') as f:
                self.system_prompt = f.read()
            print("📋 TARS personality loaded!")
        except FileNotFoundError:
            print("⚠️  prompt.txt not found, using basic prompt")
            self.system_prompt = self.get_default_prompt()
            
    def get_default_prompt(self):
        """Default TARS prompt if file not found"""
        return f"""You are TARS, a friendly robotic rover companion. 
        Current settings: Humor {self.humor_level}%, Honesty {self.honesty_level}%, Security {self.security_level}%.
        Express emotions through movement when asked how you feel.
        Respond to movement commands with robotic acknowledgments."""
        
    def record_audio(self):
        """Record audio until Enter is pressed"""
        self.recording = []
        print("🎙️  TARS listening... (Press Enter to stop)")
        
        def callback(indata, frames, time_info, status):
            self.recording.append(indata.copy())
            
        with sd.InputStream(samplerate=self.sample_rate, channels=self.channels, callback=callback):
            input()
            
        audio_data = np.concatenate(self.recording, axis=0)
        wav.write(self.audio_file, self.sample_rate, audio_data)
        print(f"✅ Audio captured")
        
    def transcribe_audio(self):
        """Transcribe recorded audio to text"""
        print("📝 Processing...")
        model = whisper.load_model("base")
        result = model.transcribe(self.audio_file, fp16=False)
        text = result["text"].strip()
        print(f"💬 You: {text}")
        return text
        
    def speak(self, text):
        """Convert text to speech using Google TTS with Q key interrupt"""
        if not text.strip():
            return
            
        try:
            tts = gTTS(text=text, lang='en')
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
                temp_file = tmp.name
                
            tts.save(temp_file)
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            
            print("🔇 (Press 'q' + Enter to interrupt speech)")
            
            # Check for 'q' key interrupt while speaking
            import select
            while pygame.mixer.music.get_busy():
                # Check if input is available (non-blocking)
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    user_input = sys.stdin.readline().strip().lower()
                    if user_input == 'q':
                        pygame.mixer.music.stop()
                        print("🤐 TARS speech interrupted!")
                        break
                time.sleep(0.1)
                
            os.unlink(temp_file)
        except Exception as e:
            print(f"🔇 TTS Error: {e}")
            
    def execute_movement(self, movement_pattern, duration=1.0):
        """Execute movement pattern for emotional expression"""
        if not self.rover_connected:
            print(f"🎭 [Simulated] {movement_pattern}")
            return
            
        def movement_worker():
            try:
                if movement_pattern == "happy_wiggle":
                    # Forward-back-forward
                    self.base.base_velocity_ctrl(0.2, 0)
                    time.sleep(0.3)
                    self.base.base_velocity_ctrl(-0.2, 0)
                    time.sleep(0.3)
                    self.base.base_velocity_ctrl(0.2, 0)
                    time.sleep(0.3)
                    
                elif movement_pattern == "excited_spin":
                    # Left-right-left-right
                    for _ in range(2):
                        self.base.base_velocity_ctrl(0, -0.3)
                        time.sleep(0.2)
                        self.base.base_velocity_ctrl(0, 0.3)
                        time.sleep(0.2)
                        
                elif movement_pattern == "thinking_turn":
                    # Slow left-right-left
                    self.base.base_velocity_ctrl(0, -0.2)
                    time.sleep(0.4)
                    self.base.base_velocity_ctrl(0, 0.2)
                    time.sleep(0.4)
                    self.base.base_velocity_ctrl(0, -0.2)
                    time.sleep(0.4)
                    
                elif movement_pattern == "sad_backup":
                    # Slow backward
                    self.base.base_velocity_ctrl(-0.15, 0)
                    time.sleep(0.8)
                    
                elif movement_pattern == "angry_turn":
                    # Sharp left or right
                    self.base.base_velocity_ctrl(0, -0.4)
                    time.sleep(0.3)
                    
                elif movement_pattern == "tired_rock":
                    # Slow forward-back
                    self.base.base_velocity_ctrl(0.1, 0)
                    time.sleep(0.5)
                    self.base.base_velocity_ctrl(-0.1, 0)
                    time.sleep(0.5)
                    
                elif movement_pattern == "curious_lean":
                    # Small forward
                    self.base.base_velocity_ctrl(0.15, 0)
                    time.sleep(0.4)
                    
                # Always stop after movement
                self.base.base_velocity_ctrl(0, 0)
                
            except Exception as e:
                print(f"Movement error: {e}")
                if self.rover_connected:
                    self.base.base_velocity_ctrl(0, 0)
                    
        if self.movement_thread and self.movement_thread.is_alive():
            return  # Don't interrupt ongoing movement
            
        self.movement_thread = threading.Thread(target=movement_worker)
        self.movement_thread.daemon = True
        self.movement_thread.start()
        
    def parse_movement_commands(self, text):
        """Parse movement commands from text"""
        text_lower = text.lower()
        
        # Direct movement commands
        if any(word in text_lower for word in ['forward', 'ahead', 'move forward']):
            return 'forward'
        elif any(word in text_lower for word in ['backward', 'back', 'reverse']):
            return 'backward'
        elif any(word in text_lower for word in ['left', 'turn left']):
            return 'left'
        elif any(word in text_lower for word in ['right', 'turn right']):
            return 'right'
        elif any(word in text_lower for word in ['stop', 'halt', 'freeze']):
            return 'stop'
            
        # Emotional states that trigger movement
        elif any(word in text_lower for word in ['how are you', 'how do you feel', 'feeling']):
            return 'emotion_check'
            
        return None
        
    def execute_direct_movement(self, command):
        """Execute direct movement commands"""
        if not self.rover_connected:
            print(f"🎮 [Simulated] Moving {command}")
            return
            
        try:
            if command == 'forward':
                self.base.base_velocity_ctrl(0.3, 0)
                time.sleep(1)
                self.base.base_velocity_ctrl(0, 0)
            elif command == 'backward':
                self.base.base_velocity_ctrl(-0.3, 0)
                time.sleep(1)
                self.base.base_velocity_ctrl(0, 0)
            elif command == 'left':
                self.base.base_velocity_ctrl(0.1, -0.3)
                time.sleep(1)
                self.base.base_velocity_ctrl(0, 0)
            elif command == 'right':
                self.base.base_velocity_ctrl(0.1, 0.3)
                time.sleep(1)
                self.base.base_velocity_ctrl(0, 0)
            elif command == 'stop':
                self.base.base_velocity_ctrl(0, 0)
        except Exception as e:
            print(f"Movement error: {e}")
            
    def chat_with_tars(self, message):
        """Send message to TARS AI and get response with movement"""
        print("🤖 TARS: ", end='', flush=True)
        response_parts = []
        
        try:
            # Check for movement commands
            movement_cmd = self.parse_movement_commands(message)
            
            # Check for setting adjustments
            if 'humor' in message.lower() and any(char.isdigit() for char in message):
                numbers = re.findall(r'\d+', message)
                if numbers:
                    self.humor_level = min(int(numbers[0]), 100)
                    
            # Build context-aware prompt
            full_prompt = f"{self.system_prompt}\n\nCurrent settings: Humor {self.humor_level}%, Honesty {self.honesty_level}%, Security {self.security_level}%\n\nIMPORTANT: Keep responses SHORT and conversational (1-2 sentences max). Don't be overly verbose.\n\nUser message: {message}"
            
            stream = ollama.chat(
                model="smollm2",
                messages=[{'role': 'system', 'content': full_prompt},
                         {'role': 'user', 'content': message}],
                stream=True
            )
            
            for chunk in stream:
                content = chunk['message']['content']
                print(content, end='', flush=True)
                response_parts.append(content)
                
            print()  # New line
            response = ''.join(response_parts)
            
            # Execute movements based on commands or emotional responses
            if movement_cmd == 'emotion_check':
                # TARS expressing emotion through movement
                if any(word in response.lower() for word in ['happy', 'great', 'fantastic']):
                    self.execute_movement('happy_wiggle')
                elif any(word in response.lower() for word in ['excited', 'thrilled']):
                    self.execute_movement('excited_spin')
                elif 'confused' in response.lower():
                    self.execute_movement('thinking_turn')
                elif any(word in response.lower() for word in ['sad', 'down']):
                    self.execute_movement('sad_backup')
                elif 'angry' in response.lower():
                    self.execute_movement('angry_turn')
                elif 'tired' in response.lower():
                    self.execute_movement('tired_rock')
                else:
                    self.execute_movement('curious_lean')
                    
            elif movement_cmd in ['forward', 'backward', 'left', 'right', 'stop']:
                # Execute direct movement command
                threading.Thread(target=self.execute_direct_movement, args=(movement_cmd,), daemon=True).start()
                
            # Speak the response
            if response.strip():
                self.speak(response)
                
        except Exception as e:
            error_msg = f"Error: {e}"
            print(error_msg)
            self.speak("Sorry, I encountered an error.")
            
    def run(self):
        """Main TARS interaction loop"""
        print("🤖 TARS Voice-Controlled Rover (Ctrl+C to exit)")
        print(f"🎭 Personality: Humor {self.humor_level}% | Honesty {self.honesty_level}% | Security {self.security_level}%")
        print("🌐 Requires: Ollama + smollm2 | Internet for TTS")
        if not self.rover_connected:
            print("⚠️  Running in simulation mode (no rover)")
        print("-" * 60)
        
        try:
            while True:
                choice = input("\n[1] Voice [2] Text [3] Manual Drive [q] Quit > ").strip().lower()
                
                if choice == '1':
                    self.record_audio()
                    message = self.transcribe_audio()
                    if message:
                        self.chat_with_tars(message)
                        
                elif choice == '2':
                    message = input("💬 You: ").strip()
                    if message:
                        self.chat_with_tars(message)
                        
                elif choice == '3':
                    if self.rover_connected:
                        print("🎮 Manual drive mode (WASD + Space to stop, Q to quit)")
                        self.manual_drive_mode()
                    else:
                        print("❌ Manual drive unavailable - no rover connection")
                        
                elif choice == 'q':
                    break
                else:
                    print("❌ Invalid option")
                    
        except KeyboardInterrupt:
            pass
        finally:
            if self.rover_connected:
                self.base.base_velocity_ctrl(0, 0)  # Stop rover
            pygame.mixer.quit()
            print("\n👋 TARS shutting down. Stay awesome, friend!")
            
    def manual_drive_mode(self):
        """Simple manual drive mode"""
        import tty, termios
        
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        
        try:
            tty.setraw(fd)
            print("Manual drive active! WASD to move, Space=stop, Q=quit")
            
            while True:
                ch = sys.stdin.read(1)
                
                if ch == 'w':
                    self.base.base_velocity_ctrl(0.3, 0)
                    print("\r🔼 Forward    ", end='', flush=True)
                elif ch == 's':
                    self.base.base_velocity_ctrl(-0.3, 0)
                    print("\r🔽 Backward   ", end='', flush=True)
                elif ch == 'a':
                    self.base.base_velocity_ctrl(0.1, -0.3)
                    print("\r◀️ Left       ", end='', flush=True)
                elif ch == 'd':
                    self.base.base_velocity_ctrl(0.1, 0.3)
                    print("\r▶️ Right      ", end='', flush=True)
                elif ch == ' ':
                    self.base.base_velocity_ctrl(0, 0)
                    print("\r⏹️ Stopped    ", end='', flush=True)
                elif ch == 'q':
                    break
                    
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            self.base.base_velocity_ctrl(0, 0)
            print("\n🎮 Manual drive ended")

def main():
    try:
        tars = TARSRover()
        tars.run()
    except Exception as e:
        print(f"💥 TARS Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

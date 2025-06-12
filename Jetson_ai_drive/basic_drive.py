#!/usr/bin/env python3
"""
Simple terminal controller for TARS rover
Controls: WASD for movement, Space for stop, Q to quit
"""

import sys
import time
import threading
import tty
import termios
from base_ctrl_js import BaseController

class SimpleRoverController:
    def __init__(self):
        # Initialize robot base
        self.base = BaseController('/dev/ttyUSB1', 115200)
        
        # Movement parameters
        self.linear_speed = 0.0
        self.angular_speed = 0.0
        self.MAX_SPEED = 0.3
        self.MAX_STEER = 0.2
        
        # Control flags
        self.running = True
        self._input_char = None
        self._stop_event = threading.Event()
        
    def _read_input(self):
        """Read keyboard input in raw mode"""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while not self._stop_event.is_set():
                ch = sys.stdin.read(1)
                self._input_char = ch
                time.sleep(0.01)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    
    def handle_input(self):
        """Process keyboard input"""
        if self._input_char:
            ch = self._input_char
            self._input_char = None
            
            if ch == 'w':  # Forward
                self.linear_speed = self.MAX_SPEED
                self.angular_speed = 0.0
            elif ch == 's':  # Backward
                self.linear_speed = -self.MAX_SPEED
                self.angular_speed = 0.0
            elif ch == 'a':  # Turn left - needs power to turn
                self.angular_speed = -self.MAX_STEER
                self.linear_speed = 0.5  # Add forward speed for turning power
            elif ch == 'd':  # Turn right - needs power to turn
                self.angular_speed = self.MAX_STEER
                self.linear_speed = 0.5  # Add forward speed for turning power
            elif ch == ' ':  # Stop
                self.linear_speed = 0.0
                self.angular_speed = 0.0
            elif ch == 'q' or ch == '\x1b':  # Quit (q or ESC)
                self.running = False
                
            # Combined movements
            elif ch == 'e':  # Forward + Right
                self.linear_speed = 0.5  # Boost speed for turning
                self.angular_speed = self.MAX_STEER
            elif ch == 'r':  # Forward + Left
                self.linear_speed = 0.5  # Boost speed for turning
                self.angular_speed = -self.MAX_STEER
            elif ch == 'z':  # Backward + Left
                self.linear_speed = -0.5  # Boost speed for turning
                self.angular_speed = -self.MAX_STEER
            elif ch == 'x':  # Backward + Right
                self.linear_speed = -0.5  # Boost speed for turning
                self.angular_speed = self.MAX_STEER
    
    def update_robot(self):
        """Send velocity commands to robot"""
        self.base.base_velocity_ctrl(self.linear_speed, self.angular_speed)
    
    def print_status(self):
        """Print current status"""
        status = f"\rSpeed: {self.linear_speed:+.2f} m/s | Steer: {self.angular_speed:+.2f} rad/s | "
        
        if self.linear_speed > 0:
            status += "Moving: Forward"
        elif self.linear_speed < 0:
            status += "Moving: Backward"
        else:
            status += "Moving: Stopped"
            
        if self.angular_speed > 0:
            status += " + Right turn"
        elif self.angular_speed < 0:
            status += " + Left turn"
            
        print(status + "  ", end='', flush=True)
    
    def run(self):
        """Main control loop"""
        print("=== Simple Rover Controller ===")
        print("Controls:")
        print("  W/S: Forward/Backward")
        print("  A/D: Turn Left/Right")
        print("  E/R: Forward+Right/Left")
        print("  Z/X: Backward+Left/Right")
        print("  Space: Stop")
        print("  Q/ESC: Quit")
        print("==============================\n")
        
        # Start input thread
        input_thread = threading.Thread(target=self._read_input)
        input_thread.daemon = True
        input_thread.start()
        
        try:
            last_update = time.time()
            
            while self.running:
                # Handle keyboard input
                self.handle_input()
                
                # Update robot at fixed intervals (20Hz)
                current_time = time.time()
                if current_time - last_update >= 0.05:
                    self.update_robot()
                    self.print_status()
                    last_update = current_time
                
                time.sleep(0.01)
                
        except KeyboardInterrupt:
            print("\n\nCtrl+C detected. Stopping...")
        finally:
            # Clean shutdown
            self._stop_event.set()
            self.base.base_velocity_ctrl(0, 0)  # Stop robot
            print("\nRobot stopped. Goodbye!")

def main():
    try:
        controller = SimpleRoverController()
        controller.run()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Simple terminal controller for TARS rover with smooth acceleration
Controls: WASD for movement, Space for stop, Q to quit
"""

import sys
import time
import threading
import tty
import termios
import select
from base_ctrl_js import BaseController

class SimpleRoverController:
    def __init__(self):
        # Initialize robot base
        self.base = BaseController('/dev/ttyUSB1', 115200)
        
        # Movement parameters
        self.linear_speed = 0.0
        self.angular_speed = 0.0
        
        # Speed limits
        self.MAX_SPEED = 0.5
        self.MIN_TURN_SPEED = 0.5  # Minimum speed when turning (instant)
        self.MAX_STEER = 0.2
        
        # Acceleration parameters
        self.LINEAR_ACCEL = 0.02   # Speed increase per update (20Hz = 0.4 m/s per second)
        self.ANGULAR_ACCEL = 0.05  # Steer increase per update
        
        # Target speeds (what we want to reach)
        self.target_linear = 0.0
        self.target_angular = 0.0
        
        # Control flags
        self.running = True
        self._stop_event = threading.Event()
        
        # Key states with timestamps
        self._key_states = {}
        self._lock = threading.Lock()
        self.KEY_TIMEOUT = 0.15  # Keys expire after 150ms without repeat
        
    def _read_input(self):
        """Read keyboard input continuously"""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while not self._stop_event.is_set():
                # Non-blocking read with timeout
                if select.select([sys.stdin], [], [], 0.01)[0]:
                    ch = sys.stdin.read(1)
                    
                    # Exit keys
                    if ch == 'q' or ch == '\x1b':
                        self.running = False
                        break
                    
                    # Update key timestamp
                    with self._lock:
                        if ch in 'wasd ':
                            self._key_states[ch] = time.time()
                
                time.sleep(0.005)  # Small delay to prevent CPU spinning
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    
    def get_active_keys(self):
        """Get currently active keys based on recent presses"""
        current_time = time.time()
        active_keys = set()
        
        with self._lock:
            # Check which keys were pressed recently
            expired_keys = []
            for key, timestamp in self._key_states.items():
                if current_time - timestamp < self.KEY_TIMEOUT:
                    active_keys.add(key)
                else:
                    expired_keys.append(key)
            
            # Remove expired keys
            for key in expired_keys:
                del self._key_states[key]
        
        return active_keys
    
    def update_targets(self):
        """Update target speeds based on active keys"""
        active_keys = self.get_active_keys()
        
        # Reset targets
        self.target_linear = 0.0
        self.target_angular = 0.0
        
        # Emergency stop overrides everything
        if ' ' in active_keys:
            self.target_linear = 0.0
            self.target_angular = 0.0
            # Immediate stop - set actual speeds to zero
            self.linear_speed = 0.0
            self.angular_speed = 0.0
            return
        
        # Check for forward/backward
        moving_forward = False
        moving_backward = False
        if 'w' in active_keys:
            self.target_linear = self.MAX_SPEED
            moving_forward = True
        elif 's' in active_keys:
            self.target_linear = -self.MAX_SPEED
            moving_backward = True
        
        # Check for turning
        turning = False
        if 'a' in active_keys:
            self.target_angular = -self.MAX_STEER
            turning = True
        elif 'd' in active_keys:
            self.target_angular = self.MAX_STEER
            turning = True
        
        # Apply minimum speed when turning
        if turning:
            if not moving_forward and not moving_backward:
                # Turn in place - need forward speed
                self.target_linear = self.MIN_TURN_SPEED
            elif moving_forward:
                # Moving forward and turning - boost to min speed
                self.target_linear = self.MIN_TURN_SPEED
            elif moving_backward:
                # Moving backward and turning - boost to min speed (negative)
                self.target_linear = -self.MIN_TURN_SPEED
    
    def smooth_speed_update(self):
        """Gradually adjust current speeds towards target speeds"""
        # Check if we're currently turning
        is_turning = abs(self.target_angular) > 0.01
        
        # Special handling for linear speed when turning
        if is_turning:
            # When turning, we need instant minimum speed
            if abs(self.target_linear) >= self.MIN_TURN_SPEED:
                # Instant jump to turn speed
                self.linear_speed = self.target_linear
            elif self.target_linear > 0 and self.linear_speed < self.MIN_TURN_SPEED:
                # Forward turn - instant boost
                self.linear_speed = self.MIN_TURN_SPEED
            elif self.target_linear < 0 and self.linear_speed > -self.MIN_TURN_SPEED:
                # Backward turn - instant boost
                self.linear_speed = -self.MIN_TURN_SPEED
            else:
                # Normal smooth adjustment
                if abs(self.target_linear - self.linear_speed) < self.LINEAR_ACCEL:
                    self.linear_speed = self.target_linear
                elif self.linear_speed < self.target_linear:
                    self.linear_speed += self.LINEAR_ACCEL
                elif self.linear_speed > self.target_linear:
                    self.linear_speed -= self.LINEAR_ACCEL
        else:
            # Not turning - normal smooth acceleration/deceleration
            if abs(self.target_linear - self.linear_speed) < self.LINEAR_ACCEL:
                self.linear_speed = self.target_linear
            elif self.linear_speed < self.target_linear:
                self.linear_speed += self.LINEAR_ACCEL
            elif self.linear_speed > self.target_linear:
                self.linear_speed -= self.LINEAR_ACCEL
        
        # Update angular speed (always smooth)
        if abs(self.target_angular - self.angular_speed) < self.ANGULAR_ACCEL:
            self.angular_speed = self.target_angular
        elif self.angular_speed < self.target_angular:
            self.angular_speed += self.ANGULAR_ACCEL
        elif self.angular_speed > self.target_angular:
            self.angular_speed -= self.ANGULAR_ACCEL
    
    def update_robot(self):
        """Send velocity commands to robot"""
        self.base.base_velocity_ctrl(self.linear_speed, self.angular_speed)
    
    def print_status(self):
        """Print current status"""
        # Get active keys for display
        active_keys = self.get_active_keys()
        keys_str = ''.join(sorted(active_keys)) if active_keys else 'none'
        
        # Show current and target speeds
        status = f"\rKeys: [{keys_str:^4}] | "
        status += f"Speed: {self.linear_speed:+.2f}"
        if abs(self.target_linear - self.linear_speed) > 0.01:
            status += f"→{self.target_linear:+.2f}"
        status += " m/s | "
        
        status += f"Steer: {self.angular_speed:+.2f}"
        if abs(self.target_angular - self.angular_speed) > 0.01:
            status += f"→{self.target_angular:+.2f}"
        status += " rad/s | "
        
        if self.linear_speed > 0.01:
            status += "Forward "
        elif self.linear_speed < -0.01:
            status += "Backward"
        else:
            status += "Stopped "
            
        if self.angular_speed > 0.01:
            status += "+Right "
        elif self.angular_speed < -0.01:
            status += "+Left  "
        else:
            status += "       "
            
        print(status + "  ", end='', flush=True)
    
    def run(self):
        """Main control loop"""
        print("=== Smooth Rover Controller ===")
        print("Controls (hold keys to move):")
        print("  W/S: Forward/Backward")
        print("  A/D: Turn Left/Right")
        print("  W+A/D: Move + Turn")
        print("  Space: Emergency Stop")
        print("  Q/ESC: Quit")
        print(f"\nMin turn speed: {self.MIN_TURN_SPEED} m/s")
        print("==============================\n")
        
        # Start input thread
        input_thread = threading.Thread(target=self._read_input)
        input_thread.daemon = True
        input_thread.start()
        
        try:
            last_update = time.time()
            
            while self.running:
                # Update target speeds based on keys
                self.update_targets()
                
                # Update robot at fixed intervals (20Hz)
                current_time = time.time()
                if current_time - last_update >= 0.05:  # 50ms = 20Hz
                    # Smoothly adjust speeds
                    self.smooth_speed_update()
                    
                    # Send commands to robot
                    self.update_robot()
                    
                    # Update display
                    self.print_status()
                    
                    last_update = current_time
                
                time.sleep(0.005)  # 5ms loop delay
                
        except KeyboardInterrupt:
            print("\n\nCtrl+C detected. Stopping...")
        finally:
            # Clean shutdown
            self._stop_event.set()
            
            # Smooth stop
            print("\nStopping smoothly...")
            while abs(self.linear_speed) > 0.01 or abs(self.angular_speed) > 0.01:
                self.target_linear = 0.0
                self.target_angular = 0.0
                self.smooth_speed_update()
                self.update_robot()
                time.sleep(0.05)
            
            self.base.base_velocity_ctrl(0, 0)  # Final stop
            
            if input_thread.is_alive():
                input_thread.join(timeout=1.0)
            print("Robot stopped. Goodbye!")

def main():
    try:
        controller = SimpleRoverController()
        controller.run()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

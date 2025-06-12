#!/usr/bin/env python3
"""Robust Robotic Driving Assistant with better error handling and command detection"""
import requests
import json
import sys
import re

# More explicit system prompt with better structure
SYSTEM_PROMPT = """You are a robotic driving assistant. Follow these rules EXACTLY:

RULE 1: First, determine the command type:
- NAVIGATION: Commands about going to destinations (home, office, airport, school)
- MANUAL: Direct movement commands (stop, forward, backward, left, right)
- FARE_REPORT: JSON input with duration/fare/distance
- CHAT: Any other input (greetings, questions, unclear commands)

RULE 2: Response formats by type:

For NAVIGATION commands:
Line 1: Friendly response about the navigation
Line 2: JSON: {"task_type": "navigate", "action": "navigate_to", "parameters": {"destination": "[DESTINATION]", "speed": "[SPEED]"}}

For MANUAL commands:
Line 1: Friendly response about the action
Line 2: JSON: {"task_type": "manual_command", "action": "[ACTION]", "parameters": {"destination": null, "speed": null}}

For FARE_REPORT:
Line 1: Single taxi driver response about the fare (no JSON)

For CHAT (non-command input):
Line 1: Friendly response asking for a navigation or manual command (no JSON)

RULE 3: Speed detection for NAVIGATION:
- FAST: quickly, quick, rapidly, hurry, rush, asap, faster, fast
- SLOW: slowly, slow, careful, carefully, steady, safe, safer  
- NORMAL: default when no speed word is found

RULE 4: ALWAYS include BOTH destination AND speed in navigation JSON. Never omit the speed field.

EXAMPLES:

User: "go home"
Assistant: I'll take you home at normal speed.
JSON: {"task_type": "navigate", "action": "navigate_to", "parameters": {"destination": "home", "speed": "normal"}}

User: "bring me to airport"
Assistant: Taking you to the airport at normal speed.
JSON: {"task_type": "navigate", "action": "navigate_to", "parameters": {"destination": "airport", "speed": "normal"}}

User: "hi"
Assistant: Hello! Where would you like to go? I can take you home, to the office, school, or airport.

User: "stop"
Assistant: Stopping the vehicle now.
JSON: {"task_type": "manual_command", "action": "stop", "parameters": {"destination": null, "speed": null}}

User: "{"duration": 15, "fare": 12.5, "distance": 8.2}"
Assistant: That'll be $12.50 for an 8.2 km ride in 15 minutes. Thank you!

CRITICAL: Only output JSON for navigation and manual commands. For unclear inputs, ask for clarification."""

def detect_command_type(message):
    """Detect the type of command from user input"""
    lower_msg = message.lower().strip()
    
    # Check for fare report
    if is_fare_report_input(message):
        return "fare_report"
    
    # Navigation keywords and destinations
    nav_keywords = ['go', 'take', 'bring', 'drive', 'navigate', 'head']
    destinations = ['home', 'office', 'airport', 'school', 'work', 'house']
    
    # Manual command keywords
    manual_commands = {
        'stop': 'stop',
        'forward': 'go_forward',
        'go forward': 'go_forward',
        'move forward': 'go_forward',
        'backward': 'go_backward',
        'go backward': 'go_backward',
        'reverse': 'go_backward',
        'left': 'turn_left',
        'turn left': 'turn_left',
        'go left': 'turn_left',
        'right': 'turn_right',
        'turn right': 'turn_right',
        'go right': 'turn_right',
        'turn around': 'turn_around',
        'u-turn': 'turn_around'
    }
    
    # Check for manual commands
    for cmd, action in manual_commands.items():
        if cmd in lower_msg:
            return "manual", action
    
    # Check for navigation
    has_nav_keyword = any(keyword in lower_msg for keyword in nav_keywords)
    has_destination = any(dest in lower_msg for dest in destinations)
    
    # Even without nav keyword, if there's a clear destination, treat as navigation
    if has_destination:
        return "navigate"
    
    # If it has navigation keywords but no clear destination, still might be navigation
    if has_nav_keyword:
        return "navigate"
    
    return "chat"

def preprocess_command(message):
    """Preprocess command to help the model understand better"""
    lower_msg = message.lower()
    
    # Detect command type
    cmd_type = detect_command_type(message)
    
    if cmd_type == "fare_report":
        return message + " (Type: FARE_REPORT)"
    elif cmd_type == "chat":
        return message + " (Type: CHAT - not a navigation or manual command)"
    elif isinstance(cmd_type, tuple) and cmd_type[0] == "manual":
        return message + f" (Type: MANUAL, Action: {cmd_type[1]})"
    
    # For navigation commands, detect speed
    fast_words = ['quickly', 'quick', 'rapidly', 'hurry', 'rush', 'asap', 'faster', 'fast']
    slow_words = ['slowly', 'slow', 'careful', 'carefully', 'steady', 'safe', 'safer']
    
    speed = "normal"
    for word in fast_words:
        if word in lower_msg:
            speed = "fast"
            break
    
    if speed == "normal":
        for word in slow_words:
            if word in lower_msg:
                speed = "slow"
                break
    
    # Detect destination
    destination_map = {
        'home': 'home',
        'house': 'home',
        'office': 'office',
        'work': 'office',
        'school': 'school',
        'airport': 'airport'
    }
    
    destination = None
    for dest_var, dest_standard in destination_map.items():
        if dest_var in lower_msg:
            destination = dest_standard
            break
    
    hints = f" (Type: NAVIGATE, Destination: {destination or 'unknown'}, Speed: {speed})"
    return message + hints

def extract_json_from_response(response):
    """Extract JSON from the model's response"""
    # Look for JSON line
    json_match = re.search(r'JSON:\s*({.*})', response, re.IGNORECASE)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            return None
    return None

def post_process_response(response, message):
    """Post-process the response to ensure it's valid"""
    # Extract JSON if present
    parsed_json = extract_json_from_response(response)
    
    # If it's a navigation command but JSON is missing or incomplete, fix it
    cmd_type = detect_command_type(message)
    
    if cmd_type == "navigate" and parsed_json:
        # Ensure speed field exists
        if 'parameters' in parsed_json and 'speed' not in parsed_json['parameters']:
            parsed_json['parameters']['speed'] = 'normal'
            
            # Reconstruct response with fixed JSON
            lines = response.split('\n')
            if len(lines) > 0:
                fixed_response = lines[0] + '\n' + f"JSON: {json.dumps(parsed_json)}"
                return fixed_response, parsed_json
    
    return response, parsed_json

def chat_with_driving_assistant(message, url="http://localhost:11434/api/generate", model="smollm2"):
    """Send message to Ollama with system prompt and stream response"""
    
    # Preprocess the message
    processed_message = preprocess_command(message)
    
    # System prompt and user message combination
    full_prompt = f"{SYSTEM_PROMPT}\n\nUser: {processed_message}\nAssistant:"

    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": True,
        "options": {
            "temperature": 0.1,
            "top_p": 0.8,
            "repeat_penalty": 1.1,
            "num_predict": 150
        }
    }

    try:
        response = requests.post(url, json=payload, stream=True)
        response.raise_for_status()

        print("🤖 Driving Assistant: ", end='', flush=True)
        full_response = ""
        buffer = ""

        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                if 'response' in data:
                    chunk = data['response']
                    buffer += chunk
                    
                    # Clean display: remove hints but preserve spaces
                    clean_chunk = re.sub(r'\s*\(Type:.*?\)\s*', ' ', chunk)
                    # Also clean any double spaces
                    clean_chunk = re.sub(r'\s+', ' ', clean_chunk)
                    
                    # Print cleaned chunk
                    print(clean_chunk, end='', flush=True)
                    full_response += chunk
                    
                if data.get('done', False):
                    break

        print()  # New line
        
        # Post-process to fix any JSON issues
        full_response, parsed_json = post_process_response(full_response, message)
        
        # Display parsed JSON if available
        if parsed_json and not is_fare_report_input(message):
            print("\n📊 Parsed Command:")
            print(f"   Task Type: {parsed_json.get('task_type', 'unknown')}")
            print(f"   Action: {parsed_json.get('action', 'unknown')}")
            if 'parameters' in parsed_json:
                params = parsed_json['parameters']
                if params.get('destination'):
                    print(f"   Destination: {params['destination']}")
                if params.get('speed') is not None:
                    print(f"   Speed: {params['speed']}")
        
        return full_response

    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to Ollama server. Is it running on localhost:11434?")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def is_fare_report_input(message):
    """Check if the input is a fare report JSON"""
    try:
        data = json.loads(message.strip())
        required_keys = {'duration', 'fare', 'distance'}
        return (isinstance(data, dict) and
                required_keys.issubset(set(data.keys())) and
                all(isinstance(data[key], (int, float)) for key in required_keys))
    except:
        return False

def show_examples():
    """Show example commands"""
    print("\n📚 Example Commands:")
    print("\n  🧭 Navigation:")
    print("    • 'go home' → normal speed")
    print("    • 'take me home quickly' → fast speed")
    print("    • 'drive to the office' → normal speed")
    print("    • 'bring me to school carefully' → slow speed")
    print("    • 'i want to go to the airport' → normal speed")
    print("\n  🎮 Manual Control:")
    print("    • 'stop' → stop the vehicle")
    print("    • 'go forward' → move forward")
    print("    • 'turn left' → turn left")
    print("    • 'reverse' → go backward")
    print("\n  💰 Fare Report:")
    print("    • '{\"duration\": 23, \"fare\": 18.5, \"distance\": 12.4}'")
    print("\n  💬 Other inputs will be treated as chat")

def main():
    print("🚗 Robust Robotic Driving Assistant (Ctrl+C to exit)")
    print("=" * 50)
    print("Commands:")
    print("  • Navigation: 'go home', 'take me to school', 'bring me to airport'")
    print("  • Manual control: 'stop', 'go forward', 'turn left', 'reverse'")
    print("  • Fare report: '{\"duration\": 23, \"fare\": 18.5, \"distance\": 12.4}'")
    print("  • Type 'help' to see more examples")
    print("-" * 50)

    try:
        while True:
            message = input("\n🗣️  You: ").strip()
            if message:
                if message.lower() in ['exit', 'quit', '종료']:
                    break
                elif message.lower() in ['help', 'examples', '?']:
                    show_examples()
                    continue

                chat_with_driving_assistant(message)

    except KeyboardInterrupt:
        print("\n👋 Goodbye! Drive safely!")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Single message mode
        message = " ".join(sys.argv[1:])
        print(f"🚗 Processing command: {message}")
        chat_with_driving_assistant(message)
    else:
        # Interactive mode
        main()

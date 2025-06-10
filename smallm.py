#!/usr/bin/env python3
"""Lightweight Ollama smollm2 Terminal Client"""

import requests
import json
import sys

def chat_with_phi4(message, url="http://localhost:11434/api/generate", model="smollm2"):
    """Send message to Ollama and stream response"""
    payload = {
        "model": model,
        "prompt": message,
        "stream": True
    }
    
    try:
        response = requests.post(url, json=payload, stream=True)
        response.raise_for_status()
        
        print("🤖 AI: ", end='', flush=True)
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                if 'response' in data:
                    print(data['response'], end='', flush=True)
                if data.get('done', False):
                    break
        print()  # New line
        
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    print("🤖 Lightweight smollm2 Chat (Ctrl+C to exit)")
    print("-" * 40)
    
    try:
        while True:
            message = input("\n💬 You: ").strip()
            if message:
                chat_with_phi4(message)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Single message mode
        chat_with_phi4(" ".join(sys.argv[1:]))
    else:
        # Interactive mode
        main()

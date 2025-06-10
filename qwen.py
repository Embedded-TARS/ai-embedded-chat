#!/usr/bin/env python3
"""Lightweight Ollama Terminal Client"""
import requests
import json
import sys
import re

def chat_with_ollama(message, url="http://localhost:11434/api/generate", model="qwen3:1.7b"):
    """Send message to Ollama and stream response"""
    payload = {
        "model": model,
        "prompt": message,
        "stream": True
    }
    
    try:
        response = requests.post(url, json=payload, stream=True)
        response.raise_for_status()
        
        print("🤖 Assistant: ", end='', flush=True)
        
        full_response = ""
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                if 'response' in data:
                    full_response += data['response']
                if data.get('done', False):
                    break
        
        # Filter out content between <think> and </think> tags
        filtered_response = re.sub(r'<think>.*?</think>\s*', '', full_response, flags=re.DOTALL)
        print(filtered_response.strip())
        
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    print("🤖 Lightweight Ollama Chat (Ctrl+C to exit)")
    print("-" * 40)
    
    try:
        while True:
            message = input("\n💬 You: ").strip()
            if message:
                chat_with_ollama(message)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Single message mode
        chat_with_ollama(" ".join(sys.argv[1:]))
    else:
        # Interactive mode
        main()

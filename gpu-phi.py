#!/usr/bin/env python3
"""Lightweight Ollama Phi-4 Terminal Client with Jetson support"""

import requests
import json
import sys
import time

def check_ollama_status(base_url="http://localhost:11434"):
    """Check if Ollama is running and what models are available"""
    try:
        # Check if Ollama is running
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"✅ Ollama is running at {base_url}")
            if models:
                print(f"📦 Available models: {', '.join([m['name'] for m in models])}")
                return True, [m['name'] for m in models]
            else:
                print("⚠️  No models installed")
                return True, []
        else:
            print(f"❌ Ollama responded with status: {response.status_code}")
            return False, []
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to Ollama at {base_url}")
        print("💡 Make sure Ollama is running: ollama serve")
        return False, []
    except Exception as e:
        print(f"❌ Error checking Ollama: {e}")
        return False, []

def chat_with_phi4(message, url="http://localhost:11434/api/generate", model="phi4", use_gpu=True):
    """Send message to Ollama and stream response with GPU support"""
    payload = {
        "model": model,
        "prompt": message,
        "stream": True,
        "options": {
            "num_gpu": -1 if use_gpu else 0,  # -1 uses all available GPUs, 0 uses CPU only
            "num_thread": 4 if not use_gpu else None  # CPU threads when not using GPU
        }
    }
    
    try:
        response = requests.post(url, json=payload, stream=True, timeout=30)
        response.raise_for_status()
        
        print("🤖 Phi-4: ", end='', flush=True)
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                if 'response' in data:
                    print(data['response'], end='', flush=True)
                if data.get('done', False):
                    break
        print()  # New line
        
    except requests.exceptions.Timeout:
        print("❌ Request timed out. Model might be loading...")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"❌ Model '{model}' not found. Try: ollama pull {model}")
        else:
            print(f"❌ HTTP Error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    # Check for GPU flag
    use_gpu = "--cpu" not in sys.argv
    if "--cpu" in sys.argv:
        sys.argv.remove("--cpu")
    
    # Check for custom model
    model = "phi4-mini"  # Default to phi4-mini for better Jetson compatibility
    if "--model" in sys.argv:
        idx = sys.argv.index("--model")
        if idx + 1 < len(sys.argv):
            model = sys.argv[idx + 1]
            sys.argv.remove("--model")
            sys.argv.remove(model)
    
    print("🔍 Checking Ollama status...")
    is_running, available_models = check_ollama_status()
    
    if not is_running:
        print("\n💡 To start Ollama:")
        print("   ollama serve")
        print(f"\n💡 To install {model}:")
        print(f"   ollama pull {model}")
        return
    
    # Check if model exists (with or without :latest tag)
    model_found = False
    actual_model = model
    
    if available_models:
        # Try exact match first
        if model in available_models:
            model_found = True
            actual_model = model
        # Try with :latest suffix
        elif f"{model}:latest" in available_models:
            model_found = True
            actual_model = f"{model}:latest"
        # Try without :latest suffix
        elif any(m.startswith(f"{model}:") for m in available_models):
            matching = [m for m in available_models if m.startswith(f"{model}:")]
            model_found = True
            actual_model = matching[0]
    
    if available_models and not model_found:
        print(f"\n⚠️  Model '{model}' not found in available models")
        print(f"💡 Install it with: ollama pull {model}")
        print(f"💡 Or use an available model: {', '.join(available_models)}")
        return
    
    gpu_status = "🚀 GPU" if use_gpu else "💻 CPU"
    print(f"\n🤖 Lightweight {model.upper()} Chat ({gpu_status}) - Ctrl+C to exit")
    print("Flags: --cpu (force CPU), --model <name>")
    print("-" * 50)
    
    try:
        while True:
            message = input("\n💬 You: ").strip()
            if message:
                chat_with_phi4(message, model=model, use_gpu=use_gpu)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        # Single message mode
        use_gpu = "--cpu" not in sys.argv
        model = "phi4"
        
        # Parse flags
        args_copy = sys.argv[1:]
        if "--cpu" in args_copy:
            args_copy.remove("--cpu")
        if "--model" in args_copy:
            idx = args_copy.index("--model")
            if idx + 1 < len(args_copy):
                model = args_copy[idx + 1]
                args_copy.remove("--model")
                args_copy.remove(model)
        else:
            model = "phi4-mini"  # Default for single message mode too
        
        message = " ".join(args_copy)
        if message:
            chat_with_phi4(message, model=model, use_gpu=use_gpu)
    else:
        # Interactive mode
        main()

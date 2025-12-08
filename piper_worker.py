"""
Piper TTS Worker - Simple Version
"""
import os
import sys
import subprocess
import time

def start_piper():
    """Start Piper TTS server"""
    print("🚀 Starting Piper TTS...")
    
    # Check if piper-tts is installed
    try:
        import piper
        print("✅ Piper TTS is installed")
    except ImportError:
        print("❌ Piper TTS not installed. Please add to requirements.txt")
        return
    
    # Create voices directory
    voices_dir = "voices"
    os.makedirs(voices_dir, exist_ok=True)
    
    # Download a default voice if not exists
    default_voice = "en_US-lessac-medium.onnx"
    voice_path = os.path.join(voices_dir, default_voice)
    
    if not os.path.exists(voice_path):
        print("📥 Downloading default voice...")
        import requests
        
        voice_url = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
        
        try:
            response = requests.get(voice_url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(voice_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"✅ Voice downloaded: {default_voice}")
        except Exception as e:
            print(f"❌ Failed to download voice: {e}")
            return
    
    # Start Piper HTTP server
    print(f"🔧 Starting Piper server on port 5001...")
    
    cmd = [
        sys.executable, "-m", "piper",
        "--model", voice_path,
        "--host", "0.0.0.0",
        "--port", "5001"
    ]
    
    try:
        # Run Piper server (this will block)
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print("✅ Piper TTS Server is running!")
        print("📡 Endpoint: http://localhost:5001")
        
        # Print output
        while True:
            output = process.stdout.readline()
            if output:
                print(f"[Piper] {output.strip()}")
            
            error = process.stderr.readline()
            if error:
                print(f"[Piper Error] {error.strip()}")
            
            # Check if process is still running
            if process.poll() is not None:
                break
            
            time.sleep(0.1)
                
    except Exception as e:
        print(f"❌ Error starting Piper: {e}")
    finally:
        if 'process' in locals() and process.poll() is None:
            process.terminate()

if __name__ == "__main__":
    start_piper()

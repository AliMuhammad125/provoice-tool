"""
Piper TTS Server
"""
import os
import sys
import subprocess
import time
import atexit

def start_piper_server():
    """Start Piper TTS server"""
    print("🚀 Starting Piper TTS Server...")
    
    # Check if Piper is installed
    try:
        import piper
        print("✅ Piper TTS is installed")
    except ImportError:
        print("❌ Piper TTS not installed. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "piper-tts"])
    
    # Create voices directory
    voices_dir = "voices"
    os.makedirs(voices_dir, exist_ok=True)
    
    # Download default voice if not exists
    default_voice = "en_US-lessac-medium.onnx"
    voice_path = os.path.join(voices_dir, default_voice)
    
    if not os.path.exists(voice_path):
        print("📥 Downloading default voice...")
        voice_url = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
        
        try:
            import requests
            response = requests.get(voice_url, stream=True)
            with open(voice_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"✅ Voice downloaded: {default_voice}")
        except Exception as e:
            print(f"❌ Failed to download voice: {e}")
            return
    
    # Start Piper server
    cmd = [
        sys.executable, "-m", "piper",
        "--model", voice_path,
        "--host", "127.0.0.1",
        "--port", "5001",
        "--debug"
    ]
    
    print(f"🔧 Starting command: {' '.join(cmd)}")
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Register cleanup
        def cleanup():
            if process.poll() is None:
                process.terminate()
                process.wait()
                print("✅ Piper server stopped")
        
        atexit.register(cleanup)
        
        # Wait a bit for server to start
        time.sleep(3)
        
        # Check if server is running
        if process.poll() is None:
            print("✅ Piper TTS Server is running on http://localhost:5001")
            
            # Read output in background
            import threading
            
            def read_output():
                while True:
                    output = process.stdout.readline()
                    if output:
                        print(f"[Piper] {output.strip()}")
            
            output_thread = threading.Thread(target=read_output, daemon=True)
            output_thread.start()
            
            # Keep the process alive
            process.wait()
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Piper server failed to start")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            
    except Exception as e:
        print(f"❌ Error starting Piper server: {e}")

if __name__ == "__main__":
    start_piper_server()

import os
import uuid
import time
import sys
import requests
import threading
import subprocess
from flask import Flask, render_template, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

# Config
AUDIO_DIR = os.path.join("static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)
MAX_CHARS = 10000

# Piper Server
PIPER_PORT = 5001
PIPER_URL = f"http://localhost:{PIPER_PORT}"

# Voice Map (Piper Voices)
VOICE_MAP = {
    'en-us': {'Male': 'en_US-lessac-medium', 'Female': 'en_US-kathleen-medium'},
    'en-uk': {'Male': 'en_GB-semaine-medium', 'Female': 'en_GB-semaine-medium'},
    'hi': {'Male': 'hi_IN-medium', 'Female': 'hi_IN-medium'},
    'ur': {'Male': 'ur_PK-medium', 'Female': 'ur_PK-medium'},
    'story': {'Male': 'en_US-lessac-medium'},
    'horror': {'Male': 'en_US-vctk-medium'},
    'cartoon': {'Male': 'en_US-hfc_male-medium'},
    'news': {'Female': 'en_GB-semaine-medium'},
    'ar': {'Male': 'ar_SA-medium', 'Female': 'ar_SA-medium'},
    'es': {'Male': 'es_ES-medium', 'Female': 'es_ES-medium'},
    'fr': {'Male': 'fr_FR-medium', 'Female': 'fr_FR-medium'},
    'default': {'Male': 'en_US-lessac-medium', 'Female': 'en_US-kathleen-medium'}
}

# Cleanup
def cleanup_files():
    now = time.time()
    for f in os.listdir(AUDIO_DIR):
        f_path = os.path.join(AUDIO_DIR, f)
        if os.path.isfile(f_path) and (now - os.path.getmtime(f_path) > 600):
            try:
                os.remove(f_path)
            except:
                pass

scheduler = BackgroundScheduler()
scheduler.add_job(func=cleanup_files, trigger="interval", minutes=10)
scheduler.start()

# Piper Server Startup
def start_piper_server():
    """Start Piper TTS server"""
    print("🚀 Starting Piper TTS Server...")
    
    try:
        import piper
        print("✅ Piper TTS is available")
    except ImportError:
        print("❌ Piper TTS not installed!")
        return False
    
    # Download voice if needed
    voices_dir = "voices"
    os.makedirs(voices_dir, exist_ok=True)
    
    default_voice = "en_US-lessac-medium.onnx"
    voice_path = os.path.join(voices_dir, default_voice)
    
    if not os.path.exists(voice_path):
        print("📥 Downloading default voice...")
        try:
            voice_url = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
            response = requests.get(voice_url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(voice_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print("✅ Voice downloaded")
        except Exception as e:
            print(f"❌ Failed to download voice: {e}")
            return False
    
    # Start Piper server
    print(f"🔧 Starting Piper server on port {PIPER_PORT}...")
    
    cmd = [
        sys.executable, "-m", "piper",
        "--model", voice_path,
        "--host", "0.0.0.0",
        "--port", str(PIPER_PORT)
    ]
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        time.sleep(3)
        
        if process.poll() is None:
            print("✅ Piper server started!")
            return True
        else:
            print("❌ Piper server failed to start")
            return False
            
    except Exception as e:
        print(f"❌ Error starting Piper: {e}")
        return False

# Start Piper
PIPER_READY = False
try:
    PIPER_READY = start_piper_server()
except Exception as e:
    print(f"⚠️ Piper startup error: {e}")

# Piper Generator
def generate_with_piper(text, voice, speed=0):
    """Generate audio using Piper TTS"""
    try:
        params = {'text': text, 'voice': voice}
        
        if speed != 0:
            length_scale = 1.0 - (speed / 100.0)
            params['length_scale'] = max(0.5, min(2.0, length_scale))
        
        response = requests.post(
            f"{PIPER_URL}/generate",
            json=params,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.content
            
    except Exception as e:
        print(f"Piper error: {e}")
    
    return None

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.json
        text = data.get('text', '').strip()
        lang_code = data.get('language', 'en-us')
        gender = data.get('gender', 'Male')
        pitch_val = int(data.get('pitch', 0))
        speed_val = int(data.get('speed', 0))

        # Validation
        if not text:
            return jsonify({'error': 'Please enter text.'}), 400
        if len(text) > MAX_CHARS:
            return jsonify({'error': 'Text too long.'}), 400

        # Voice Selection
        voice_config = VOICE_MAP.get(lang_code, VOICE_MAP['default'])
        
        if lang_code in ['story', 'horror', 'cartoon', 'news']:
            selected_voice = list(voice_config.values())[0]
        else:
            selected_voice = voice_config.get(gender, voice_config['Male'])

        # Generate filename (FIXED LINE)
        filename = f"audio_{str(uuid.uuid4())[:8]}.wav"
        filepath = os.path.join(AUDIO_DIR, filename)
        
        # Generate with Piper
        if PIPER_READY:
            audio_data = generate_with_piper(text, selected_voice, speed_val)
            
            if audio_data:
                with open(filepath, 'wb') as f:
                    f.write(audio_data)
                
                return jsonify({
                    'success': True,
                    'file_url': f"/static/audio/{filename}",
                    'filename': filename,
                    'source': 'piper'
                })
            else:
                return jsonify({'error': 'Piper generation failed.'}), 500
        else:
            return jsonify({'error': 'Piper TTS not available.'}), 500

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Server error. Try again.'}), 500

@app.route('/api/status')
def status():
    piper_status = 'offline'
    
    if PIPER_READY:
        try:
            response = requests.get(f"{PIPER_URL}/", timeout=5)
            piper_status = 'online' if response.status_code == 200 else 'offline'
        except:
            pass
    
    return jsonify({
        'status': 'online',
        'piper_ready': PIPER_READY,
        'piper_status': piper_status
    })

@app.route('/test')
def test():
    return jsonify({
        'status': 'ok',
        'piper_ready': PIPER_READY,
        'audio_dir': os.path.exists(AUDIO_DIR)
    })

if __name__ == '__main__':
    print(f"🚀 Server Starting...")
    print(f"🔊 Piper Ready: {PIPER_READY}")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)

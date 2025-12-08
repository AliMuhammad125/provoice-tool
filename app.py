import os
import uuid
import time
import json
import hashlib
import threading
import subprocess
import sys
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import requests

app = Flask(__name__)

# Config
AUDIO_DIR = os.path.join("static", "audio")
CACHE_DIR = os.path.join("data", "cache")
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)
MAX_CHARS = 5000

# Piper Server URL (will be started in background)
PIPER_SERVER = "http://localhost:5001"

# --- VOICE MAP (Piper Voices) ---
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

# --- CACHE SYSTEM ---
def get_cache_key(text, lang_code, gender, pitch, speed):
    key_string = f"{text}|{lang_code}|{gender}|{pitch}|{speed}"
    return hashlib.md5(key_string.encode()).hexdigest()

def get_cached_audio(cache_key):
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            cache_time = datetime.fromisoformat(cache_data['timestamp'])
            if (datetime.now() - cache_time).total_seconds() < 604800:
                return cache_data['filename']
        except:
            pass
    return None

def save_to_cache(cache_key, filename):
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    
    cache_data = {
        'filename': filename,
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
    except:
        pass

# --- CLEANUP ---
def cleanup_files():
    now = time.time()
    
    for f in os.listdir(AUDIO_DIR):
        f_path = os.path.join(AUDIO_DIR, f)
        if os.path.isfile(f_path) and (now - os.path.getmtime(f_path) > 3600):
            try:
                os.remove(f_path)
            except:
                pass

scheduler = BackgroundScheduler()
scheduler.add_job(func=cleanup_files, trigger="interval", minutes=10)
scheduler.start()

# --- ROMAN URDU ---
try:
    from roman_urdu import roman_urdu_to_urdu_text
    ROMAN_URDU_SUPPORT = True
except ImportError:
    ROMAN_URDU_SUPPORT = False
    roman_urdu_to_urdu_text = lambda x: x

# --- PIPER SERVER STARTUP ---
def start_piper_server():
    """Start Piper TTS server in background"""
    print("🚀 Attempting to start Piper server...")
    
    try:
        # Check if piper is installed
        import piper
        print("✅ Piper TTS is available")
    except ImportError:
        print("❌ Piper TTS not installed. Using fallback mode.")
        return
    
    # Download a voice if needed
    voices_dir = "voices"
    os.makedirs(voices_dir, exist_ok=True)
    
    default_voice = "en_US-lessac-medium.onnx"
    voice_path = os.path.join(voices_dir, default_voice)
    
    if not os.path.exists(voice_path):
        print("📥 Downloading default voice...")
        try:
            import requests as rq
            voice_url = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
            
            response = rq.get(voice_url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(voice_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print("✅ Voice downloaded")
        except Exception as e:
            print(f"❌ Failed to download voice: {e}")
            return
    
    # Start Piper server
    print("🔧 Starting Piper HTTP server...")
    
    cmd = [
        sys.executable, "-m", "piper",
        "--model", voice_path,
        "--host", "0.0.0.0",
        "--port", "5001",
        "--debug"
    ]
    
    try:
        # Run in background
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit for server to start
        time.sleep(3)
        
        # Check if server is running
        if process.poll() is None:
            print("✅ Piper server started on port 5001")
            
            # Start thread to read output
            def read_output():
                while True:
                    if process.poll() is not None:
                        break
                    line = process.stdout.readline()
                    if line:
                        print(f"[Piper] {line.strip()}")
            
            output_thread = threading.Thread(target=read_output, daemon=True)
            output_thread.start()
            
            return process
        else:
            print("❌ Piper server failed to start")
            stdout, stderr = process.communicate()
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            
    except Exception as e:
        print(f"❌ Error starting Piper: {e}")
    
    return None

# Start Piper server when app starts
piper_process = None
PIPER_AVAILABLE = False

try:
    piper_process = start_piper_server()
    if piper_process:
        PIPER_AVAILABLE = True
        print("🎉 Piper TTS ready for use!")
except Exception as e:
    print(f"⚠️ Piper initialization failed: {e}")

# --- PIPER GENERATOR ---
def generate_piper_audio(text, voice, speed, pitch, filename):
    """Generate audio using Piper TTS"""
    if not PIPER_AVAILABLE:
        return False
    
    try:
        # Simple speed adjustment
        length_scale = 1.0
        if speed > 0:
            length_scale = max(0.5, 1.0 - (speed / 200.0))
        elif speed < 0:
            length_scale = min(2.0, 1.0 + (abs(speed) / 100.0))
        
        response = requests.post(
            f"{PIPER_SERVER}/generate",
            json={
                'text': text,
                'voice': voice,
                'length_scale': length_scale
            },
            timeout=10
        )
        
        if response.status_code == 200:
            filepath = os.path.join(AUDIO_DIR, filename)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            return True
            
    except Exception as e:
        print(f"Piper Error: {e}")
    
    return False

# --- EDGE-TTS FALLBACK ---
def generate_edge_audio(text, lang_code, gender, pitch, speed, filename):
    """Fallback to Edge-TTS if Piper fails"""
    try:
        # Edge-TTS voice mapping
        EDGE_VOICES = {
            'en-us': {'Male': 'en-US-GuyNeural', 'Female': 'en-US-JennyNeural'},
            'en-uk': {'Male': 'en-GB-RyanNeural', 'Female': 'en-GB-SoniaNeural'},
            'hi': {'Male': 'hi-IN-MadhurNeural', 'Female': 'hi-IN-SwaraNeural'},
            'ur': {'Male': 'ur-PK-SalmanNeural', 'Female': 'ur-PK-UzmaNeural'},
            'default': {'Male': 'en-US-GuyNeural', 'Female': 'en-US-JennyNeural'}
        }
        
        voice_config = EDGE_VOICES.get(lang_code, EDGE_VOICES['default'])
        voice = voice_config.get(gender, voice_config['Male'])
        
        # Generate with Edge-TTS
        import edge_tts
        import asyncio
        
        pitch_str = f"{'+' if pitch >= 0 else ''}{pitch}Hz"
        rate_str = f"{'+' if speed >= 0 else ''}{speed}%"
        
        async def generate():
            communicate = edge_tts.Communicate(text, voice, pitch=pitch_str, rate=rate_str)
            await communicate.save(os.path.join(AUDIO_DIR, filename))
        
        # Set event loop policy for Windows/Linux
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(generate())
            return True
        finally:
            loop.close()
            
    except Exception as e:
        print(f"Edge-TTS Error: {e}")
    
    return False

# --- ROUTES ---
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
        input_type = data.get('input_type', 'normal')

        # Validation
        if not text:
            return jsonify({'error': 'Please enter text.'}), 400
        if len(text) > MAX_CHARS:
            return jsonify({'error': f'Text too long. Max {MAX_CHARS} characters.'}), 400

        # Roman Urdu Conversion
        if input_type == 'roman_urdu' and ROMAN_URDU_SUPPORT:
            text = roman_urdu_to_urdu_text(text)

        # Check cache first
        cache_key = get_cache_key(text, lang_code, gender, pitch_val, speed_val)
        cached_file = get_cached_audio(cache_key)
        
        if cached_file:
            return jsonify({
                'success': True,
                'file_url': f"/static/audio/{cached_file}",
                'filename': cached_file,
                'source': 'cache',
                'input_type': input_type
            })

        # Voice Selection for Piper
        voice_config = VOICE_MAP.get(lang_code, VOICE_MAP['default'])
        
        if lang_code in ['story', 'horror', 'cartoon', 'news']:
            selected_voice = list(voice_config.values())[0]
        else:
            selected_voice = voice_config.get(gender, voice_config['Male'])

        # Generate filename
        filename = f"audio_{uuid.uuid4()[:8]}.wav"
        
        # Try Piper first
        if PIPER_AVAILABLE and generate_piper_audio(text, selected_voice, speed_val, pitch_val, filename):
            source = 'piper'
        else:
            # Fallback to Edge-TTS
            if generate_edge_audio(text, lang_code, gender, pitch_val, speed_val, filename):
                source = 'edge'
            else:
                return jsonify({'error': 'Audio generation failed. Please try again.'}), 500
        
        # Save to cache
        save_to_cache(cache_key, filename)
        
        return jsonify({
            'success': True,
            'file_url': f"/static/audio/{filename}",
            'filename': filename,
            'source': source,
            'input_type': input_type
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Server error. Please try again.'}), 500

@app.route('/api/status')
def status():
    """Check system status"""
    piper_status = 'offline'
    if PIPER_AVAILABLE:
        try:
            response = requests.get(f"{PIPER_SERVER}/status", timeout=2)
            piper_status = 'online' if response.status_code == 200 else 'offline'
        except:
            piper_status = 'offline'
    
    cache_count = len([f for f in os.listdir(CACHE_DIR) if f.endswith('.json')])
    
    return jsonify({
        'status': 'online',
        'piper_available': PIPER_AVAILABLE,
        'piper_status': piper_status,
        'roman_urdu_support': ROMAN_URDU_SUPPORT,
        'cache_entries': cache_count,
        'engine': 'piper+edge_tts_hybrid'
    })

if __name__ == '__main__':
    print(f"🚀 TTS Server Starting...")
    print(f"🔊 Piper Available: {PIPER_AVAILABLE}")
    print(f"🇵🇰 Roman Urdu Support: {ROMAN_URDU_SUPPORT}")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)

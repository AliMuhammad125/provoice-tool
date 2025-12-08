import os
import uuid
import time
import json
import hashlib
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

# Piper Server URL (Render.com internal)
PIPER_SERVER = "http://localhost:5001"

# --- VOICE MAP (Piper Voices) ---
VOICE_MAP = {
    # English
    'en-us': {'Male': 'en_US-lessac-medium', 'Female': 'en_US-kathleen-medium'},
    'en-uk': {'Male': 'en_GB-semaine-medium', 'Female': 'en_GB-semaine-medium'},
    
    # Hindi & Urdu
    'hi': {'Male': 'hi_IN-medium', 'Female': 'hi_IN-medium'},
    'ur': {'Male': 'ur_PK-medium', 'Female': 'ur_PK-medium'},
    
    # Special Voices
    'story': {'Male': 'en_US-lessac-medium'},
    'horror': {'Male': 'en_US-vctk-medium'},
    'cartoon': {'Male': 'en_US-hfc_male-medium'},
    'news': {'Female': 'en_GB-semaine-medium'},
    
    # Other Languages
    'ar': {'Male': 'ar_SA-medium', 'Female': 'ar_SA-medium'},
    'es': {'Male': 'es_ES-medium', 'Female': 'es_ES-medium'},
    'fr': {'Male': 'fr_FR-medium', 'Female': 'fr_FR-medium'},
    
    'default': {'Male': 'en_US-lessac-medium', 'Female': 'en_US-kathleen-medium'}
}

# --- CACHE SYSTEM ---
def get_cache_key(text, lang_code, gender, pitch, speed):
    """Generate unique cache key"""
    key_string = f"{text}|{lang_code}|{gender}|{pitch}|{speed}"
    return hashlib.md5(key_string.encode()).hexdigest()

def get_cached_audio(cache_key):
    """Get audio from cache"""
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Check if cache is valid (7 days)
            cache_time = datetime.fromisoformat(cache_data['timestamp'])
            if (datetime.now() - cache_time).total_seconds() < 604800:
                return cache_data['filename']
        except:
            pass
    return None

def save_to_cache(cache_key, filename):
    """Save audio to cache"""
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
    """Clean old files"""
    now = time.time()
    
    # Audio files (1 hour)
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

# --- PIPER GENERATOR ---
def generate_piper_audio(text, voice, speed, pitch, filename):
    """Generate audio using Piper TTS"""
    try:
        # Prepare parameters
        length_scale = 1.0
        if speed > 0:  # Faster
            length_scale = max(0.5, 1.0 - (speed / 200.0))
        elif speed < 0:  # Slower
            length_scale = min(2.0, 1.0 + (abs(speed) / 100.0))
        
        # Call Piper server
        response = requests.post(
            f"{PIPER_SERVER}/generate",
            json={
                'text': text,
                'voice': voice,
                'length_scale': length_scale,
                'pitch_adjust': pitch / 10.0  # Simple pitch adjustment
            },
            timeout=15  # Shorter timeout
        )
        
        if response.status_code == 200:
            filepath = os.path.join(AUDIO_DIR, filename)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            return True
    except Exception as e:
        print(f"Piper Error: {e}")
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

        # Voice Selection
        voice_config = VOICE_MAP.get(lang_code, VOICE_MAP['default'])
        
        if lang_code in ['story', 'horror', 'cartoon', 'news']:
            selected_voice = list(voice_config.values())[0]
        else:
            selected_voice = voice_config.get(gender, voice_config['Male'])

        # Generate filename
        filename = f"audio_{uuid.uuid4()[:8]}.wav"
        
        # Generate with Piper
        if generate_piper_audio(text, selected_voice, speed_val, pitch_val, filename):
            # Save to cache
            save_to_cache(cache_key, filename)
            
            return jsonify({
                'success': True,
                'file_url': f"/static/audio/{filename}",
                'filename': filename,
                'source': 'piper',
                'input_type': input_type
            })
        else:
            return jsonify({'error': 'Audio generation failed. Please try again.'}), 500

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Server error. Please try again.'}), 500

@app.route('/api/status')
def status():
    """Check system status"""
    try:
        # Check Piper server
        response = requests.get(f"{PIPER_SERVER}/status", timeout=5)
        piper_status = 'online' if response.status_code == 200 else 'offline'
    except:
        piper_status = 'offline'
    
    # Count cache files
    cache_count = len([f for f in os.listdir(CACHE_DIR) if f.endswith('.json')])
    
    return jsonify({
        'status': 'online',
        'piper_server': piper_status,
        'roman_urdu_support': ROMAN_URDU_SUPPORT,
        'cache_entries': cache_count,
        'voices_available': list(VOICE_MAP.keys())
    })

if __name__ == '__main__':
    print("🚀 TTS Server Starting...")
    print(f"🔊 Piper Server: {PIPER_SERVER}")
    print(f"🇵🇰 Roman Urdu Support: {ROMAN_URDU_SUPPORT}")
    print(f"💾 Cache Directory: {CACHE_DIR}")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)

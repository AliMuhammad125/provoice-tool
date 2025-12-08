import os
import uuid
import asyncio
import time
import sys
import requests
import threading
from flask import Flask, render_template, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import edge_tts

# --- WINDOWS/LINUX FIX ---
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

app = Flask(__name__)

# Config
AUDIO_DIR = os.path.join("static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)
MAX_CHARS = 10000

# --- TTS MODE ---
# Change to 'piper' for Piper TTS, 'edge' for Edge-TTS, 'auto' for auto-select
TTS_MODE = 'auto'  # 'auto' will try Piper first, then Edge-TTS

# --- PIPER SERVER CONFIG ---
PIPER_SERVER_URL = "http://localhost:5001"

# --- VOICE MAP (EDGE-TTS) ---
EDGE_VOICE_MAP = {
    'ur': {'Male': 'ur-PK-SalmanNeural', 'Female': 'ur-PK-UzmaNeural'},
    'hi': {'Male': 'hi-IN-MadhurNeural', 'Female': 'hi-IN-SwaraNeural'},
    'en-us': {'Male': 'en-US-GuyNeural', 'Female': 'en-US-JennyNeural'},
    'en-uk': {'Male': 'en-GB-RyanNeural', 'Female': 'en-GB-SoniaNeural'},
    'en-in': {'Male': 'en-IN-PrabhatNeural', 'Female': 'en-IN-NeerjaNeural'},
    'story': {'Male': 'en-US-ChristopherNeural'},
    'horror': {'Male': 'en-US-EricNeural'},
    'cartoon': {'Female': 'en-US-AnaNeural'},
    'news': {'Female': 'en-US-AriaNeural'},
    'ar': {'Male': 'ar-SA-HamedNeural', 'Female': 'ar-SA-ZariyahNeural'},
    'es': {'Male': 'es-ES-AlvaroNeural', 'Female': 'es-ES-ElviraNeural'},
    'fr': {'Male': 'fr-FR-HenriNeural', 'Female': 'fr-FR-DeniseNeural'},
    'default': {'Male': 'en-US-GuyNeural', 'Female': 'en-US-JennyNeural'}
}

# --- PIPER VOICE MAP ---
PIPER_VOICE_MAP = {
    'ur': {'Male': 'ur_PK-medium', 'Female': 'ur_PK-medium'},
    'hi': {'Male': 'hi_IN-medium', 'Female': 'hi_IN-medium'},
    'en-us': {'Male': 'en_US-lessac-medium', 'Female': 'en_US-kathleen-medium'},
    'en-uk': {'Male': 'en_GB-semaine-medium', 'Female': 'en_GB-semaine-medium'},
    'en-in': {'Male': 'en_IN-medium', 'Female': 'en_IN-medium'},
    'story': {'Male': 'en_US-lessac-medium'},
    'horror': {'Male': 'en_US-vctk-medium'},
    'cartoon': {'Male': 'en_US-hfc_male-medium'},
    'news': {'Female': 'en_GB-semaine-medium'},
    'default': {'Male': 'en_US-lessac-medium', 'Female': 'en_US-kathleen-medium'}
}

# --- CLEANUP TASK ---
def cleanup_files():
    now = time.time()
    for f in os.listdir(AUDIO_DIR):
        f_path = os.path.join(AUDIO_DIR, f)
        if os.path.isfile(f_path):
            if now - os.path.getmtime(f_path) > 600:  # 10 Mins
                try:
                    os.remove(f_path)
                except:
                    pass

scheduler = BackgroundScheduler()
scheduler.add_job(func=cleanup_files, trigger="interval", minutes=10)
scheduler.start()

# --- ROMAN URDU IMPORT ---
try:
    from roman_urdu import roman_urdu_to_urdu_text
    ROMAN_URDU_SUPPORT = True
except ImportError:
    ROMAN_URDU_SUPPORT = False
    print("Roman Urdu module not found. Roman Urdu support disabled.")

# --- ASYNC GENERATOR (EDGE-TTS) ---
async def generate_audio_edge(text, voice, pitch, rate, filename):
    processed_text = text.replace("[pause]", "... ... ... ")
    communicate = edge_tts.Communicate(processed_text, voice, pitch=pitch, rate=rate)
    await communicate.save(os.path.join(AUDIO_DIR, filename))

# --- PIPER GENERATOR ---
def generate_audio_piper(text, voice, speed, filename):
    """Generate audio using Piper TTS server"""
    try:
        response = requests.post(
            f"{PIPER_SERVER_URL}/generate",
            json={
                'text': text,
                'voice': voice,
                'speed': speed
            },
            timeout=30
        )
        
        if response.status_code == 200:
            filepath = os.path.join(AUDIO_DIR, filename)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            return True
    except Exception as e:
        print(f"Piper TTS Error: {e}")
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
        input_type = data.get('input_type', 'normal')  # normal or roman_urdu

        # Validation
        if not text:
            return jsonify({'error': 'Please enter text.'}), 400
        if len(text) > MAX_CHARS:
            return jsonify({'error': 'Text too long.'}), 400

        # Roman Urdu Conversion
        if input_type == 'roman_urdu' and ROMAN_URDU_SUPPORT:
            text = roman_urdu_to_urdu_text(text)

        # Voice Selection
        if TTS_MODE in ['auto', 'piper']:
            voice_config = PIPER_VOICE_MAP.get(lang_code, PIPER_VOICE_MAP['default'])
        else:
            voice_config = EDGE_VOICE_MAP.get(lang_code, EDGE_VOICE_MAP['default'])
        
        if lang_code in ['story', 'horror', 'cartoon', 'news']:
            selected_voice = list(voice_config.values())[0]
        else:
            selected_voice = voice_config.get(gender, voice_config['Male'])

        # Generate filename
        filename = f"audio_{lang_code}_{str(uuid.uuid4())[:8]}"
        
        # Try Piper first if auto or piper mode
        audio_generated = False
        tts_source = 'edge'
        
        if TTS_MODE in ['auto', 'piper']:
            # Piper uses .wav format
            piper_filename = filename + ".wav"
            pitch_str = f"{'+' if pitch_val >= 0 else ''}{pitch_val}Hz"
            rate_str = f"{'+' if speed_val >= 0 else ''}{speed_val}%"
            
            if generate_audio_piper(text, selected_voice, speed_val, piper_filename):
                audio_generated = True
                tts_source = 'piper'
                filename = piper_filename
        
        # Fallback to Edge-TTS
        if not audio_generated and TTS_MODE in ['auto', 'edge']:
            # Edge-TTS uses .mp3 format
            edge_filename = filename + ".mp3"
            pitch_str = f"{'+' if pitch_val >= 0 else ''}{pitch_val}Hz"
            rate_str = f"{'+' if speed_val >= 0 else ''}{speed_val}%"
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    generate_audio_edge(text, selected_voice, pitch_str, rate_str, edge_filename)
                )
                audio_generated = True
                tts_source = 'edge'
                filename = edge_filename
            except Exception as e:
                print(f"Edge-TTS Error: {e}")
            finally:
                loop.close()

        if not audio_generated:
            return jsonify({'error': 'Audio generation failed. Please try again.'}), 500

        return jsonify({
            'success': True,
            'file_url': f"/static/audio/{filename}",
            'filename': filename,
            'source': tts_source,
            'input_type': input_type
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Server error. Please try again.'}), 500

@app.route('/api/status')
def status():
    """Check TTS system status"""
    piper_status = 'unknown'
    try:
        response = requests.get(f"{PIPER_SERVER_URL}/status", timeout=5)
        piper_status = 'online' if response.status_code == 200 else 'offline'
    except:
        piper_status = 'offline'
    
    return jsonify({
        'status': 'online',
        'piper_server': piper_status,
        'tts_mode': TTS_MODE,
        'roman_urdu_support': ROMAN_URDU_SUPPORT,
        'voices_available': list(EDGE_VOICE_MAP.keys())
    })

if __name__ == '__main__':
    # Start Piper server in background thread
    if TTS_MODE in ['auto', 'piper']:
        try:
            from piper_server import start_piper_server
            piper_thread = threading.Thread(target=start_piper_server, daemon=True)
            piper_thread.start()
            print("✅ Piper TTS server started in background")
        except ImportError:
            print("⚠️ Piper server module not found. Using Edge-TTS only.")
            TTS_MODE = 'edge'
    
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

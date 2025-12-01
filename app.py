import os
import uuid
import asyncio
import time
import sys
from flask import Flask, render_template, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import edge_tts

# --- CONFIGURATION ---
app = Flask(__name__)
AUDIO_DIR = os.path.join("static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)
MAX_CHARS = 5000 

# --- VOICE MAP ---
VOICE_MAP = {
    # Local Languages
    'ur': {'Male': 'ur-PK-SalmanNeural', 'Female': 'ur-PK-UzmaNeural'},
    'hi': {'Male': 'hi-IN-MadhurNeural', 'Female': 'hi-IN-SwaraNeural'},
    
    # English Accents
    'en-us': {'Male': 'en-US-GuyNeural', 'Female': 'en-US-JennyNeural'},
    'en-uk': {'Male': 'en-GB-RyanNeural', 'Female': 'en-GB-SoniaNeural'},
    'en-in': {'Male': 'en-IN-PrabhatNeural', 'Female': 'en-IN-NeerjaNeural'},

    # Special Voices
    'story': {'Male': 'en-US-ChristopherNeural'}, 
    'horror': {'Male': 'en-US-EricNeural'},       
    'cartoon': {'Female': 'en-US-AnaNeural'},     
    'news': {'Female': 'en-US-AriaNeural'},       

    # Global
    'ar': {'Male': 'ar-SA-HamedNeural', 'Female': 'ar-SA-ZariyahNeural'},
    'es': {'Male': 'es-ES-AlvaroNeural', 'Female': 'es-ES-ElviraNeural'},
    'fr': {'Male': 'fr-FR-HenriNeural', 'Female': 'fr-FR-DeniseNeural'},

    'default': {'Male': 'en-US-GuyNeural', 'Female': 'en-US-JennyNeural'}
}

# --- CLEANUP TASK ---
def cleanup_files():
    now = time.time()
    for f in os.listdir(AUDIO_DIR):
        f_path = os.path.join(AUDIO_DIR, f)
        if os.path.isfile(f_path):
            if now - os.path.getmtime(f_path) > 600: # 10 Minutes
                try: os.remove(f_path)
                except: pass

scheduler = BackgroundScheduler()
scheduler.add_job(func=cleanup_files, trigger="interval", minutes=10)
scheduler.start()

# --- ASYNC GENERATOR ---
async def generate_audio(text, voice, pitch, rate, filename):
    processed_text = text.replace("[pause]", "... ... ... ")
    communicate = edge_tts.Communicate(processed_text, voice, pitch=pitch, rate=rate)
    await communicate.save(os.path.join(AUDIO_DIR, filename))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.json
        text = data.get('text', '').strip()
        lang_code = data.get('language', 'en-us') 
        gender = data.get('gender', 'Male')
        pitch_val = int(data.get('pitch', 0))
        speed_val = int(data.get('speed', 0))

        if not text: return jsonify({'error': 'Please enter text.'}), 400
        if len(text) > MAX_CHARS: return jsonify({'error': 'Text too long.'}), 400

        # Voice Selection
        lang_config = VOICE_MAP.get(lang_code, VOICE_MAP['default'])
        if lang_code in ['story', 'horror', 'cartoon', 'news']:
            selected_voice = list(lang_config.values())[0]
        else:
            selected_voice = lang_config.get(gender, lang_config['Male'])

        # Parameters
        pitch_str = f"{'+' if pitch_val >= 0 else ''}{pitch_val}Hz"
        rate_str = f"{'+' if speed_val >= 0 else ''}{speed_val}%"
        filename = f"audio_{lang_code}_{str(uuid.uuid4())[:8]}.mp3"

        # Execution Logic (Cross-Platform)
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            asyncio.run(generate_audio(text, selected_voice, pitch_str, rate_str, filename))
        else:
            # Linux/Render ke liye
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(generate_audio(text, selected_voice, pitch_str, rate_str, filename))
            loop.close()

        return jsonify({
            'success': True,
            'file_url': f"/static/audio/{filename}",
            'filename': filename
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Server Busy. Try again.'}), 500

if __name__ == '__main__':
    # Render Gunicorn use karega, lekin local testing k liye ye theek hai
    app.run(debug=True)
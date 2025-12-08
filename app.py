import os
import uuid
import time
import torch
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Config
AUDIO_DIR = os.path.join("static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)
MAX_CHARS = 2000

# Initialize TTS model
tts_model = None
tts_loaded = False

try:
    print("🚀 Loading Coqui TTS (High Quality)...")
    # Use a smaller model that works on Render.com
    from TTS.api import TTS
    tts_model = TTS("tts_models/en/ljspeech/tacotron2-DDC")
    tts_loaded = True
    print("✅ Coqui TTS loaded successfully!")
except Exception as e:
    print(f"⚠️ Coqui TTS not available: {e}")
    tts_loaded = False

# Fallback to pyttsx3 if Coqui fails
import pyttsx3
pyttsx3_engine = pyttsx3.init()
pyttsx3_engine.setProperty('rate', 170)
pyttsx3_engine.setProperty('volume', 1.0)

# Language mapping
LANG_MAP = {
    'en-us': 'en',
    'en-uk': 'en', 
    'en': 'en',
    'hi': 'hi',
    'ur': 'ur',
    'default': 'en'
}

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
        speed_val = int(data.get('speed', 0))

        if not text:
            return jsonify({'error': 'Please enter text.'}), 400
        if len(text) > MAX_CHARS:
            return jsonify({'error': 'Text too long.'}), 400

        lang = LANG_MAP.get(lang_code, LANG_MAP['default'])
        filename = f"audio_{uuid.uuid4().hex[:8]}.wav"
        filepath = os.path.join(AUDIO_DIR, filename)
        
        success = False
        source = 'coqui'
        
        # Try Coqui TTS first (Best quality)
        if tts_loaded and lang == 'en':  # Coqui works best with English
            try:
                tts_model.tts_to_file(text=text, file_path=filepath)
                success = True
            except Exception as e:
                print(f"Coqui TTS error: {e}")
                source = 'pyttsx3'
        
        # Fallback to pyttsx3
        if not success:
            try:
                # Set voice gender
                voices = pyttsx3_engine.getProperty('voices')
                if gender == 'Female':
                    for voice in voices:
                        if 'female' in voice.name.lower():
                            pyttsx3_engine.setProperty('voice', voice.id)
                            break
                
                # Adjust speed
                rate = 170 + (speed_val * 2)
                pyttsx3_engine.setProperty('rate', max(100, min(300, rate)))
                
                # Convert .wav to .mp3 filename for pyttsx3
                mp3_file = filepath.replace('.wav', '.mp3')
                pyttsx3_engine.save_to_file(text, mp3_file)
                pyttsx3_engine.runAndWait()
                
                # Rename to .wav for consistency
                if os.path.exists(mp3_file):
                    os.rename(mp3_file, filepath)
                    success = True
                    
            except Exception as e:
                print(f"pyttsx3 error: {e}")
        
        if success:
            return jsonify({
                'success': True,
                'file_url': f"/static/audio/{filename}",
                'filename': filename,
                'source': source,
                'quality': 'high' if source == 'coqui' else 'medium'
            })
        else:
            return jsonify({'error': 'Audio generation failed.'}), 500
            
    except Exception as e:
        print(f"Server error: {e}")
        return jsonify({'error': 'Server error.'}), 500

@app.route('/api/status')
def status():
    return jsonify({
        'status': 'online',
        'coqui_loaded': tts_loaded,
        'pyttsx3_ready': True,
        'quality': 'high' if tts_loaded else 'medium',
        'languages': list(LANG_MAP.keys()),
        'free': True
    })

if __name__ == '__main__':
    print("🎯 High Quality TTS Server")
    print("🔊 Primary: Coqui TTS (Studio Quality)")
    print("🔄 Fallback: pyttsx3 (System Voices)")
    print("🌍 Languages: Multiple")
    print("💰 Cost: 100% FREE")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

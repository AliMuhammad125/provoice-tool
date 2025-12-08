import os
import uuid
import time
from flask import Flask, render_template, request, jsonify
from gtts import gTTS
import pyttsx3

app = Flask(__name__)

# Config
AUDIO_DIR = os.path.join("static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)
MAX_CHARS = 5000

print("🚀 Starting Google TTS + pyttsx3 Server...")

# Initialize pyttsx3 for offline fallback
pyttsx3_engine = pyttsx3.init()
pyttsx3_engine.setProperty('rate', 170)
pyttsx3_engine.setProperty('volume', 1.0)

# Language mapping
LANG_MAP = {
    'en-us': 'en',
    'en-uk': 'en',
    'en': 'en',
    'hi': 'hi',  # Hindi - Google TTS works!
    'ur': 'ur',  # Urdu - Google TTS works!
    'ar': 'ar',  # Arabic
    'es': 'es',  # Spanish
    'fr': 'fr',  # French
    'default': 'en'
}

# Routes
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
        
        if not text:
            return jsonify({'error': 'Please enter text.'}), 400
        
        if len(text) > MAX_CHARS:
            return jsonify({'error': 'Text too long.'}), 400
        
        # Get language
        lang = LANG_MAP.get(lang_code, 'en')
        
        filename = f"audio_{uuid.uuid4().hex[:8]}.mp3"
        filepath = os.path.join(AUDIO_DIR, filename)
        
        # ALWAYS use Google TTS (Best quality)
        try:
            # Google TTS generation
            tts = gTTS(
                text=text,
                lang=lang,
                slow=False,  # Normal speed
                lang_check=False  # Allow any language
            )
            tts.save(filepath)
            source = 'google_tts'
            quality = 'excellent'
            
        except Exception as e:
            print(f"Google TTS failed: {e}")
            
            # Fallback to pyttsx3 (only for English)
            if lang == 'en':
                pyttsx3_engine.save_to_file(text, filepath)
                pyttsx3_engine.runAndWait()
                source = 'pyttsx3'
                quality = 'good'
            else:
                return jsonify({'error': 'Language not supported in fallback.'}), 500
        
        return jsonify({
            'success': True,
            'file_url': f"/static/audio/{filename}",
            'filename': filename,
            'source': source,
            'quality': quality,
            'language': lang
        })
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Server error.'}), 500

@app.route('/api/status')
def status():
    return jsonify({
        'status': 'online',
        'primary': 'Google TTS (Best Quality)',
        'fallback': 'pyttsx3 (English only)',
        'languages': list(LANG_MAP.keys()),
        'quality': 'excellent',
        'free': True
    })

if __name__ == '__main__':
    print("🎯 Google TTS Server Started")
    print("🔊 Primary: Google TTS (Excellent Quality)")
    print("🔄 Fallback: pyttsx3 (English only)")
    print("🌍 Languages: English, Hindi, Urdu, Arabic, Spanish, French")
    print("💰 Cost: 100% FREE")
    print("🎵 Quality: EXCELLENT (Google grade)")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

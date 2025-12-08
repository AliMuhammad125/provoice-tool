import os
import uuid
import time
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Config
AUDIO_DIR = os.path.join("static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)
MAX_CHARS = 3000

# Initialize Coqui TTS
print("🚀 Initializing Coqui TTS...")

try:
    # Try to import Coqui TTS
    from TTS.api import TTS
    tts_engine = TTS("tts_models/en/ljspeech/tacotron2-DDC")
    TTS_AVAILABLE = True
    print("✅ Coqui TTS loaded successfully!")
    
except ImportError:
    print("❌ Coqui TTS not installed. Using fallback.")
    TTS_AVAILABLE = False
    tts_engine = None

# Fallback: pyttsx3
if not TTS_AVAILABLE:
    try:
        import pyttsx3
        fallback_engine = pyttsx3.init()
        fallback_engine.setProperty('rate', 170)
        fallback_engine.setProperty('volume', 1.0)
        print("✅ pyttsx3 fallback loaded")
    except:
        fallback_engine = None
        print("❌ No TTS engine available")

# Language mapping
LANG_MAP = {
    'en-us': 'en',
    'en-uk': 'en', 
    'en': 'en',
    'hi': 'hi',  # Hindi
    'ur': 'ur',  # Urdu
    'es': 'es',
    'fr': 'fr',
    'ar': 'ar'
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
        speed = int(data.get('speed', 0))

        # Validation
        if not text:
            return jsonify({'error': 'Please enter text.'}), 400
        
        if len(text) > MAX_CHARS:
            return jsonify({'error': f'Text too long. Max {MAX_CHARS} characters.'}), 400

        # Get language
        lang = LANG_MAP.get(lang_code, 'en')
        
        # Generate filename
        filename = f"audio_{uuid.uuid4().hex[:8]}.wav"
        filepath = os.path.join(AUDIO_DIR, filename)
        
        # Try Coqui TTS first (Best quality)
        if TTS_AVAILABLE and tts_engine and lang == 'en':
            try:
                # Generate with Coqui TTS
                tts_engine.tts_to_file(text=text, file_path=filepath)
                source = 'coqui_tts'
                quality = 'high'
                
            except Exception as e:
                print(f"Coqui TTS error: {e}")
                # Fallback
                if 'fallback_engine' in locals():
                    fallback_engine.save_to_file(text, filepath.replace('.wav', '.mp3'))
                    fallback_engine.runAndWait()
                    source = 'pyttsx3'
                    quality = 'medium'
                    # Rename to .wav
                    mp3_file = filepath.replace('.wav', '.mp3')
                    if os.path.exists(mp3_file):
                        os.rename(mp3_file, filepath)
                else:
                    return jsonify({'error': 'TTS engine failed.'}), 500
                    
        else:
            # Use fallback
            if 'fallback_engine' in locals():
                fallback_engine.save_to_file(text, filepath.replace('.wav', '.mp3'))
                fallback_engine.runAndWait()
                source = 'pyttsx3'
                quality = 'medium'
                # Rename to .wav
                mp3_file = filepath.replace('.wav', '.mp3')
                if os.path.exists(mp3_file):
                    os.rename(mp3_file, filepath)
            else:
                return jsonify({'error': 'No TTS engine available.'}), 500

        # Check if file was created
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            return jsonify({
                'success': True,
                'file_url': f"/static/audio/{filename}",
                'filename': filename,
                'source': source,
                'quality': quality,
                'language': lang
            })
        else:
            return jsonify({'error': 'Audio file not created.'}), 500
            
    except Exception as e:
        print(f"Server error: {e}")
        return jsonify({'error': 'Server error. Please try again.'}), 500

@app.route('/api/status')
def status():
    return jsonify({
        'status': 'online',
        'coqui_tts': TTS_AVAILABLE,
        'fallback_engine': 'pyttsx3' if 'fallback_engine' in locals() else 'none',
        'languages': list(LANG_MAP.keys()),
        'max_chars': MAX_CHARS,
        'free': True,
        'quality': 'high' if TTS_AVAILABLE else 'medium'
    })

@app.route('/test')
def test():
    return jsonify({
        'status': 'ok',
        'coqui_tts': TTS_AVAILABLE,
        'audio_dir': os.path.exists(AUDIO_DIR)
    })

if __name__ == '__main__':
    print("🎯 Coqui TTS Server")
    print(f"🔊 Coqui TTS: {'✅ Available' if TTS_AVAILABLE else '❌ Not available'}")
    print(f"🔄 Fallback: pyttsx3")
    print(f"🌍 Languages: {len(LANG_MAP)}")
    print(f"💰 Cost: 100% FREE")
    print(f"🎵 Quality: {'High' if TTS_AVAILABLE else 'Medium'}")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

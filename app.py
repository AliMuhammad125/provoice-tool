import os
import uuid
import time
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Config
AUDIO_DIR = os.path.join("static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)
MAX_CHARS = 3000

print("🚀 Starting Coqui TTS Server...")

# Load Coqui TTS
tts_engine = None
try:
    from TTS.api import TTS
    print("📦 Loading Coqui TTS model (please wait 3-5 minutes)...")
    
    # Use a small but high-quality model
    tts_engine = TTS(model_name="tts_models/en/ljspeech/glow-tts")
    print("✅ Coqui TTS loaded successfully!")
    print(f"🎵 Model: glow-tts (High Quality)")
    
except Exception as e:
    print(f"❌ Coqui TTS load failed: {e}")
    print("⚠️ Using fallback mode")
    tts_engine = None

# Fallback if Coqui fails
if not tts_engine:
    try:
        import pyttsx3
        fallback_engine = pyttsx3.init()
        fallback_engine.setProperty('rate', 170)
        fallback_engine.setProperty('volume', 1.0)
        print("✅ Fallback engine: pyttsx3 loaded")
    except:
        fallback_engine = None
        print("❌ No TTS engine available")

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
        lang = data.get('language', 'en')
        
        if not text:
            return jsonify({'error': 'Please enter text.'}), 400
        
        if len(text) > MAX_CHARS:
            return jsonify({'error': f'Text too long. Max {MAX_CHARS} characters.'}), 400
        
        filename = f"audio_{uuid.uuid4().hex[:8]}.wav"
        filepath = os.path.join(AUDIO_DIR, filename)
        
        # Try Coqui TTS first (BEST QUALITY)
        if tts_engine:
            try:
                tts_engine.tts_to_file(text=text, file_path=filepath)
                quality = 'excellent'
                engine = 'coqui_tts'
            except Exception as e:
                print(f"Coqui error: {e}")
                if 'fallback_engine' in locals() and fallback_engine:
                    fallback_engine.save_to_file(text, filepath)
                    fallback_engine.runAndWait()
                    quality = 'good'
                    engine = 'pyttsx3'
                else:
                    return jsonify({'error': 'TTS engine failed.'}), 500
        else:
            if 'fallback_engine' in locals() and fallback_engine:
                fallback_engine.save_to_file(text, filepath)
                fallback_engine.runAndWait()
                quality = 'good'
                engine = 'pyttsx3'
            else:
                return jsonify({'error': 'No TTS engine available.'}), 500
        
        return jsonify({
            'success': True,
            'file_url': f"/static/audio/{filename}",
            'filename': filename,
            'quality': quality,
            'engine': engine
        })
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Server error.'}), 500

@app.route('/api/status')
def status():
    return jsonify({
        'status': 'online',
        'coqui_loaded': tts_engine is not None,
        'fallback_available': 'fallback_engine' in locals(),
        'quality': 'excellent' if tts_engine else 'good',
        'free': True,
        'unlimited': True
    })

@app.route('/test')
def test():
    return jsonify({
        'status': 'ok',
        'coqui': tts_engine is not None,
        'timestamp': time.time()
    })

if __name__ == '__main__':
    print("🎯 Coqui TTS Server Started")
    print("🔊 Quality: Excellent (Studio Grade)")
    print("💰 Cost: 100% FREE")
    print("♾️ Limits: UNLIMITED")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

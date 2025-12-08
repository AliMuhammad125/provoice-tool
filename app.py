import os
import uuid
import time
import torch
from flask import Flask, render_template, request, jsonify
import numpy as np
from scipy.io.wavfile import write as write_wav

app = Flask(__name__)

# Config
AUDIO_DIR = os.path.join("static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)
MAX_CHARS = 500

print("🚀 Loading Bark TTS (Best Quality Free)...")

# Try to load Bark TTS
bark_model = None
try:
    from bark import SAMPLE_RATE, generate_audio, preload_models
    import numpy as np
    
    # Preload models (first time only)
    print("📦 Downloading Bark models (first time, ~5-10 minutes)...")
    preload_models()
    
    bark_model = {
        'generate_audio': generate_audio,
        'SAMPLE_RATE': SAMPLE_RATE
    }
    
    print("✅ Bark TTS loaded successfully!")
    print("🎵 Quality: EXCELLENT (Better than Edge-TTS)")
    print("💰 Cost: 100% FREE")
    print("♾️ Limits: NONE")
    
except Exception as e:
    print(f"❌ Bark TTS load failed: {e}")
    bark_model = None

# Fallback: pyttsx3
if not bark_model:
    try:
        import pyttsx3
        fallback_engine = pyttsx3.init()
        fallback_engine.setProperty('rate', 170)
        print("✅ Fallback: pyttsx3 loaded")
    except:
        fallback_engine = None

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.json
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'error': 'Please enter text.'}), 400
        
        if len(text) > MAX_CHARS:
            return jsonify({'error': f'Text too long. Max {MAX_CHARS} characters.'}), 400
        
        filename = f"audio_{uuid.uuid4().hex[:8]}.wav"
        filepath = os.path.join(AUDIO_DIR, filename)
        
        # Try Bark TTS first (EXCELLENT QUALITY)
        if bark_model:
            try:
                # Generate with Bark
                audio_array = bark_model['generate_audio'](
                    text,
                    history_prompt="v2/en_speaker_6"  # Professional voice
                )
                
                # Save as WAV
                write_wav(
                    filepath,
                    bark_model['SAMPLE_RATE'],
                    audio_array
                )
                
                return jsonify({
                    'success': True,
                    'file_url': f"/static/audio/{filename}",
                    'filename': filename,
                    'quality': 'excellent',
                    'engine': 'bark_tts'
                })
                
            except Exception as e:
                print(f"Bark TTS error: {e}")
        
        # Fallback to pyttsx3
        if 'fallback_engine' in locals() and fallback_engine:
            try:
                fallback_engine.save_to_file(text, filepath)
                fallback_engine.runAndWait()
                
                return jsonify({
                    'success': True,
                    'file_url': f"/static/audio/{filename}",
                    'filename': filename,
                    'quality': 'good',
                    'engine': 'pyttsx3'
                })
            except:
                pass
        
        return jsonify({'error': 'All TTS engines failed.'}), 500
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Server error.'}), 500

@app.route('/api/status')
def status():
    return jsonify({
        'status': 'online',
        'bark_tts': bark_model is not None,
        'fallback': 'fallback_engine' in locals(),
        'quality': 'excellent' if bark_model else 'good',
        'max_chars': MAX_CHARS,
        'free': True,
        'unlimited': True
    })

if __name__ == '__main__':
    print("🎯 Bark TTS Server Started")
    print("🔊 Quality: EXCELLENT (Best Free)")
    print("🌍 Supports: English + Emotions + Sound effects")
    print("⚠️ Note: First request may take 30-60 seconds")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

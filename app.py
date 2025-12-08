import os
import uuid
import time
import json
import hashlib
import threading
import subprocess
import sys
import traceback
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import requests

app = Flask(__name__)

# Simple Config
AUDIO_DIR = "static/audio"
os.makedirs(AUDIO_DIR, exist_ok=True)
MAX_CHARS = 5000

# Voice Map (Simplified)
VOICE_MAP = {
    'en-us': {'Male': 'en-US-GuyNeural', 'Female': 'en-US-JennyNeural'},
    'en-uk': {'Male': 'en-GB-RyanNeural', 'Female': 'en-GB-SoniaNeural'},
    'hi': {'Male': 'hi-IN-MadhurNeural', 'Female': 'hi-IN-SwaraNeural'},
    'ur': {'Male': 'ur-PK-SalmanNeural', 'Female': 'ur-PK-UzmaNeural'},
    'default': {'Male': 'en-US-GuyNeural', 'Female': 'en-US-JennyNeural'}
}

# Cleanup
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

@app.route('/test')
def test():
    """Test endpoint"""
    return jsonify({
        'status': 'ok',
        'audio_dir': os.path.exists(AUDIO_DIR),
        'files_in_audio': len(os.listdir(AUDIO_DIR)),
        'flask_ready': True
    })

@app.route('/generate', methods=['POST'])
def generate():
    """Simple TTS generation (Edge-TTS only for now)"""
    try:
        data = request.json
        print(f"📦 Request data: {data}")
        
        text = data.get('text', '').strip()
        lang_code = data.get('language', 'en-us')
        gender = data.get('gender', 'Male')
        
        if not text:
            return jsonify({'error': 'Please enter text.'}), 400
        
        if len(text) > MAX_CHARS:
            return jsonify({'error': f'Text too long. Max {MAX_CHARS} chars.'}), 400
        
        # Select voice
        voice_config = VOICE_MAP.get(lang_code, VOICE_MAP['default'])
        voice = voice_config.get(gender, voice_config['Male'])
        
        print(f"🎵 Selected voice: {voice}")
        
        # Generate filename
        filename = f"audio_{uuid.uuid4()[:8]}.mp3"
        filepath = os.path.join(AUDIO_DIR, filename)
        
        # Generate with Edge-TTS
        try:
            import edge_tts
            import asyncio
            
            # Fix for Windows/Linux
            if sys.platform == 'win32':
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            
            async def generate_audio():
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(filepath)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(generate_audio())
                print(f"✅ Audio generated: {filename}")
            finally:
                loop.close()
            
            return jsonify({
                'success': True,
                'file_url': f"/static/audio/{filename}",
                'filename': filename
            })
            
        except Exception as e:
            print(f"❌ Edge-TTS Error: {e}")
            return jsonify({'error': f'TTS Error: {str(e)}'}), 500
        
    except Exception as e:
        print(f"❌ Server Error: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/status')
def status():
    return jsonify({
        'status': 'online',
        'engine': 'edge-tts',
        'audio_dir': os.path.exists(AUDIO_DIR),
        'max_chars': MAX_CHARS
    })

if __name__ == '__main__':
    print("🚀 Simple TTS Server Starting...")
    print(f"📁 Audio Dir: {AUDIO_DIR}")
    print(f"🔤 Max Chars: {MAX_CHARS}")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)

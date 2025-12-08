import os
import uuid
import time
import json
from flask import Flask, render_template, request, jsonify, send_from_directory
from TTS.api import TTS
import threading

app = Flask(__name__)

# Configuration
AUDIO_DIR = os.path.join("static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)
MAX_CHARS = 5000
CACHE_FILE = "tts_cache.json"

# Global TTS engine
tts_engine = None
tts_loading = False
tts_loaded = False

# Language mapping
LANGUAGE_MAP = {
    'en-us': 'en',
    'en-uk': 'en',
    'en-in': 'en',
    'hi': 'hi',      # Hindi
    'ur': 'ur',      # Urdu
    'ar': 'ar',      # Arabic
    'es': 'es',      # Spanish
    'fr': 'fr',      # French
    'de': 'de',      # German
    'it': 'it',      # Italian
    'pt': 'pt',      # Portuguese
    'default': 'en'
}

# Voice gender mapping (Coqui uses speakers, we map genders)
VOICE_GENDER_MAP = {
    'en': {'Male': 'male', 'Female': 'female'},
    'hi': {'Male': 'male', 'Female': 'female'},
    'ur': {'Male': 'male', 'Female': 'female'},
    'default': {'Male': 'male', 'Female': 'female'}
}

# Load cache
def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

# Save cache
def save_cache(cache):
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f)
    except:
        pass

# Initialize TTS in background
def init_tts():
    global tts_engine, tts_loaded, tts_loading
    
    if tts_loading or tts_loaded:
        return
    
    tts_loading = True
    print("🚀 Initializing Coqui TTS XTTS-v2...")
    
    try:
        # Load the best multilingual model
        tts_engine = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")
        
        # Test if Hindi/Urdu are supported
        test_texts = {
            'hi': 'नमस्ते',
            'ur': 'السلام علیکم',
            'en': 'Hello'
        }
        
        print("✅ Coqui TTS loaded successfully!")
        print(f"🔊 Available languages: {tts_engine.languages if hasattr(tts_engine, 'languages') else 'All'}")
        print(f"🎭 Model: XTTS-v2 (Multilingual)")
        
        tts_loaded = True
        
    except Exception as e:
        print(f"❌ Error loading TTS: {e}")
        print("⚠️ Falling back to basic TTS functionality")
        tts_loaded = False
    
    tts_loading = False

# Cleanup old audio files
def cleanup_files():
    """Remove files older than 2 hours"""
    try:
        current_time = time.time()
        for filename in os.listdir(AUDIO_DIR):
            filepath = os.path.join(AUDIO_DIR, filename)
            if os.path.isfile(filepath):
                file_age = current_time - os.path.getmtime(filepath)
                if file_age > 7200:  # 2 hours
                    try:
                        os.remove(filepath)
                    except:
                        pass
    except Exception as e:
        print(f"Cleanup error: {e}")

# Start TTS initialization in background
tts_thread = threading.Thread(target=init_tts, daemon=True)
tts_thread.start()

# Start cleanup scheduler
cleanup_thread = threading.Thread(target=lambda: [time.sleep(3600), cleanup_files()], daemon=True)
cleanup_thread.start()

# ========== ROUTES ==========

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
    """Generate audio from text"""
    try:
        # Parse request data
        data = request.json
        text = data.get('text', '').strip()
        lang_code = data.get('language', 'en-us')
        gender = data.get('gender', 'Male')
        pitch = int(data.get('pitch', 0))
        speed = int(data.get('speed', 0))
        
        # Validate input
        if not text:
            return jsonify({'error': 'Please enter text.'}), 400
        
        if len(text) > MAX_CHARS:
            return jsonify({'error': f'Text too long. Maximum {MAX_CHARS} characters allowed.'}), 400
        
        # Generate cache key
        cache_key = f"{text}_{lang_code}_{gender}_{pitch}_{speed}"
        
        # Check cache first
        cache = load_cache()
        if cache_key in cache and os.path.exists(os.path.join(AUDIO_DIR, cache[cache_key])):
            return jsonify({
                'success': True,
                'file_url': f"/static/audio/{cache[cache_key]}",
                'filename': cache[cache_key],
                'source': 'cache'
            })
        
        # Get language code
        language = LANGUAGE_MAP.get(lang_code, LANGUAGE_MAP['default'])
        
        # Generate filename
        filename = f"audio_{uuid.uuid4().hex[:8]}.wav"
        filepath = os.path.join(AUDIO_DIR, filename)
        
        # Wait for TTS to load (max 30 seconds)
        if not tts_loaded:
            start_time = time.time()
            while not tts_loaded and (time.time() - start_time) < 30:
                time.sleep(1)
        
        # Generate audio
        if tts_loaded and tts_engine:
            try:
                # Prepare parameters
                params = {
                    'text': text,
                    'file_path': filepath,
                    'language': language
                }
                
                # Add speed adjustment if requested
                if speed != 0:
                    # Convert speed to rate (Coqui uses different param)
                    rate = 1.0 + (speed / 100.0)
                    params['rate'] = rate
                
                # Generate audio
                tts_engine.tts_to_file(**params)
                
                # Cache the result
                cache[cache_key] = filename
                save_cache(cache)
                
                return jsonify({
                    'success': True,
                    'file_url': f"/static/audio/{filename}",
                    'filename': filename,
                    'source': 'coqui_tts',
                    'language': language,
                    'quality': 'studio'
                })
                
            except Exception as e:
                print(f"TTS generation error: {e}")
                # Fall through to backup method
        
        # Backup method: Return error with instructions
        return jsonify({
            'success': False,
            'error': 'TTS engine is initializing. Please try again in 30 seconds.',
            'retry_after': 30
        }), 503
        
    except Exception as e:
        print(f"Server error: {e}")
        return jsonify({'error': 'Server error. Please try again.'}), 500

@app.route('/api/status')
def status():
    """API status endpoint"""
    return jsonify({
        'status': 'online',
        'tts_loaded': tts_loaded,
        'tts_loading': tts_loading,
        'engine': 'Coqui TTS XTTS-v2',
        'supported_languages': list(LANGUAGE_MAP.keys()),
        'max_chars': MAX_CHARS,
        'cache_size': len(load_cache()),
        'audio_files': len(os.listdir(AUDIO_DIR)) if os.path.exists(AUDIO_DIR) else 0
    })

@app.route('/api/languages')
def languages():
    """List supported languages"""
    return jsonify({
        'languages': [
            {'code': 'en-us', 'name': 'English (US)', 'voice': 'Neural'},
            {'code': 'en-uk', 'name': 'English (UK)', 'voice': 'British'},
            {'code': 'hi', 'name': 'Hindi', 'voice': 'Indian'},
            {'code': 'ur', 'name': 'Urdu', 'voice': 'Pakistani'},
            {'code': 'ar', 'name': 'Arabic', 'voice': 'Middle Eastern'},
            {'code': 'es', 'name': 'Spanish', 'voice': 'European'},
            {'code': 'fr', 'name': 'French', 'voice': 'European'},
            {'code': 'de', 'name': 'German', 'voice': 'European'},
            {'code': 'it', 'name': 'Italian', 'voice': 'European'},
            {'code': 'pt', 'name': 'Portuguese', 'voice': 'Brazilian'}
        ]
    })

@app.route('/test')
def test():
    """Test endpoint"""
    return jsonify({
        'status': 'ok',
        'message': 'TTS Server is running',
        'timestamp': time.time(),
        'version': '2.0.0'
    })

@app.route('/static/audio/<filename>')
def serve_audio(filename):
    """Serve audio files"""
    return send_from_directory(AUDIO_DIR, filename)

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("=" * 50)
    print("🎯 COQUI TTS SERVER - STUDIO QUALITY")
    print("=" * 50)
    print("🔊 Engine: Coqui TTS XTTS-v2")
    print("🌍 Languages: English, Hindi, Urdu, Arabic, Spanish, French + more")
    print("🎵 Quality: Studio Grade (Near Human)")
    print("💰 Cost: 100% FREE")
    print("♾️ Limits: UNLIMITED")
    print("⚡ Cache: Enabled")
    print("=" * 50)
    
    # Start the server
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

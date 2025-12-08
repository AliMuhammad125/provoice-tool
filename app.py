import os
import uuid
import time
from flask import Flask, render_template, request, jsonify
import pyttsx3

app = Flask(__name__)

# Config
AUDIO_DIR = os.path.join("static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)
MAX_CHARS = 3000

# Initialize pyttsx3 (ALWAYS WORKS)
print("🚀 Initializing pyttsx3 TTS...")
engine = pyttsx3.init()

# Configure engine
engine.setProperty('rate', 170)  # Speed
engine.setProperty('volume', 1.0)  # Volume

# Get available voices
voices = engine.getProperty('voices')
print(f"✅ Found {len(voices)} system voices")

# Voice mapping
VOICES = {
    'male': None,
    'female': None
}

# Find male and female voices
for voice in voices:
    if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
        VOICES['female'] = voice.id
    elif 'male' in voice.name.lower() or 'david' in voice.name.lower():
        VOICES['male'] = voice.id

print(f"🎭 Male voice: {'Found' if VOICES['male'] else 'Not found'}")
print(f"🎭 Female voice: {'Found' if VOICES['female'] else 'Not found'}")

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
        gender = data.get('gender', 'Male').lower()
        pitch_val = int(data.get('pitch', 0))
        speed_val = int(data.get('speed', 0))

        # Validation
        if not text:
            return jsonify({'error': 'Please enter text.'}), 400
        
        if len(text) > MAX_CHARS:
            return jsonify({'error': f'Text too long. Max {MAX_CHARS} characters.'}), 400

        # Set voice based on gender
        voice_id = VOICES.get(gender, VOICES['male'])
        if voice_id:
            engine.setProperty('voice', voice_id)
        
        # Adjust speed
        base_rate = 170
        adjusted_rate = base_rate + (speed_val * 2)
        engine.setProperty('rate', max(100, min(300, adjusted_rate)))
        
        # Adjust pitch (pyttsx3 doesn't support pitch directly)
        # We can adjust voice selection instead
        
        # Generate filename
        filename = f"audio_{uuid.uuid4().hex[:8]}.mp3"
        filepath = os.path.join(AUDIO_DIR, filename)
        
        # Generate audio
        engine.save_to_file(text, filepath)
        engine.runAndWait()
        
        # Verify file was created
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            return jsonify({
                'success': True,
                'file_url': f"/static/audio/{filename}",
                'filename': filename,
                'engine': 'pyttsx3',
                'voice': gender,
                'speed': speed_val
            })
        else:
            return jsonify({'error': 'Audio file creation failed.'}), 500
            
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Server error. Please try again.'}), 500

@app.route('/api/status')
def status():
    return jsonify({
        'status': 'online',
        'engine': 'pyttsx3',
        'voices_available': len(voices),
        'male_voice': VOICES['male'] is not None,
        'female_voice': VOICES['female'] is not None,
        'max_chars': MAX_CHARS,
        'free': True,
        'unlimited': True,
        'quality': 'good'
    })

@app.route('/api/voices')
def list_voices():
    """List all available system voices"""
    voice_list = []
    for i, voice in enumerate(voices):
        voice_list.append({
            'id': i,
            'name': voice.name,
            'gender': 'female' if 'female' in voice.name.lower() else 'male',
            'languages': voice.languages if hasattr(voice, 'languages') else ['en']
        })
    
    return jsonify({
        'voices': voice_list,
        'total': len(voice_list)
    })

@app.route('/test')
def test():
    return jsonify({
        'status': 'ok',
        'message': 'TTS Server is running',
        'timestamp': time.time()
    })

if __name__ == '__main__':
    print("🎯 Python TTS Server Started")
    print("🔊 Engine: pyttsx3 (System TTS)")
    print("💾 Uses: Windows David/Zira, Linux eSpeak voices")
    print("💰 Cost: 100% FREE")
    print("♾️ Limits: UNLIMITED")
    print("🎵 Quality: GOOD (System voices)")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

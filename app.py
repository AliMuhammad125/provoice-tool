import os
import uuid
import time
import subprocess
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Config
AUDIO_DIR = os.path.join("static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)
MAX_CHARS = 5000

# Voice Options
VOICES = {
    'en-us': 'en_US-lessac-medium',
    'en-uk': 'en_GB-semaine-medium', 
    'hi': 'hi_IN-medium',
    'ur': 'ur_PK-medium',
    'story': 'en_US-lessac-medium',
    'horror': 'en_US-vctk-medium',
    'cartoon': 'en_US-hfc_male-medium',
    'news': 'en_GB-semaine-medium'
}

# Direct Piper Function
def generate_with_piper(text, voice_model, output_file):
    """Generate audio directly using Piper command"""
    try:
        # Build command
        cmd = [
            'python', '-m', 'piper',
            '--model', f'voices/{voice_model}.onnx',
            '--output_file', output_file
        ]
        
        # Run Piper
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Send text and wait
        stdout, stderr = process.communicate(input=text)
        
        if process.returncode == 0:
            return True
        else:
            print(f"Piper error: {stderr}")
            return False
            
    except Exception as e:
        print(f"Piper execution error: {e}")
        return False

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
        
        if not text:
            return jsonify({'error': 'No text'}), 400
        
        if len(text) > MAX_CHARS:
            return jsonify({'error': 'Text too long'}), 400
        
        # Get voice model
        voice_model = VOICES.get(lang_code, VOICES['en-us'])
        
        # Generate filename
        filename = f"audio_{uuid.uuid4().hex[:8]}.wav"
        filepath = os.path.join(AUDIO_DIR, filename)
        
        # Generate with Piper
        success = generate_with_piper(text, voice_model, filepath)
        
        if success and os.path.exists(filepath):
            return jsonify({
                'success': True,
                'file_url': f'/static/audio/{filename}',
                'filename': filename,
                'engine': 'piper'
            })
        else:
            return jsonify({'error': 'Audio generation failed'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status')
def status():
    return jsonify({
        'status': 'online',
        'engine': 'Piper TTS (Direct)',
        'voices': list(VOICES.keys())
    })

if __name__ == '__main__':
    print("🚀 Piper TTS Server (Direct Mode)")
    print("🔊 No HTTP server, direct generation")
    print("💰 100% FREE, Unlimited")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

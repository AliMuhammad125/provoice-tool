import os
import uuid
import torch
import time
from flask import Flask, render_template, request, jsonify
from TTS.api import TTS
import threading

app = Flask(__name__)

AUDIO_DIR = "static/audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# Available Models (Choose one)
MODELS = {
    "high_quality": "tts_models/en/ljspeech/tacotron2-DDC",
    "fast": "tts_models/en/ljspeech/glow-tts",
    "multilingual": "tts_models/multilingual/multi-dataset/your_tts",
    "best_quality": "tts_models/en/ljspeech/tortoise-v2"  # SLOW but BEST
}

# Initialize TTS in background
tts_engine = None
tts_ready = False

def load_tts():
    """Load TTS model in background"""
    global tts_engine, tts_ready
    try:
        print("🚀 Loading Coqui TTS (may take 2-3 minutes)...")
        
        # Use CUDA if available, else CPU
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🔧 Using device: {device}")
        
        # Load model (fast quality for speed)
        tts_engine = TTS(model_name=MODELS["fast"]).to(device)
        
        tts_ready = True
        print("✅ Coqui TTS loaded successfully!")
        print(f"🎵 Available speakers: {tts_engine.speakers}")
        
    except Exception as e:
        print(f"❌ Error loading TTS: {e}")
        tts_ready = False

# Start loading TTS
tts_thread = threading.Thread(target=load_tts, daemon=True)
tts_thread.start()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.json
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'error': 'Please enter text'}), 400
        
        if len(text) > 1000:
            return jsonify({'error': 'Text too long (max 1000 chars)'}), 400
        
        # Wait for TTS to load (max 30 seconds)
        start_time = time.time()
        while not tts_ready and (time.time() - start_time) < 30:
            time.sleep(1)
        
        if not tts_ready:
            return jsonify({'error': 'TTS engine still loading. Try in 30 seconds.'}), 503
        
        # Generate audio
        filename = f"audio_{uuid.uuid4().hex[:8]}.wav"
        filepath = os.path.join(AUDIO_DIR, filename)
        
        try:
            # Generate with Coqui TTS
            tts_engine.tts_to_file(
                text=text,
                file_path=filepath,
                speaker=tts_engine.speakers[0] if tts_engine.speakers else None,
                language="en"
            )
            
            # Convert to mp3 if needed
            if filepath.endswith('.wav'):
                mp3_path = filepath.replace('.wav', '.mp3')
                os.system(f"ffmpeg -i {filepath} -y {mp3_path} 2>/dev/null")
                if os.path.exists(mp3_path):
                    filename = filename.replace('.wav', '.mp3')
                    os.remove(filepath)
            
            return jsonify({
                'success': True,
                'file_url': f'/static/audio/{filename}',
                'filename': filename,
                'quality': 'coqui_tts'
            })
            
        except Exception as e:
            print(f"TTS Generation Error: {e}")
            return jsonify({'error': 'Audio generation failed'}), 500
            
    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({'error': 'Server error'}), 500

@app.route('/status')
def status():
    return jsonify({
        'status': 'online',
        'tts_ready': tts_ready,
        'engine': 'Coqui TTS',
        'quality': 'studio',
        'free': True,
        'unlimited': True
    })

if __name__ == '__main__':
    print("🎯 Starting BEST QUALITY TTS Server")
    print("🔊 Engine: Coqui TTS (Studio Quality)")
    print("💰 Cost: FREE FOREVER")
    print("♾️ Limits: NONE")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

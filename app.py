from flask import Flask, request, Response, jsonify, render_template_string
import requests
import io
import logging
import os
import time
from functools import wraps

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Hugging Face API token
HF_TOKEN = os.environ.get('HUGGING_FACE_TOKEN')
if not HF_TOKEN:
    logger.error("❌ HUGGING_FACE_TOKEN environment variable not set!")
    HF_TOKEN = "MISSING_TOKEN"

logger.info(f"✅ HUGGING_FACE_TOKEN loaded: {HF_TOKEN[:5]}...{HF_TOKEN[-5:] if len(HF_TOKEN) > 10 else ''}")

# ✅ NEW MODELS - Recently Updated (from your screenshot)
NEW_TTS_MODELS = {
    'moss-tts': 'OpenMOSS-Team/MOSS-TTS',                    # 8B model - High quality
    'soulx-singer': 'Soul-AILab/SoulX-Singer',                # Singer model
    'kugelaudio': 'kugelaudio/kugelaudio-0-open',            # Open audio model
    'qwen3-tts': 'Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice',     # 1.7B model
    'kani-tts': 'nininenixi/kani-tts-2-en',                  # 0.4B - Fast
}

# Backup models (just in case)
BACKUP_MODELS = {
    'bark': 'suno/bark',
    'bark-small': 'suno/bark-small',
}

# Combine all models
ALL_MODELS = {**NEW_TTS_MODELS, **BACKUP_MODELS}

def handle_errors(f):
    """Decorator to handle errors gracefully"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {str(e)}")
            return jsonify({
                "error": "Internal server error",
                "details": str(e)
            }), 500
    return decorated_function

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎤 New TTS Models - Feb 2025</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', sans-serif; }
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            width: 100%;
            max-width: 800px;
            padding: 40px;
            animation: slideUp 0.5s ease;
        }
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 2.2em;
        }
        h1 span {
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 1.1em;
            border-left: 4px solid #667eea;
            padding-left: 15px;
        }
        .model-badge {
            display: inline-block;
            background: #e0e7ff;
            color: #4f46e5;
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 0.8em;
            margin-left: 10px;
        }
        .form-group { margin-bottom: 25px; }
        label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 600;
        }
        textarea, select {
            width: 100%;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            font-size: 1em;
            transition: all 0.3s ease;
            background: #f9f9f9;
        }
        textarea {
            min-height: 150px;
            resize: vertical;
        }
        textarea:focus, select:focus {
            outline: none;
            border-color: #667eea;
            background: white;
            box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
        }
        select {
            cursor: pointer;
            appearance: none;
            background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e");
            background-repeat: no-repeat;
            background-position: right 15px center;
            background-size: 15px;
        }
        .model-info {
            background: #f0f4ff;
            border-radius: 10px;
            padding: 15px;
            margin-top: 10px;
            font-size: 0.95em;
            color: #4a5568;
            display: flex;
            align-items: flex-start;
            gap: 10px;
        }
        .model-info i { color: #667eea; font-size: 1.2em; margin-top: 2px; }
        .model-details {
            line-height: 1.6;
        }
        .model-tag {
            background: #4f46e5;
            color: white;
            padding: 3px 8px;
            border-radius: 15px;
            font-size: 0.8em;
            margin-right: 5px;
        }
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 18px 30px;
            border-radius: 12px;
            font-size: 1.1em;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }
        button:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        }
        button:disabled { opacity: 0.7; cursor: not-allowed; }
        .audio-container {
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 12px;
            display: none;
            animation: fadeIn 0.5s ease;
        }
        .audio-container.show { display: block; }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .audio-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .audio-header h3 { color: #333; font-size: 1.2em; }
        .download-btn {
            background: #28a745;
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9em;
            display: inline-flex;
            align-items: center;
            gap: 5px;
            text-decoration: none;
        }
        .download-btn:hover { background: #218838; }
        audio { width: 100%; margin-top: 10px; }
        .loader {
            display: none;
            text-align: center;
            margin: 20px 0;
        }
        .loader.show { display: block; }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .loader p { color: #666; font-size: 1.1em; }
        .char-counter {
            text-align: right;
            font-size: 0.85em;
            color: #888;
            margin-top: 5px;
        }
        .char-counter.warning { color: #dc3545; }
        .stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
        }
        .stat {
            text-align: center;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 10px;
        }
        .stat i {
            font-size: 1.5em;
            color: #667eea;
            margin-bottom: 5px;
            display: block;
        }
        .stat span { color: #555; font-size: 0.9em; }
        .stat .value {
            font-size: 1.2em;
            font-weight: bold;
            color: #4f46e5;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>
            <span>🎤 TTS Studio</span>
            <span class="model-badge">Feb 2025 Models</span>
        </h1>
        <div class="subtitle">
            Latest Hugging Face TTS Models - Recently Updated
        </div>
        
        <div class="form-group">
            <label>🎯 Select Model</label>
            <select id="modelSelect">
                <option value="moss-tts">🌿 MOSS-TTS (8B) - Latest, High Quality</option>
                <option value="soulx-singer">🎤 SoulX-Singer - Singing Voice</option>
                <option value="kugelaudio">🎵 KugelAudio-0 - Open Audio</option>
                <option value="qwen3-tts">🐉 Qwen3-TTS (1.7B) - Custom Voice</option>
                <option value="kani-tts">🔊 Kani-TTS-2 (0.4B) - Fast</option>
                <option value="bark">🎭 Bark - Backup Model</option>
            </select>
            
            <div class="model-info" id="modelInfo">
                <i>ℹ️</i>
                <div class="model-details" id="modelDescription">
                    <strong>OpenMOSS-Team/MOSS-TTS</strong> - 8B parameter model<br>
                    Updated 3 days ago • 196 discussions • 9.6k runs
                </div>
            </div>
        </div>
        
        <div class="form-group">
            <label>📝 Enter Text</label>
            <textarea id="textInput" placeholder="Type text here... (max 500 chars)">Assalam-o-Alaikum! Yeh latest TTS models ka test hai.</textarea>
            <div class="char-counter" id="charCounter">0/500</div>
        </div>
        
        <button onclick="generateSpeech()" id="generateBtn">
            <span>🎙️ Generate Speech</span>
        </button>
        
        <div class="loader" id="loader">
            <div class="spinner"></div>
            <p>Generating... (20-30 sec for first time)</p>
            <small style="color: #888;">Model loading may take time</small>
        </div>
        
        <div class="audio-container" id="audioContainer">
            <div class="audio-header">
                <h3>🎧 Generated Audio</h3>
                <a href="#" class="download-btn" id="downloadBtn" download="speech.wav">⬇️ Download</a>
            </div>
            <audio id="audioPlayer" controls></audio>
        </div>
        
        <div class="stats">
            <div class="stat">
                <i>🆕</i>
                <span class="value">5</span>
                <span>New Models</span>
            </div>
            <div class="stat">
                <i>📊</i>
                <span class="value" id="modelStats">8B</span>
                <span>Parameters</span>
            </div>
            <div class="stat">
                <i>⚡</i>
                <span class="value">Free</span>
                <span>To Use</span>
            </div>
        </div>
    </div>

    <script>
        const textInput = document.getElementById('textInput');
        const charCounter = document.getElementById('charCounter');
        const modelSelect = document.getElementById('modelSelect');
        const modelDescription = document.getElementById('modelDescription');
        const modelStats = document.getElementById('modelStats');
        const generateBtn = document.getElementById('generateBtn');
        const loader = document.getElementById('loader');
        const audioContainer = document.getElementById('audioContainer');
        const audioPlayer = document.getElementById('audioPlayer');
        const downloadBtn = document.getElementById('downloadBtn');
        
        // Model details
        const modelDetails = {
            'moss-tts': {
                name: 'OpenMOSS-Team/MOSS-TTS',
                desc: '8B parameter model - High quality TTS',
                stats: '8B',
                details: 'Updated 3 days ago • 196 discussions • 9.6k runs'
            },
            'soulx-singer': {
                name: 'Soul-AILab/SoulX-Singer',
                desc: 'Specialized for singing voice',
                stats: '1B',
                details: 'Updated 5 days ago • 88 discussions • 691 runs'
            },
            'kugelaudio': {
                name: 'kugelaudio/kugelaudio-0-open',
                desc: 'Open audio generation model',
                stats: '1.5B',
                details: 'Updated 10 days ago • 159 discussions • 38.3k runs'
            },
            'qwen3-tts': {
                name: 'Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice',
                desc: 'Custom voice capable - 1.7B',
                stats: '1.7B',
                details: 'Updated 18 days ago • 956 discussions • 675k runs'
            },
            'kani-tts': {
                name: 'nininenixi/kani-tts-2-en',
                desc: 'Lightweight fast model - 0.4B',
                stats: '0.4B',
                details: 'Updated 2 days ago • 71 discussions • 483 runs'
            },
            'bark': {
                name: 'suno/bark',
                desc: 'Backup model - Expressive TTS',
                stats: '1B',
                details: 'Stable backup model'
            }
        };
        
        function updateCharCounter() {
            const len = textInput.value.length;
            charCounter.textContent = len + '/500';
            if (len > 450) charCounter.classList.add('warning');
            else charCounter.classList.remove('warning');
        }
        
        textInput.addEventListener('input', updateCharCounter);
        updateCharCounter();
        
        modelSelect.addEventListener('change', function() {
            const model = this.value;
            const details = modelDetails[model];
            if (details) {
                modelDescription.innerHTML = `<strong>${details.name}</strong> - ${details.desc}<br><small>${details.details}</small>`;
                modelStats.textContent = details.stats;
            }
        });
        
        async function generateSpeech() {
            const text = textInput.value.trim();
            const model = modelSelect.value;
            
            if (!text) { alert('Please enter text!'); return; }
            if (text.length > 500) { alert('Max 500 characters!'); return; }
            
            generateBtn.disabled = true;
            loader.classList.add('show');
            audioContainer.classList.remove('show');
            
            try {
                const response = await fetch('/tts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text, model })
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || `Error ${response.status}`);
                }
                
                const audioBlob = await response.blob();
                const audioUrl = URL.createObjectURL(audioBlob);
                
                audioPlayer.src = audioUrl;
                audioContainer.classList.add('show');
                downloadBtn.href = audioUrl;
                audioPlayer.play();
                
            } catch (error) {
                alert('Error: ' + error.message);
                console.error(error);
            } finally {
                generateBtn.disabled = false;
                loader.classList.remove('show');
            }
        }
        
        textInput.addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                generateSpeech();
            }
        });
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/tts', methods=['POST', 'OPTIONS'])
@handle_errors
def generate_speech():
    if request.method == 'OPTIONS':
        return '', 200
    
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({"error": "Please provide text"}), 400
    
    text = data['text']
    model_key = data.get('model', 'moss-tts')
    
    if not text:
        return jsonify({"error": "Text cannot be empty"}), 400
    
    if len(text) > 500:
        return jsonify({"error": "Text too long (max 500 chars)"}), 400
    
    if model_key not in ALL_MODELS:
        return jsonify({"error": f"Model {model_key} not found"}), 400
    
    model_id = ALL_MODELS[model_key]
    
    if HF_TOKEN == "MISSING_TOKEN":
        return jsonify({"error": "Hugging Face token not configured"}), 500
    
    logger.info(f"🔊 Generating with model: {model_id}")
    
    try:
        # Try the selected model first
        response = requests.post(
            f"https://api-inference.huggingface.co/models/{model_id}",
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            json={"inputs": text},
            timeout=60
        )
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', 'audio/flac')
            return Response(
                response.content,
                mimetype=content_type,
                headers={'Access-Control-Allow-Origin': '*'}
            )
        
        elif response.status_code == 503:
            # Model is loading
            return jsonify({
                "error": "Model is loading. Please wait 20 seconds and try again.",
                "status": "loading"
            }), 503
        
        else:
            # Try backup model (bark) if primary fails
            logger.info(f"Primary model failed, trying backup...")
            backup_response = requests.post(
                "https://api-inference.huggingface.co/models/suno/bark",
                headers={"Authorization": f"Bearer {HF_TOKEN}"},
                json={"inputs": text},
                timeout=60
            )
            
            if backup_response.status_code == 200:
                content_type = backup_response.headers.get('Content-Type', 'audio/flac')
                return Response(
                    backup_response.content,
                    mimetype=content_type,
                    headers={'Access-Control-Allow-Origin': '*'}
                )
            
            return jsonify({
                "error": f"API Error: {response.status_code}",
                "details": response.text[:200]
            }), response.status_code
    
    except requests.exceptions.Timeout:
        return jsonify({"error": "Request timeout. Try again."}), 504
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/models')
@handle_errors
def list_models():
    """List all available models"""
    return jsonify({
        "new_models": [
            {
                "id": "moss-tts",
                "name": "MOSS-TTS",
                "hf_id": "OpenMOSS-Team/MOSS-TTS",
                "size": "8B",
                "updated": "3 days ago",
                "runs": "9.6k"
            },
            {
                "id": "soulx-singer",
                "name": "SoulX-Singer",
                "hf_id": "Soul-AILab/SoulX-Singer",
                "size": "~1B",
                "updated": "5 days ago",
                "runs": "691"
            },
            {
                "id": "kugelaudio",
                "name": "KugelAudio-0",
                "hf_id": "kugelaudio/kugelaudio-0-open",
                "size": "~1.5B",
                "updated": "10 days ago",
                "runs": "38.3k"
            },
            {
                "id": "qwen3-tts",
                "name": "Qwen3-TTS",
                "hf_id": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
                "size": "1.7B",
                "updated": "18 days ago",
                "runs": "675k"
            },
            {
                "id": "kani-tts",
                "name": "Kani-TTS-2",
                "hf_id": "nininenixi/kani-tts-2-en",
                "size": "0.4B",
                "updated": "2 days ago",
                "runs": "483"
            }
        ],
        "backup_models": [
            {
                "id": "bark",
                "name": "Bark",
                "hf_id": "suno/bark"
            }
        ]
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "models": list(ALL_MODELS.keys()),
        "token": "✅" if HF_TOKEN != "MISSING_TOKEN" else "❌"
    })

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    return response

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("="*60)
    print("🚀 Starting TTS Server with NEW Models (Feb 2025)")
    print("="*60)
    print("📝 New Models Available:")
    for key, value in NEW_TTS_MODELS.items():
        print(f"   • {key}: {value}")
    print("\n📝 Backup Models:")
    for key, value in BACKUP_MODELS.items():
        print(f"   • {key}: {value}")
    print("-"*60)
    print(f"🔑 Token Status: {'✅ Configured' if HF_TOKEN != 'MISSING_TOKEN' else '❌ MISSING'}")
    print(f"🌐 Server Port: {port}")
    print("="*60)
    
    app.run(host='0.0.0.0', port=port, debug=True)

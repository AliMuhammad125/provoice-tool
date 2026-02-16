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

# Hugging Face API token - Render ke environment variables se lega
HF_TOKEN = os.environ.get('HUGGING_FACE_TOKEN')
if not HF_TOKEN:
    logger.error("❌ HUGGING_FACE_TOKEN environment variable not set!")
    HF_TOKEN = "MISSING_TOKEN"  # Placeholder to avoid crashes

logger.info(f"✅ HUGGING_FACE_TOKEN loaded: {HF_TOKEN[:5]}...{HF_TOKEN[-5:] if len(HF_TOKEN) > 10 else ''}")

# TTS Models
TTS_MODELS = {
    'mms-english': 'facebook/mms-tts-eng',
    'mms-hindi': 'facebook/mms-tts-hin',
    'mms-urdu': 'facebook/mms-tts-urd',
}

# Add more models but mark them as experimental
EXPERIMENTAL_MODELS = {
    'bark': 'suno/bark',
    'speecht5': 'microsoft/speecht5_tts',
}

# Combine all models
ALL_MODELS = {**TTS_MODELS, **EXPERIMENTAL_MODELS}

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
                "details": str(e),
                "tip": "Check logs for more information"
            }), 500
    return decorated_function

# HTML Template for the frontend
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎤 TTS Studio - Text to Speech</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
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
            max-width: 700px;
            padding: 40px;
            animation: slideUp 0.5s ease;
        }
        
        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
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
        
        .form-group {
            margin-bottom: 25px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 600;
            font-size: 1em;
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
            padding: 10px 15px;
            margin-top: 10px;
            font-size: 0.9em;
            color: #4a5568;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .model-info i {
            color: #667eea;
            font-size: 1.2em;
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
        
        button:disabled {
            opacity: 0.7;
            cursor: not-allowed;
        }
        
        .audio-container {
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 12px;
            display: none;
            animation: fadeIn 0.5s ease;
        }
        
        .audio-container.show {
            display: block;
        }
        
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .audio-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .audio-header h3 {
            color: #333;
            font-size: 1.2em;
        }
        
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
        
        .download-btn:hover {
            background: #218838;
        }
        
        audio {
            width: 100%;
            margin-top: 10px;
        }
        
        .loader {
            display: none;
            text-align: center;
            margin: 20px 0;
        }
        
        .loader.show {
            display: block;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .loader p {
            color: #666;
            font-size: 1.1em;
        }
        
        .char-counter {
            text-align: right;
            font-size: 0.85em;
            color: #888;
            margin-top: 5px;
        }
        
        .char-counter.warning {
            color: #dc3545;
        }
        
        .status-badge {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 600;
            margin-left: 10px;
        }
        
        .status-badge.success {
            background: #d4edda;
            color: #155724;
        }
        
        .status-badge.error {
            background: #f8d7da;
            color: #721c24;
        }
        
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
        }
        
        .feature {
            text-align: center;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 10px;
        }
        
        .feature i {
            font-size: 1.5em;
            color: #667eea;
            margin-bottom: 5px;
            display: block;
        }
        
        .feature span {
            color: #555;
            font-size: 0.9em;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 25px;
            }
            
            h1 {
                font-size: 1.8em;
            }
            
            .features {
                grid-template-columns: 1fr 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>
            <span>🎤 TTS Studio</span>
        </h1>
        <div class="subtitle">
            Transform your text into natural speech using AI
        </div>
        
        <div class="form-group">
            <label>🌐 Select Language / Voice</label>
            <select id="modelSelect">
                <option value="mms-english">🇺🇸 English (US) - High Quality</option>
                <option value="mms-urdu">🇵🇰 Urdu (اردو) - High Quality</option>
                <option value="mms-hindi">🇮🇳 Hindi (हिन्दी) - High Quality</option>
                <option value="bark">🎭 Bark - Expressive (Experimental)</option>
                <option value="speecht5">🤖 SpeechT5 - Research (Experimental)</option>
            </select>
            <div class="model-info">
                <i>ℹ️</i>
                <span id="modelDescription">Meta's MMS model - High quality, fast response</span>
            </div>
        </div>
        
        <div class="form-group">
            <label>📝 Enter your text</label>
            <textarea id="textInput" placeholder="Type or paste your text here... (max 500 characters)">Assalam-o-Alaikum! Yeh meri website hai. Main Hugging Face TTS use kar raha hoon.</textarea>
            <div class="char-counter" id="charCounter">0/500 characters</div>
        </div>
        
        <button onclick="generateSpeech()" id="generateBtn">
            <span>🎙️ Generate Speech</span>
        </button>
        
        <div class="loader" id="loader">
            <div class="spinner"></div>
            <p>Generating your speech... (may take 20-30 sec for first time)</p>
            <small style="color: #888;">Model loading might take time on first request</small>
        </div>
        
        <div class="audio-container" id="audioContainer">
            <div class="audio-header">
                <h3>🎧 Your Generated Audio</h3>
                <a href="#" class="download-btn" id="downloadBtn" download="speech.wav">⬇️ Download</a>
            </div>
            <audio id="audioPlayer" controls controlsList="nodownload"></audio>
        </div>
        
        <div class="features">
            <div class="feature">
                <i>🚀</i>
                <span>Fast Processing</span>
            </div>
            <div class="feature">
                <i>🌍</i>
                <span>Multiple Languages</span>
            </div>
            <div class="feature">
                <i>🎯</i>
                <span>High Quality</span>
            </div>
            <div class="feature">
                <i>💯</i>
                <span>Free to Use</span>
            </div>
        </div>
    </div>

    <script>
        const textInput = document.getElementById('textInput');
        const charCounter = document.getElementById('charCounter');
        const modelSelect = document.getElementById('modelSelect');
        const modelDescription = document.getElementById('modelDescription');
        const generateBtn = document.getElementById('generateBtn');
        const loader = document.getElementById('loader');
        const audioContainer = document.getElementById('audioContainer');
        const audioPlayer = document.getElementById('audioPlayer');
        const downloadBtn = document.getElementById('downloadBtn');
        
        // Model descriptions
        const modelDescriptions = {
            'mms-english': '🇺🇸 Meta MMS English - High quality, natural sounding voice',
            'mms-urdu': '🇵🇰 Meta MMS Urdu - اردو میں اعلیٰ معیار کی آواز',
            'mms-hindi': '🇮🇳 Meta MMS Hindi - हिंदी में उच्च गुणवत्ता वाली आवाज़',
            'bark': '🎭 Suno Bark - Expressive speech with emotions (slower)',
            'speecht5': '🤖 Microsoft SpeechT5 - Research model for experiments'
        };
        
        // Update character counter
        function updateCharCounter() {
            const len = textInput.value.length;
            charCounter.textContent = `${len}/500 characters`;
            if (len > 450) {
                charCounter.classList.add('warning');
            } else {
                charCounter.classList.remove('warning');
            }
        }
        
        textInput.addEventListener('input', updateCharCounter);
        updateCharCounter();
        
        // Update model description
        modelSelect.addEventListener('change', function() {
            modelDescription.textContent = modelDescriptions[this.value] || 'Select a model';
        });
        
        // Main function to generate speech
        async function generateSpeech() {
            const text = textInput.value.trim();
            const model = modelSelect.value;
            
            if (!text) {
                alert('Please enter some text!');
                return;
            }
            
            if (text.length > 500) {
                alert('Text is too long! Maximum 500 characters.');
                return;
            }
            
            // Disable button and show loader
            generateBtn.disabled = true;
            loader.classList.add('show');
            audioContainer.classList.remove('show');
            
            try {
                // API call
                const response = await fetch('/tts', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        text: text,
                        model: model
                    })
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || `Error ${response.status}`);
                }
                
                // Get audio blob
                const audioBlob = await response.blob();
                const audioUrl = URL.createObjectURL(audioBlob);
                
                // Update audio player
                audioPlayer.src = audioUrl;
                audioContainer.classList.add('show');
                
                // Update download link
                downloadBtn.href = audioUrl;
                
                // Auto play
                audioPlayer.play();
                
            } catch (error) {
                alert('Error: ' + error.message);
                console.error(error);
            } finally {
                // Re-enable button and hide loader
                generateBtn.disabled = false;
                loader.classList.remove('show');
            }
        }
        
        // Enter key shortcut (Ctrl+Enter)
        textInput.addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                generateSpeech();
            }
        });
        
        // Initial model description
        modelDescription.textContent = modelDescriptions[modelSelect.value];
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    """Serve the beautiful frontend"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api-info')
@handle_errors
def api_info():
    """API endpoint for frontend to get info"""
    token_status = "✅ Configured" if HF_TOKEN != "MISSING_TOKEN" else "❌ Missing"
    
    return jsonify({
        "service": "Hugging Face TTS API",
        "status": "running",
        "token_status": token_status,
        "environment": os.environ.get('RENDER', 'development'),
        "available_models": list(TTS_MODELS.keys()),
        "experimental_models": list(EXPERIMENTAL_MODELS.keys()),
        "max_chars": 500
    })

@app.route('/models')
@handle_errors
def list_models():
    """List all available models"""
    return jsonify({
        "stable_models": [
            {
                "id": "mms-english",
                "name": "English (US)",
                "hf_id": "facebook/mms-tts-eng",
                "language": "English",
                "status": "stable"
            },
            {
                "id": "mms-hindi",
                "name": "हिन्दी (Hindi)",
                "hf_id": "facebook/mms-tts-hin",
                "language": "Hindi",
                "status": "stable"
            },
            {
                "id": "mms-urdu",
                "name": "اردو (Urdu)",
                "hf_id": "facebook/mms-tts-urd",
                "language": "Urdu",
                "status": "stable"
            }
        ],
        "experimental_models": [
            {
                "id": "bark",
                "name": "Bark (Expressive)",
                "hf_id": "suno/bark",
                "language": "English",
                "status": "experimental",
                "note": "May take 30-60 seconds to load"
            },
            {
                "id": "speecht5",
                "name": "SpeechT5",
                "hf_id": "microsoft/speecht5_tts",
                "language": "English",
                "status": "experimental"
            }
        ]
    })

@app.route('/health')
@handle_errors
def health_check():
    """Health check endpoint for Render"""
    token_ok = HF_TOKEN != "MISSING_TOKEN"
    
    # Test Hugging Face API with a quick call
    hf_status = "unknown"
    if token_ok:
        try:
            test_response = requests.get(
                "https://api-inference.huggingface.co/status",
                headers={"Authorization": f"Bearer {HF_TOKEN}"},
                timeout=5
            )
            hf_status = "connected" if test_response.status_code == 200 else "error"
        except:
            hf_status = "unreachable"
    
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "token_configured": token_ok,
        "huggingface_status": hf_status,
        "models_available": len(ALL_MODELS)
    })

@app.route('/tts', methods=['POST', 'OPTIONS'])
@handle_errors
def generate_speech():
    """Generate speech using Hugging Face models"""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return '', 200
    
    # Get JSON data
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No JSON data received"}), 400
    
    text = data.get('text', '')
    model_key = data.get('model', 'mms-english')
    
    # Validate text
    if not text:
        return jsonify({"error": "No text provided"}), 400
    
    if len(text) > 500:
        return jsonify({
            "error": "Text too long (max 500 characters)",
            "current_length": len(text)
        }), 400
    
    # Validate model
    if model_key not in ALL_MODELS:
        return jsonify({
            "error": f"Model '{model_key}' not found",
            "available_models": list(TTS_MODELS.keys()),
            "experimental": list(EXPERIMENTAL_MODELS.keys())
        }), 400
    
    model_id = ALL_MODELS[model_key]
    
    # Check token
    if HF_TOKEN == "MISSING_TOKEN":
        return jsonify({
            "error": "Hugging Face token not configured",
            "solution": "Add HUGGING_FACE_TOKEN to Render environment variables"
        }), 500
    
    logger.info(f"🔊 Generating speech with {model_id}")
    logger.info(f"📝 Text: {text[:50]}...")
    
    # Prepare API request
    API_URL = f"https://api-inference.huggingface.co/models/{model_id}"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    # Different payload for different models
    if model_key == 'bark':
        payload = {
            "inputs": text,
            "parameters": {
                "voice_preset": "v2/en_speaker_6"
            }
        }
    else:
        payload = {"inputs": text}
    
    try:
        # Make request to Hugging Face
        response = requests.post(
            API_URL,
            headers=headers,
            json=payload,
            timeout=60  # Longer timeout for model loading
        )
        
        logger.info(f"HF API Response status: {response.status_code}")
        
        # Handle different response statuses
        if response.status_code == 200:
            # Success - return audio
            content_type = response.headers.get('Content-Type', 'audio/flac')
            
            return Response(
                response.content,
                mimetype=content_type,
                headers={
                    'Content-Disposition': f'attachment; filename=speech.{content_type.split("/")[-1]}',
                    'X-Model-Used': model_id,
                    'X-Model-Key': model_key,
                    'Access-Control-Allow-Origin': '*'
                }
            )
        
        elif response.status_code == 503:
            # Model is loading
            return jsonify({
                "error": "Model is loading. Please wait 20 seconds and try again.",
                "status": "loading",
                "estimated_time": "20-30 seconds",
                "model": model_id
            }), 503
        
        else:
            # Other errors
            error_text = response.text[:200] if response.text else "No error details"
            logger.error(f"HF API error: {response.status_code} - {error_text}")
            
            return jsonify({
                "error": f"Hugging Face API error: {response.status_code}",
                "details": error_text,
                "model": model_id
            }), response.status_code
    
    except requests.exceptions.Timeout:
        logger.error("Timeout error")
        return jsonify({
            "error": "Request timeout",
            "tip": "Model might be loading. Try again in 30 seconds."
        }), 504
    
    except requests.exceptions.ConnectionError:
        logger.error("Connection error")
        return jsonify({
            "error": "Connection error",
            "tip": "Check internet connection"
        }), 503
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500

@app.after_request
def after_request(response):
    """Add CORS headers"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    return response

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info("="*50)
    logger.info("🚀 Starting Hugging Face TTS Server with Frontend")
    logger.info("="*50)
    logger.info(f"📝 Models available: {list(TTS_MODELS.keys())}")
    logger.info(f"🔬 Experimental: {list(EXPERIMENTAL_MODELS.keys())}")
    
    if HF_TOKEN == "MISSING_TOKEN":
        logger.error("❌ HUGGING_FACE_TOKEN not set!")
        logger.error("📌 Add it to environment variables")
    else:
        logger.info("✅ Hugging Face token configured")
    
    logger.info(f"🌐 Server starting on port {port}")
    logger.info(f"📱 Open http://localhost:{port} in your browser")
    logger.info("="*50)
    
    app.run(host='0.0.0.0', port=port, debug=True)

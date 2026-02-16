from flask import Flask, request, Response, jsonify, render_template_string
import edge_tts
import asyncio
import io
import logging
import os
import time
import random
from datetime import datetime
from functools import wraps

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiting storage
request_log = {}

# Voice configurations with gender info
VOICES = {
    # Male Voices
    'en-US-GuyNeural': {'name': '🇺🇸 Guy (Male)', 'gender': 'male', 'lang': 'en-US'},
    'en-US-DavisNeural': {'name': '🇺🇸 Davis (Male)', 'gender': 'male', 'lang': 'en-US'},
    'en-US-JasonNeural': {'name': '🇺🇸 Jason (Male)', 'gender': 'male', 'lang': 'en-US'},
    'en-US-TonyNeural': {'name': '🇺🇸 Tony (Male)', 'gender': 'male', 'lang': 'en-US'},
    'en-GB-RyanNeural': {'name': '🇬🇧 Ryan (Male)', 'gender': 'male', 'lang': 'en-GB'},
    'en-GB-ThomasNeural': {'name': '🇬🇧 Thomas (Male)', 'gender': 'male', 'lang': 'en-GB'},
    'hi-IN-MadhurNeural': {'name': '🇮🇳 मधुर (Male)', 'gender': 'male', 'lang': 'hi-IN'},
    'ur-PK-AsadNeural': {'name': '🇵🇰 اسد (Male)', 'gender': 'male', 'lang': 'ur-PK'},
    
    # Female Voices
    'en-US-JennyNeural': {'name': '🇺🇸 Jenny (Female)', 'gender': 'female', 'lang': 'en-US'},
    'en-US-AriaNeural': {'name': '🇺🇸 Aria (Female)', 'gender': 'female', 'lang': 'en-US'},
    'en-US-MichelleNeural': {'name': '🇺🇸 Michelle (Female)', 'gender': 'female', 'lang': 'en-US'},
    'en-US-SaraNeural': {'name': '🇺🇸 Sara (Female)', 'gender': 'female', 'lang': 'en-US'},
    'en-GB-LibbyNeural': {'name': '🇬🇧 Libby (Female)', 'gender': 'female', 'lang': 'en-GB'},
    'en-GB-SoniaNeural': {'name': '🇬🇧 Sonia (Female)', 'gender': 'female', 'lang': 'en-GB'},
    'hi-IN-SwaraNeural': {'name': '🇮🇳 स्वरा (Female)', 'gender': 'female', 'lang': 'hi-IN'},
    'ur-PK-UzmaNeural': {'name': '🇵🇰 عظمیٰ (Female)', 'gender': 'female', 'lang': 'ur-PK'},
}

def rate_limit(max_requests_per_hour=10):
    """Rate limiting decorator - 10 requests per hour max"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.remote_addr
            current_time = time.time()
            
            # Clean old requests
            if client_ip in request_log:
                request_log[client_ip] = [t for t in request_log[client_ip] 
                                         if current_time - t < 3600]  # 1 hour
            
            # Check rate limit
            if client_ip in request_log and len(request_log[client_ip]) >= max_requests_per_hour:
                wait_time = 3600 - (current_time - min(request_log[client_ip]))
                return jsonify({
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {max_requests_per_hour} requests per hour",
                    "wait_time": int(wait_time / 60),  # minutes
                    "try_again": f"Please wait {int(wait_time / 60)} minutes"
                }), 429
            
            # Add delay of 20-30 seconds
            delay = random.randint(20, 30)
            logger.info(f"⏰ Adding delay of {delay} seconds...")
            time.sleep(delay)
            
            # Log this request
            if client_ip not in request_log:
                request_log[client_ip] = []
            request_log[client_ip].append(current_time)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/')
def home():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🔊 Edge TTS Pro</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', sans-serif; }
            body {
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
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
            }
            h1 {
                color: #1e3c72;
                margin-bottom: 10px;
                font-size: 2.2em;
            }
            .subtitle {
                color: #666;
                margin-bottom: 30px;
                border-left: 4px solid #2a5298;
                padding-left: 15px;
            }
            .row {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
                margin-bottom: 20px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 8px;
                color: #555;
                font-weight: 600;
            }
            select, input, textarea {
                width: 100%;
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 1em;
                transition: all 0.3s ease;
            }
            select:focus, input:focus, textarea:focus {
                outline: none;
                border-color: #2a5298;
                box-shadow: 0 0 0 3px rgba(42,82,152,0.1);
            }
            textarea {
                min-height: 120px;
                resize: vertical;
            }
            .gender-filter {
                display: flex;
                gap: 10px;
                margin-bottom: 15px;
            }
            .gender-btn {
                flex: 1;
                padding: 10px;
                border: 2px solid #e0e0e0;
                background: white;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 600;
                transition: all 0.3s ease;
            }
            .gender-btn.active {
                background: #2a5298;
                color: white;
                border-color: #2a5298;
            }
            .gender-btn.male.active { background: #2a5298; }
            .gender-btn.female.active { background: #c44569; }
            .pitch-control {
                margin: 20px 0;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 10px;
            }
            .pitch-value {
                display: flex;
                justify-content: space-between;
                margin-top: 5px;
                color: #666;
            }
            button {
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 1.1em;
                font-weight: 600;
                cursor: pointer;
                width: 100%;
                transition: transform 0.2s ease;
                margin: 10px 0;
            }
            button:hover:not(:disabled) {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(0,0,0,0.2);
            }
            button:disabled {
                opacity: 0.7;
                cursor: not-allowed;
            }
            .audio-container {
                margin-top: 20px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 10px;
                display: none;
            }
            .audio-container.show { display: block; }
            audio { width: 100%; margin-top: 10px; }
            .loader {
                display: none;
                text-align: center;
                margin: 20px 0;
                padding: 20px;
            }
            .loader.show { display: block; }
            .spinner {
                border: 4px solid #f3f3f3;
                border-top: 4px solid #2a5298;
                border-radius: 50%;
                width: 50px;
                height: 50px;
                animation: spin 1s linear infinite;
                margin: 0 auto 15px;
            }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            .info-box {
                background: #e3f2fd;
                border-left: 4px solid #2196f3;
                padding: 15px;
                margin: 20px 0;
                border-radius: 5px;
            }
            .char-counter {
                text-align: right;
                color: #666;
                font-size: 0.9em;
                margin-top: 5px;
            }
            .warning { color: #f57c00; }
            .voice-list {
                max-height: 200px;
                overflow-y: auto;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 10px;
            }
            .voice-item {
                padding: 8px;
                margin: 5px 0;
                border-radius: 5px;
                cursor: pointer;
                transition: background 0.3s ease;
            }
            .voice-item:hover { background: #f0f0f0; }
            .voice-item.selected {
                background: #2a5298;
                color: white;
            }
            .voice-item.male { border-left: 4px solid #2a5298; }
            .voice-item.female { border-left: 4px solid #c44569; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔊 Edge TTS Pro</h1>
            <div class="subtitle">
                Advanced Text to Speech with Pitch Control & Delay
            </div>
            
            <div class="info-box">
                <strong>⏰ Note:</strong> 20-30 second delay added to prevent abuse.<br>
                <strong>📊 Limit:</strong> 10 requests per hour.
            </div>
            
            <div class="gender-filter">
                <button class="gender-btn male active" onclick="filterGender('all')" id="filterAll">All</button>
                <button class="gender-btn male" onclick="filterGender('male')" id="filterMale">👨 Male</button>
                <button class="gender-btn female" onclick="filterGender('female')" id="filterFemale">👩 Female</button>
            </div>
            
            <div class="form-group">
                <label>🎤 Select Voice</label>
                <div class="voice-list" id="voiceList">
                    {% for voice_id, voice_data in voices.items() %}
                    <div class="voice-item {{ voice_data.gender }}" 
                         data-gender="{{ voice_data.gender }}"
                         data-voice="{{ voice_id }}"
                         onclick="selectVoice('{{ voice_id }}')">
                        {{ voice_data.name }}
                    </div>
                    {% endfor %}
                </div>
                <input type="hidden" id="selectedVoice" value="en-US-JennyNeural">
            </div>
            
            <div class="row">
                <div class="form-group">
                    <label>📝 Text to Convert</label>
                    <textarea id="textInput" placeholder="Enter text here..." maxlength="1000">Assalam-o-Alaikum! Yeh Edge TTS hai. Isme pitch control aur delay bhi hai.</textarea>
                    <div class="char-counter" id="charCounter">0/1000</div>
                </div>
            </div>
            
            <div class="pitch-control">
                <label>🎚️ Pitch Adjustment</label>
                <input type="range" id="pitch" min="-50" max="50" value="0" step="1" oninput="updatePitch()">
                <div class="pitch-value">
                    <span>Low</span>
                    <span id="pitchValue">0 Hz</span>
                    <span>High</span>
                </div>
            </div>
            
            <div class="pitch-control">
                <label>⚡ Speed Adjustment</label>
                <input type="range" id="rate" min="-50" max="50" value="0" step="1" oninput="updateRate()">
                <div class="pitch-value">
                    <span>Slow</span>
                    <span id="rateValue">0%</span>
                    <span>Fast</span>
                </div>
            </div>
            
            <div class="pitch-control">
                <label>⏸️ Gap Adjustment (ms)</label>
                <input type="range" id="gap" min="0" max="1000" value="0" step="10" oninput="updateGap()">
                <div class="pitch-value">
                    <span>No Gap</span>
                    <span id="gapValue">0 ms</span>
                    <span>Max Gap</span>
                </div>
            </div>
            
            <button onclick="generateSpeech()" id="generateBtn">
                <span>🎙️ Generate Speech (20-30 sec delay)</span>
            </button>
            
            <div class="loader" id="loader">
                <div class="spinner"></div>
                <p>⏰ Please wait 20-30 seconds...</p>
                <small>Delay added to prevent abuse</small>
            </div>
            
            <div class="audio-container" id="audioContainer">
                <h3>🎧 Generated Audio</h3>
                <audio id="audioPlayer" controls></audio>
                <a href="#" id="downloadBtn" download="speech.mp3" style="display:block; text-align:center; margin-top:10px;">⬇️ Download MP3</a>
            </div>
        </div>

        <script>
            const textInput = document.getElementById('textInput');
            const charCounter = document.getElementById('charCounter');
            
            textInput.addEventListener('input', () => {
                charCounter.textContent = textInput.value.length + '/1000';
                if (textInput.value.length > 900) {
                    charCounter.classList.add('warning');
                } else {
                    charCounter.classList.remove('warning');
                }
            });
            
            function selectVoice(voiceId) {
                document.getElementById('selectedVoice').value = voiceId;
                
                // Update UI
                document.querySelectorAll('.voice-item').forEach(item => {
                    item.classList.remove('selected');
                });
                event.target.classList.add('selected');
            }
            
            function filterGender(gender) {
                // Update buttons
                document.getElementById('filterAll').classList.remove('active');
                document.getElementById('filterMale').classList.remove('active');
                document.getElementById('filterFemale').classList.remove('active');
                
                if (gender === 'all') {
                    document.getElementById('filterAll').classList.add('active');
                } else if (gender === 'male') {
                    document.getElementById('filterMale').classList.add('active');
                } else {
                    document.getElementById('filterFemale').classList.add('active');
                }
                
                // Filter voices
                document.querySelectorAll('.voice-item').forEach(item => {
                    if (gender === 'all') {
                        item.style.display = 'block';
                    } else {
                        if (item.dataset.gender === gender) {
                            item.style.display = 'block';
                        } else {
                            item.style.display = 'none';
                        }
                    }
                });
            }
            
            function updatePitch() {
                const pitch = document.getElementById('pitch').value;
                document.getElementById('pitchValue').textContent = pitch + ' Hz';
            }
            
            function updateRate() {
                const rate = document.getElementById('rate').value;
                document.getElementById('rateValue').textContent = rate + '%';
            }
            
            function updateGap() {
                const gap = document.getElementById('gap').value;
                document.getElementById('gapValue').textContent = gap + ' ms';
            }
            
            async function generateSpeech() {
                const text = textInput.value.trim();
                const voice = document.getElementById('selectedVoice').value;
                const pitch = document.getElementById('pitch').value;
                const rate = document.getElementById('rate').value;
                const gap = document.getElementById('gap').value;
                
                if (!text) {
                    alert('Please enter text!');
                    return;
                }
                
                if (text.length > 1000) {
                    alert('Max 1000 characters!');
                    return;
                }
                
                document.getElementById('generateBtn').disabled = true;
                document.getElementById('loader').classList.add('show');
                document.getElementById('audioContainer').classList.remove('show');
                
                try {
                    const response = await fetch('/tts', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ text, voice, pitch, rate, gap })
                    });
                    
                    if (response.status === 429) {
                        const error = await response.json();
                        alert(error.message + '\n' + error.try_again);
                        return;
                    }
                    
                    if (!response.ok) {
                        throw new Error('Failed to generate speech');
                    }
                    
                    const blob = await response.blob();
                    const url = URL.createObjectURL(blob);
                    
                    document.getElementById('audioPlayer').src = url;
                    document.getElementById('downloadBtn').href = url;
                    document.getElementById('audioContainer').classList.add('show');
                    
                } catch (err) {
                    alert('Error: ' + err.message);
                } finally {
                    document.getElementById('generateBtn').disabled = false;
                    document.getElementById('loader').classList.remove('show');
                }
            }
            
            // Select first voice by default
            document.querySelector('.voice-item').classList.add('selected');
        </script>
    </body>
    </html>
    ''', voices=VOICES)

async def generate_edge_tts(text, voice, pitch, rate, gap):
    """Generate TTS using Edge TTS with pitch and rate control"""
    
    # Convert pitch and rate to Edge TTS format
    pitch_str = f"+{pitch}Hz" if int(pitch) >= 0 else f"{pitch}Hz"
    rate_str = f"+{rate}%" if int(rate) >= 0 else f"{rate}%"
    
    # Add gap as silence (using SSML)
    if int(gap) > 0:
        text = f'<speak><break time="{gap}ms"/>{text}</speak>'
    
    # Configure TTS
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        pitch=pitch_str,
        rate=rate_str
    )
    
    # Generate audio
    audio_data = b''
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    
    return audio_data

@app.route('/tts', methods=['POST'])
@rate_limit(max_requests_per_hour=10)
def tts():
    try:
        data = request.json
        text = data.get('text', '')
        voice = data.get('voice', 'en-US-JennyNeural')
        pitch = data.get('pitch', 0)
        rate = data.get('rate', 0)
        gap = data.get('gap', 0)
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        if len(text) > 1000:
            return jsonify({'error': 'Text too long (max 1000 chars)'}), 400
        
        # Log request
        logger.info(f"🔊 TTS Request - Voice: {voice}, Pitch: {pitch}, Rate: {rate}, Gap: {gap}")
        logger.info(f"📝 Text: {text[:50]}...")
        
        # Generate audio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio_data = loop.run_until_complete(
            generate_edge_tts(text, voice, pitch, rate, gap)
        )
        loop.close()
        
        if not audio_data:
            return jsonify({'error': 'Failed to generate audio'}), 500
        
        return Response(
            audio_data,
            mimetype='audio/mpeg',
            headers={
                'Access-Control-Allow-Origin': '*',
                'Content-Disposition': 'attachment; filename=speech.mp3'
            }
        )
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/voices')
def list_voices():
    """List all available voices with gender info"""
    return jsonify({
        'voices': [
            {
                'id': voice_id,
                'name': data['name'],
                'gender': data['gender'],
                'language': data['lang']
            }
            for voice_id, data in VOICES.items()
        ]
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Edge TTS Pro',
        'voices': len(VOICES),
        'rate_limit': '10 requests/hour',
        'delay': '20-30 seconds'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("="*60)
    print("🔊 Edge TTS Pro Server Starting...")
    print("="*60)
    print(f"✅ Voices Available: {len(VOICES)}")
    print(f"✅ Male Voices: {sum(1 for v in VOICES.values() if v['gender'] == 'male')}")
    print(f"✅ Female Voices: {sum(1 for v in VOICES.values() if v['gender'] == 'female')}")
    print(f"✅ Rate Limit: 10 requests/hour")
    print(f"✅ Delay: 20-30 seconds per request")
    print("-"*60)
    print(f"🌐 Port: {port}")
    print("="*60)
    
    app.run(host='0.0.0.0', port=port, debug=True)

from flask import Flask, request, Response, jsonify, render_template_string
import requests
import logging
import os

app = Flask(__name__)

# FREE TTS APIs - No token required
FREE_TTS_APIS = {
    'streamelements': 'https://api.streamelements.com/kappa/v2/speech',
    'voicerss': 'https://api.voicerss.org/',
}

@app.route('/')
def home():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🎤 Free TTS - 100% Working</title>
        <style>
            body {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                font-family: Arial;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 20px;
                padding: 40px;
                max-width: 600px;
                width: 100%;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }
            h1 { color: #333; margin-bottom: 10px; }
            .subtitle { color: #666; margin-bottom: 30px; }
            select, textarea {
                width: 100%;
                padding: 12px;
                margin: 10px 0;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 16px;
            }
            button {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 15px;
                border-radius: 8px;
                font-size: 16px;
                cursor: pointer;
                width: 100%;
                margin: 10px 0;
            }
            button:hover { transform: translateY(-2px); }
            .audio-container {
                margin-top: 20px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 8px;
                display: none;
            }
            .audio-container.show { display: block; }
            audio { width: 100%; }
            .loader {
                display: none;
                text-align: center;
                margin: 20px 0;
            }
            .loader.show { display: block; }
            .note {
                background: #fff3cd;
                color: #856404;
                padding: 10px;
                border-radius: 5px;
                margin: 10px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎤 Free Text to Speech</h1>
            <p class="subtitle">No API Key Required - 100% Working</p>
            
            <div class="note">
                ✅ Multiple voices • ✅ Free • ✅ No token needed
            </div>
            
            <select id="voiceSelect">
                <option value="Brian">🇺🇸 Brian (Male)</option>
                <option value="Amy">🇺🇸 Amy (Female)</option>
                <option value="Emma">🇬🇧 Emma (British)</option>
                <option value="Joanna">🇺🇸 Joanna (Female)</option>
                <option value="Matthew">🇺🇸 Matthew (Male)</option>
                <option value="Salli">🇺🇸 Salli (Female)</option>
                <option value="Ivy">🇺🇸 Ivy (Female)</option>
                <option value="Justin">🇺🇸 Justin (Male)</option>
            </select>
            
            <textarea id="textInput" rows="4" placeholder="Enter text here..." maxlength="300">Assalam-o-Alaikum! Yeh free TTS hai.</textarea>
            <div id="charCount">0/300</div>
            
            <button onclick="generateSpeech()" id="generateBtn">🔊 Generate Speech</button>
            
            <div class="loader" id="loader">
                <div class="spinner"></div>
                <p>Generating...</p>
            </div>
            
            <div class="audio-container" id="audioContainer">
                <audio id="audioPlayer" controls></audio>
                <a href="#" id="downloadBtn" download="speech.mp3" style="display:block; text-align:center; margin-top:10px;">⬇️ Download</a>
            </div>
        </div>

        <script>
            const textInput = document.getElementById('textInput');
            const charCount = document.getElementById('charCount');
            
            textInput.addEventListener('input', () => {
                charCount.textContent = textInput.value.length + '/300';
            });

            async function generateSpeech() {
                const text = textInput.value.trim();
                const voice = document.getElementById('voiceSelect').value;
                
                if (!text) return alert('Please enter text!');
                if (text.length > 300) return alert('Max 300 characters!');
                
                document.getElementById('generateBtn').disabled = true;
                document.getElementById('loader').classList.add('show');
                document.getElementById('audioContainer').classList.remove('show');
                
                try {
                    const response = await fetch('/tts', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({text, voice})
                    });
                    
                    if (!response.ok) throw new Error('Failed');
                    
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
        </script>
    </body>
    </html>
    ''')

@app.route('/tts', methods=['POST'])
def tts():
    try:
        data = request.json
        text = data.get('text', '')
        voice = data.get('voice', 'Brian')
        
        if not text:
            return jsonify({'error': 'No text'}), 400
        
        # Use StreamElements API (Free, no key needed)
        response = requests.get(
            'https://api.streamelements.com/kappa/v2/speech',
            params={
                'voice': voice,
                'text': text
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return Response(
                response.content,
                mimetype='audio/mpeg',
                headers={'Access-Control-Allow-Origin': '*'}
            )
        else:
            return jsonify({'error': 'API Error'}), response.status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("🚀 Free TTS Server Starting...")
    print("✅ No API Key Required")
    print(f"🌐 Port: {port}")
    app.run(host='0.0.0.0', port=port)

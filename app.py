import os
import io
import wave
import base64
import requests
from flask import Flask, request, Response, jsonify, render_template_string

app = Flask(__name__)

# Render ke dashboard se API Key uthayega
API_KEY = os.environ.get("GEMINI_API_KEY")

HTML_UI = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gemini 2.0 TTS - Fixed</title>
    <style>
        body { font-family: sans-serif; background: #f4f4f9; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .container { background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); width: 400px; text-align: center; }
        textarea { width: 100%; height: 100px; padding: 12px; border: 1px solid #ddd; border-radius: 10px; box-sizing: border-box; font-size: 15px; }
        button { width: 100%; padding: 15px; margin-top: 20px; border-radius: 10px; border: none; background: #6200ea; color: white; font-weight: bold; cursor: pointer; }
        button:disabled { background: #aaa; }
        .status { margin-top: 15px; color: #555; font-size: 13px; }
        audio { width: 100%; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Gemini 2.0 AI Voice</h2>
        <textarea id="textInput" placeholder="Yahan apna text likhein...">Salam! Main Gemini 2.0 hoon. Ye awaz direct API se aa rahi hai.</textarea>
        <select id="voiceSelect" style="width:100%; padding:10px; margin-top:10px; border-radius:8px;">
            <option value="Aoede">Aoede (Female)</option>
            <option value="Puck">Puck (Male)</option>
            <option value="Charon">Charon (Deep)</option>
            <option value="Kore">Kore (Soft)</option>
            <option value="Fenrir">Fenrir (Strong)</option>
        </select>
        <button id="btn">Generate Voice</button>
        <div id="status" class="status"></div>
        <audio id="player" controls style="display:none;"></audio>
    </div>
    <script>
        const btn = document.getElementById('btn');
        btn.onclick = async () => {
            const text = document.getElementById('textInput').value;
            const voice = document.getElementById('voiceSelect').value;
            if(!text) return alert("Text likhein!");
            
            btn.disabled = true;
            document.getElementById('status').innerText = "Gemini is speaking...";
            try {
                const res = await fetch('/tts', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({text, voice})
                });
                const data = await res.json();
                if (data.error) throw new Error(data.error);
                
                const audioBlob = await fetch('data:audio/wav;base64,' + data.audio).then(r => r.blob());
                document.getElementById('player').src = URL.createObjectURL(audioBlob);
                document.getElementById('player').style.display = "block";
                document.getElementById('player').play();
                document.getElementById('status').innerText = "Success!";
            } catch (e) {
                document.getElementById('status').innerText = "Error: " + e.message;
            } finally { btn.disabled = false; }
        };
    </script>
</body>
</html>
"""

def pcm_to_wav(pcm_data):
    """Raw PCM bytes ko WAV format mein convert karta hai"""
    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(24000)
        wav_file.writeframes(pcm_data)
    return wav_io.getvalue()

@app.route('/')
def index():
    return render_template_string(HTML_UI)

@app.route('/tts', methods=['POST'])
def tts():
    if not API_KEY:
        return jsonify({"error": "API Key nahi mili! Render settings check karein."}), 500
    
    try:
        data = request.json
        text = data.get('text', 'Hello')
        voice = data.get('voice', 'Aoede')

        # Direct REST API URL for Gemini 2.0 Flash
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"
        
        payload = {
            "contents": [{
                "parts": [{"text": text}]
            }],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {"voiceName": voice}
                    }
                }
            }
        }

        response = requests.post(url, json=payload)
        res_json = response.json()

        if response.status_code != 200:
            return jsonify({"error": res_json.get('error', {}).get('message', 'API Error')}), response.status_code

        # Audio data extract karein (Base64 mein milti hai)
        try:
            audio_base64 = res_json['candidates'][0]['content']['parts'][0]['inlineData']['data']
            raw_pcm = base64.b64decode(audio_base64)
            audio_wav = pcm_to_wav(raw_pcm)
            
            # WAV ko Base64 kar ke frontend ko bhej dein
            return jsonify({"audio": base64.b64encode(audio_wav).decode('utf-8')})
        except KeyError:
            return jsonify({"error": "Google ne audio return nahi ki. Model busy ho sakta hai."}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

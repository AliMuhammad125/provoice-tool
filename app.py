import os
import io
import wave
from flask import Flask, request, Response, jsonify, render_template_string
from google import genai
from google.genai import types

app = Flask(__name__)

# Render ke dashboard se API Key uthayega
API_KEY = os.environ.get("GEMINI_API_KEY")

# --- KHOOBSURAT INTERFACE (HTML) ---
HTML_UI = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gemini 2.0 High-Quality TTS</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; color: #333; }
        .container { background: white; padding: 2.5rem; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); width: 100%; max-width: 450px; text-align: center; }
        h1 { color: #4a148c; margin-bottom: 0.5rem; font-size: 24px; }
        p { color: #666; margin-bottom: 1.5rem; font-size: 14px; }
        textarea { width: 100%; height: 100px; padding: 15px; border: 2px solid #e0e0e0; border-radius: 12px; font-size: 16px; resize: none; box-sizing: border-box; outline: none; transition: border-color 0.3s; }
        textarea:focus { border-color: #764ba2; }
        select { width: 100%; padding: 12px; margin-top: 1rem; border-radius: 10px; border: 2px solid #e0e0e0; background: #fff; cursor: pointer; }
        button { width: 100%; padding: 15px; margin-top: 1.5rem; border-radius: 10px; border: none; background: #764ba2; color: white; font-size: 16px; font-weight: bold; cursor: pointer; box-shadow: 0 4px 15px rgba(118, 75, 162, 0.3); transition: transform 0.2s, background 0.3s; }
        button:hover { background: #5e35b1; transform: translateY(-2px); }
        button:active { transform: translateY(0); }
        button:disabled { background: #ccc; box-shadow: none; cursor: not-allowed; }
        .audio-section { margin-top: 2rem; border-top: 1px solid #eee; padding-top: 1.5rem; display: none; }
        audio { width: 100%; }
        .status { margin-top: 10px; font-size: 13px; color: #888; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Gemini 2.0 TTS</h1>
        <p>Convert your text to natural AI voice</p>
        
        <textarea id="textInput" placeholder="Write something here...">Salam! Main Gemini AI hoon. Main aapki kaise madad kar sakta hoon?</textarea>
        
        <select id="voiceSelect">
            <option value="Aoede">Aoede (Female - Natural)</option>
            <option value="Puck">Puck (Male - Energetic)</option>
            <option value="Charon">Charon (Male - Deep Voice)</option>
            <option value="Kore">Kore (Female - Soft)</option>
            <option value="Fenrir">Fenrir (Male - Strong)</option>
        </select>

        <button id="generateBtn">Generate Voice</button>
        <div id="status" class="status"></div>

        <div id="audioSection" class="audio-section">
            <audio id="audioPlayer" controls></audio>
            <p style="margin-top:10px;">Audio is ready!</p>
        </div>
    </div>

    <script>
        const btn = document.getElementById('generateBtn');
        const textInput = document.getElementById('textInput');
        const voiceSelect = document.getElementById('voiceSelect');
        const audioSection = document.getElementById('audioSection');
        const audioPlayer = document.getElementById('audioPlayer');
        const status = document.getElementById('status');

        btn.onclick = async () => {
            const text = textInput.value.trim();
            if (!text) return alert("Please enter text");

            btn.disabled = true;
            status.innerText = "Processing with Gemini 2.0...";
            audioSection.style.display = "none";

            try {
                const response = await fetch('/tts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: text, voice: voiceSelect.value })
                });

                if (!response.ok) throw new Error("API Limit reached or Error");

                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                audioPlayer.src = url;
                audioSection.style.display = "block";
                audioPlayer.play();
                status.innerText = "";
            } catch (err) {
                status.innerText = "Error: " + err.message;
                alert("Error: Check your API Key or Network");
            } finally {
                btn.disabled = false;
            }
        };
    </script>
</body>
</html>
"""

def pcm_to_wav(pcm_data, sample_rate=24000, channels=1, sample_width=2):
    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data)
    return wav_io.getvalue()

@app.route('/')
def index():
    # Browser mein ab khoobsurat UI dikhega
    return render_template_string(HTML_UI)

@app.route('/tts', methods=['POST'])
def tts():
    if not API_KEY:
        return jsonify({"error": "GEMINI_API_KEY environment variable is missing"}), 500
    
    try:
        client = genai.Client(api_key=API_KEY)
        data = request.json
        text = data.get('text', 'Hello.')
        voice = data.get('voice', 'Aoede') 

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                    )
                )
            )
        )
        
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                audio_wav = pcm_to_wav(part.inline_data.data)
                return Response(audio_wav, mimetype='audio/wav')
        
        return jsonify({"error": "No audio content generated"}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

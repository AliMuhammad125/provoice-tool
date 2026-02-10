import os
import io
import wave
from flask import Flask, request, Response, jsonify, render_template_string
from google import genai
from google.genai import types

app = Flask(__name__)

# API Key from Environment Variable
API_KEY = os.environ.get("GEMINI_API_KEY")

# --- HTML INTERFACE ---
HTML_UI = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gemini 2.0 High-Quality TTS</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .container { background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); width: 100%; max-width: 500px; text-align: center; }
        h1 { color: #1a73e8; margin-bottom: 1rem; }
        textarea { width: 100%; height: 120px; padding: 10px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; resize: none; box-sizing: border-box; }
        select, button { width: 100%; padding: 12px; margin-top: 1rem; border-radius: 8px; border: none; font-size: 16px; cursor: pointer; }
        select { background-color: #f1f3f4; border: 1px solid #ddd; }
        button { background-color: #1a73e8; color: white; font-weight: bold; transition: background 0.3s; }
        button:hover { background-color: #1557b0; }
        button:disabled { background-color: #ccc; cursor: not-allowed; }
        audio { width: 100%; margin-top: 1.5rem; }
        .status { margin-top: 10px; font-size: 14px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Gemini TTS</h1>
        <textarea id="textInput" placeholder="Yahan apna text likhein...">Hello! I am Gemini 2.0. How can I help you today?</textarea>
        
        <select id="voiceSelect">
            <option value="Aoede">Aoede (Female - Natural)</option>
            <option value="Puck">Puck (Male - Energetic)</option>
            <option value="Charon">Charon (Male - Deep)</option>
            <option value="Kore">Kore (Female - Soft)</option>
            <option value="Fenrir">Fenrir (Male - Strong)</option>
        </select>

        <button id="generateBtn">Generate Voice</button>
        <div id="status" class="status"></div>
        <audio id="audioPlayer" controls style="display:none;"></audio>
    </div>

    <script>
        const btn = document.getElementById('generateBtn');
        const textInput = document.getElementById('textInput');
        const voiceSelect = document.getElementById('voiceSelect');
        const audioPlayer = document.getElementById('audioPlayer');
        const status = document.getElementById('status');

        btn.onclick = async () => {
            const text = textInput.value.trim();
            if (!text) return alert("Please enter some text");

            btn.disabled = true;
            status.innerText = "Generating audio... Please wait.";
            audioPlayer.style.display = "none";

            try {
                const response = await fetch('/tts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: text, voice: voiceSelect.value })
                });

                if (!response.ok) throw new Error("API Error");

                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                audioPlayer.src = url;
                audioPlayer.style.display = "block";
                audioPlayer.play();
                status.innerText = "Done!";
            } catch (err) {
                status.innerText = "Error: " + err.message;
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
    # Ab browser mein UI dikhega JSON ki jagah
    return render_template_string(HTML_UI)

@app.route('/tts', methods=['POST'])
def tts():
    if not API_KEY:
        return jsonify({"error": "GEMINI_API_KEY missing"}), 500
    
    try:
        client = genai.Client(api_key=API_KEY)
        data = request.json
        text = data.get('text', '')
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
        
        return jsonify({"error": "No audio"}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

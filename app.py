import os
import io
import wave
from flask import Flask, request, Response, jsonify, render_template_string
from google import genai
from google.genai import types

app = Flask(__name__)

API_KEY = os.environ.get("GEMINI_API_KEY")

HTML_UI = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gemini 2.0 TTS</title>
    <style>
        body { font-family: sans-serif; background: #f0f2f5; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .container { background: white; padding: 30px; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); width: 400px; text-align: center; }
        textarea { width: 100%; height: 100px; padding: 10px; border-radius: 8px; border: 1px solid #ccc; box-sizing: border-box; }
        button { width: 100%; padding: 12px; margin-top: 15px; background: #007bff; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; }
        button:disabled { background: #ccc; }
        .status { margin-top: 15px; color: #666; font-size: 14px; }
        audio { width: 100%; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Gemini 2.0 TTS</h2>
        <textarea id="textInput" placeholder="Enter text...">Hello! How are you doing today?</textarea>
        <select id="voiceSelect" style="width:100%; padding:10px; margin-top:10px;">
            <option value="Aoede">Aoede (Female)</option>
            <option value="Puck">Puck (Male)</option>
            <option value="Charon">Charon (Deep)</option>
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
            btn.disabled = true;
            document.getElementById('status').innerText = "Generating...";
            try {
                const res = await fetch('/tts', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({text, voice})
                });
                const data = await res.json();
                if (data.error) throw new Error(data.error);
                
                const audioRes = await fetch('data:audio/wav;base64,' + data.audio);
                const blob = await audioRes.blob();
                document.getElementById('player').src = URL.createObjectURL(blob);
                document.getElementById('player').style.display = "block";
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
        return jsonify({"error": "API Key not found in Environment"}), 500
    
    try:
        data = request.json
        text = data.get('text', 'Hello')
        voice = data.get('voice', 'Aoede')

        client = genai.Client(api_key=API_KEY)
        
        # MODEL NAME: Try 'gemini-2.0-flash' or 'gemini-2.0-flash-exp'
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
        
        import base64
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                audio_wav = pcm_to_wav(part.inline_data.data)
                # Base64 mein convert kar rahe hain taaki JSON mein bhej saken
                encoded_audio = base64.b64encode(audio_wav).decode('utf-8')
                return jsonify({"audio": encoded_audio})
        
        return jsonify({"error": "No audio parts in response"}), 400

    except Exception as e:
        print(f"DEBUG ERROR: {str(e)}") # Ye Render Logs mein dikhayega
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

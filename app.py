import os
import io
import wave
from flask import Flask, request, Response, jsonify
from google import genai
from google.genai import types

app = Flask(__name__)

# Render par API Key yahan hardcode nahi karni chahiye
# Hum Environment Variables use karenge
API_KEY = os.environ.get("GEMINI_API_KEY")

def pcm_to_wav(pcm_data, sample_rate=24000, channels=1, sample_width=2):
    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data)
    return wav_io.getvalue()

@app.route('/tts', methods=['POST'])
def tts():
    if not API_KEY:
        return jsonify({"error": "GEMINI_API_KEY environment variable is missing"}), 500
    
    try:
        client = genai.Client(api_key=API_KEY)
        data = request.json
        text = data.get('text', 'Hello from Gemini.')
        voice = data.get('voice', 'Aoede') 

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice
                        )
                    )
                )
            )
        )
        
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                raw_pcm = part.inline_data.data
                audio_wav = pcm_to_wav(raw_pcm)
                return Response(
                    audio_wav,
                    mimetype='audio/wav',
                    headers={'Content-Disposition': 'attachment; filename=voice.wav'}
                )
        
        return jsonify({"error": "No audio content generated"}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return "Gemini 2.0 Flash TTS is running on Render!"

if __name__ == '__main__':
    # Render automatically $PORT variable deta hai
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

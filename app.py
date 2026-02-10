import os
import io
import wave
from flask import Flask, request, Response, jsonify
from google import genai
from google.genai import types

app = Flask(__name__)

# --- CONFIGURATION ---
# Yahan apni Google AI Studio wali free API key lagayein
# (Aapko Google Cloud Console ya credit card ki zarurat nahi!)
API_KEY = "AIzaSyAgU-0zlcnk7Et65pJjYPryBq2XGqIPlV4"

# Initialize the new Gemini Client
client = genai.Client(api_key=API_KEY)

def pcm_to_wav(pcm_data, sample_rate=24000, channels=1, sample_width=2):
    """Gemini raw PCM audio return karta hai, is function se hum usay WAV format mein convert karte hain"""
    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data)
    return wav_io.getvalue()

def generate_gemini_audio(text, voice_name="Aoede"):
    """
    Directly generates audio using Gemini 2.0 Flash.
    Available Voices: Aoede, Puck, Charon, Kore, Fenrir
    """
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=text,
        config=types.GenerateContentConfig(
            # Ye API ko batata hai ke humein text nahi, Awaz (Audio) chahiye!
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            )
        )
    )
    
    # Extract raw audio bytes from the response
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            # Raw PCM data ko .wav file format mein convert karein
            raw_pcm = part.inline_data.data
            return pcm_to_wav(raw_pcm)
            
    raise Exception("Audio data not found in Gemini's response")

@app.route('/tts', methods=['POST'])
def tts():
    try:
        data = request.json
        text = data.get('text', 'Hello, this is my new voice from Gemini 2.0.')
        
        # Default voice 'Aoede' hai. Lekin aap JSON me "voice": "Puck" wagera bhi bhej sakte hain
        voice = data.get('voice', 'Aoede') 
        
        # Audio generate karein
        audio_wav = generate_gemini_audio(text, voice)
        
        # Return as WAV file
        return Response(
            audio_wav,
            mimetype='audio/wav',
            headers={'Content-Disposition': 'attachment; filename=gemini_voice.wav'}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return jsonify({
        "status": "Gemini 2.0 Flash Native Audio is Active! (Free Tier)",
        "message": "Send a POST request to /tts",
        "available_voices": ["Aoede", "Puck", "Charon", "Kore", "Fenrir"]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

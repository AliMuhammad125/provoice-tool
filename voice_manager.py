"""
Voice Manager for Piper TTS
"""
import os
import requests
import threading

class VoiceManager:
    def __init__(self, voices_dir="voices"):
        self.voices_dir = voices_dir
        os.makedirs(voices_dir, exist_ok=True)
        
        # Available Piper voices
        self.available_voices = {
            'en_US-lessac-medium': {
                'url': 'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx',
                'language': 'English (US)',
                'gender': 'Male',
                'description': 'Clear American English'
            },
            'en_US-kathleen-medium': {
                'url': 'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/kathleen/medium/en_US-kathleen-medium.onnx',
                'language': 'English (US)',
                'gender': 'Female',
                'description': 'American English female'
            },
            'en_US-vctk-medium': {
                'url': 'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/vctk/medium/en_US-vctk-medium.onnx',
                'language': 'English (US)',
                'gender': 'Male',
                'description': 'Horror/creepy voice'
            },
            'en_GB-semaine-medium': {
                'url': 'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/semaine/medium/en_GB-semaine-medium.onnx',
                'language': 'English (UK)',
                'gender': 'Male',
                'description': 'British English news style'
            },
            'hi_IN-medium': {
                'url': 'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/hi/hi_IN/medium/hi_IN-medium.onnx',
                'language': 'Hindi',
                'gender': 'Male',
                'description': 'Hindi voice'
            },
            'ur_PK-medium': {
                'url': 'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/ur/ur_PK/medium/ur_PK-medium.onnx',
                'language': 'Urdu',
                'gender': 'Male',
                'description': 'Urdu voice'
            },
        }
    
    def download_voice(self, voice_name, background=True):
        """Download a voice model"""
        if voice_name not in self.available_voices:
            return False
        
        voice_info = self.available_voices[voice_name]
        url = voice_info['url']
        file_path = os.path.join(self.voices_dir, f"{voice_name}.onnx")
        
        # Check if already downloaded
        if os.path.exists(file_path):
            print(f"✅ Voice already exists: {voice_name}")
            return True
        
        print(f"📥 Downloading voice: {voice_name}")
        
        if background:
            # Download in background thread
            thread = threading.Thread(
                target=self._download_file,
                args=(url, file_path, voice_name)
            )
            thread.daemon = True
            thread.start()
            return True
        else:
            # Download immediately
            return self._download_file(url, file_path, voice_name)
    
    def _download_file(self, url, file_path, voice_name):
        """Download file helper"""
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r⬇️  Downloading {voice_name}: {percent:.1f}%", end='')
            
            print(f"\n✅ Downloaded: {voice_name}")
            return True
            
        except Exception as e:
            print(f"\n❌ Failed to download {voice_name}: {e}")
            # Clean up partial download
            if os.path.exists(file_path):
                os.remove(file_path)
            return False
    
    def get_voice_path(self, voice_name):
        """Get path to voice file"""
        file_path = os.path.join(self.voices_dir, f"{voice_name}.onnx")
        return file_path if os.path.exists(file_path) else None
    
    def list_available_voices(self):
        """List all available voices"""
        return list(self.available_voices.keys())
    
    def list_downloaded_voices(self):
        """List downloaded voices"""
        downloaded = []
        for f in os.listdir(self.voices_dir):
            if f.endswith('.onnx'):
                downloaded.append(f.replace('.onnx', ''))
        return downloaded
    
    def get_voice_info(self, voice_name):
        """Get information about a voice"""
        return self.available_voices.get(voice_name)

# Singleton instance
voice_manager = VoiceManager()

if __name__ == "__main__":
    vm = VoiceManager()
    print("Available voices:", vm.list_available_voices())
    print("Downloaded voices:", vm.list_downloaded_voices())

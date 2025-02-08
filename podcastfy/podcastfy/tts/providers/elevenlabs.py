"""ElevenLabs TTS provider implementation."""
import base64

from elevenlabs import client as elevenlabs_client
from ..base import TTSProvider
from typing import List

class ElevenLabsTTS(TTSProvider):
    def __init__(self, api_key: str, model: str = "eleven_multilingual_v2"):
        """
        Initialize ElevenLabs TTS provider.
        
        Args:
            api_key (str): ElevenLabs API key
            model (str): Model name to use. Defaults to "eleven_multilingual_v2"
        """
        self.client = elevenlabs_client.ElevenLabs(api_key=api_key)
        self.model = model
        
    def generate_audio(self, text: str, voice: str, model: str, voice2: str = None) -> dict:
        """Generate audio using ElevenLabs API."""
        """         
        audio = self.client.generate(
            text=text,
            voice=voice,
            model=model
        )
        """
        # potentially have to randomise voice?  https://api.elevenlabs.io/v1/voices https://github.com/elevenlabs/elevenlabs-python/blob/main/reference.md
        audio_with_transcript = self.client.text_to_speech.convert_with_timestamps(
            text=text,
            voice=voice,
            model=model
        )

        # " " split it up by space for transcription purposes.
        #audio_with_transcript.alignment (is an array of characters)
        words = []

        characters = audio_with_transcript["normalized_alignment"]["characters"]
        start_times = audio_with_transcript["normalized_alignment"]["character_start_times_seconds"]
        end_times = audio_with_transcript["normalized_alignment"]["character_end_times_seconds"]

        words = []
        current_word = ""
        word_start = None

        word_data = []

        for i, char in enumerate(characters):
            if char != " ":
                if current_word == "":
                    word_start = start_times[i]
                current_word += char
            else:
                if current_word:
                    word_data.append({
                        "word": current_word,
                        "start_time": word_start,
                        "end_time": end_times[i - 1]
                    })
                    current_word = ""

        if current_word:
            word_data.append({
                "word": current_word,
                "start_time": word_start,
                "end_time": end_times[-1]
            })

        audio_data = audio_with_transcript.audio_base64.encode()
        audio_content = base64.b64decode(audio_data)

        #return b''.join(chunk for chunk in audio if chunk)
        return {'audio': audio_content, 'transcript': word_data}
        
    def get_supported_tags(self) -> List[str]:
        """Get supported SSML tags."""
        return ['lang', 'p', 'phoneme', 's', 'sub'] 
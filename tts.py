"""
Text-to-Speech module using Kokoro TTS
Optimized for CPU with streaming support
"""
import logging
import io
import os
import numpy as np
from typing import AsyncGenerator, Optional
from kokoro_onnx import Kokoro
from config import settings

logger = logging.getLogger(__name__)


class TextToSpeech:
    """Text-to-Speech processor using Kokoro TTS"""

    def __init__(self):
        """Initialize Kokoro TTS pipeline"""
        logger.info(f"Loading Kokoro TTS with voice: {settings.TTS_VOICE}")

        # Get paths from settings
        model_path = settings.TTS_MODEL_PATH
        voices_path = settings.TTS_VOICES_PATH
        
        # Check if files exist
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model file not found at {model_path}\n"
                "Download it from: https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx"
            )
        
        if not os.path.exists(voices_path):
            raise FileNotFoundError(
                f"Voices file not found at {voices_path}\n"
                "Download it from: https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"
            )

        # Initialize Kokoro - CORRECT ORDER: model_path, voices_path
        self.kokoro = Kokoro(model_path, voices_path)
        self.voice = settings.TTS_VOICE
        self.speed = settings.TTS_SPEED

        logger.info("Kokoro TTS loaded successfully")

    def synthesize(self, text: str) -> Optional[bytes]:
        """
        Synthesize speech from text

        Args:
            text: Text to synthesize

        Returns:
            Audio bytes (WAV format) or None if synthesis fails
        """
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided for synthesis")
                return None

            logger.info(f"Synthesizing: {text[:100]}...")

            # Generate audio using Kokoro with voice parameter
            audio, sample_rate = self.kokoro.create(
                text, 
                voice=self.voice,
                speed=self.speed
            )

            # Convert to WAV bytes
            audio_bytes = self._to_wav_bytes(audio, sample_rate)
            return audio_bytes

        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            return None

    async def synthesize_stream(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        Synthesize speech with streaming support
        Splits text into sentences for progressive synthesis

        Args:
            text: Text to synthesize

        Yields:
            Audio bytes chunks
        """
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided for streaming synthesis")
                return

            # Split text into sentences for streaming
            sentences = self._split_sentences(text)

            for sentence in sentences:
                if sentence.strip():
                    audio_bytes = self.synthesize(sentence)
                    if audio_bytes:
                        yield audio_bytes

        except Exception as e:
            logger.error(f"TTS streaming error: {e}")

    def _split_sentences(self, text: str) -> list:
        """
        Split text into sentences for streaming

        Args:
            text: Input text

        Returns:
            List of sentences
        """
        import re

        # Split on sentence boundaries (., !, ?)
        sentences = re.split(r'([.!?]+)', text)

        # Recombine punctuation with sentences
        result = []
        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i].strip()
            punct = sentences[i + 1] if i + 1 < len(sentences) else ""
            if sentence:
                result.append(sentence + punct)

        # Add last sentence if it doesn't end with punctuation
        if len(sentences) % 2 == 1 and sentences[-1].strip():
            result.append(sentences[-1].strip())

        return result

    def _to_wav_bytes(self, audio: np.ndarray, sample_rate: int = 24000) -> bytes:
        """
        Convert audio numpy array to WAV bytes

        Args:
            audio: Audio numpy array
            sample_rate: Sample rate

        Returns:
            WAV format bytes
        """
        import wave

        # Normalize audio to int16
        audio = np.clip(audio, -1.0, 1.0)
        audio_int16 = (audio * 32767).astype(np.int16)

        # Create WAV file in memory
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())

        return buffer.getvalue()

    def synthesize_to_file(self, text: str, output_path: str) -> bool:
        """
        Synthesize speech and save to file

        Args:
            text: Text to synthesize
            output_path: Output file path

        Returns:
            True if successful, False otherwise
        """
        try:
            audio_bytes = self.synthesize(text)
            if audio_bytes:
                with open(output_path, 'wb') as f:
                    f.write(audio_bytes)
                logger.info(f"Audio saved to {output_path}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to save audio: {e}")
            return False


# Global TTS instance
_tts_instance: Optional[TextToSpeech] = None


def get_tts() -> TextToSpeech:
    """Get or create the global TTS instance"""
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = TextToSpeech()
    return _tts_instance
"""
Speech-to-Text module using Faster-Whisper
Optimized for CPU with int8 quantization
"""
import logging
from typing import Optional
from faster_whisper import WhisperModel
from config import settings

logger = logging.getLogger(__name__)


class SpeechToText:
    """Speech-to-Text processor using Faster-Whisper"""

    def __init__(self):
        """Initialize Faster-Whisper model with CPU optimization"""
        logger.info(
            f"Loading Faster-Whisper model: {settings.WHISPER_MODEL} "
            f"with {settings.WHISPER_COMPUTE_TYPE} quantization"
        )

        # Initialize model with CPU optimization (int8 quantization)
        self.model = WhisperModel(
            settings.WHISPER_MODEL,
            device="cpu",
            compute_type=settings.WHISPER_COMPUTE_TYPE,
            cpu_threads=4,  # Optimize for VPS
        )

        logger.info("Faster-Whisper model loaded successfully")

    def transcribe(self, audio_path: str) -> Optional[str]:
        """
        Transcribe audio file to text

        Args:
            audio_path: Path to audio file

        Returns:
            Transcribed text or None if transcription fails
        """
        try:
            segments, info = self.model.transcribe(
                audio_path,
                language=settings.WHISPER_LANGUAGE,
                beam_size=5,
                vad_filter=True,  # Voice Activity Detection
                vad_parameters={
                    "threshold": 0.5,
                    "min_speech_duration_ms": 250,
                },
            )

            # Combine all segments into a single text
            transcription = " ".join([segment.text.strip() for segment in segments])

            logger.info(f"Transcription: {transcription}")
            return transcription.strip() if transcription else None

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None

    def transcribe_stream(self, audio_data: bytes) -> Optional[str]:
        """
        Transcribe audio data from memory

        Args:
            audio_data: Raw audio bytes

        Returns:
            Transcribed text or None if transcription fails
        """
        import tempfile
        import os

        try:
            # Save audio data to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name

            # Transcribe the temporary file
            transcription = self.transcribe(temp_path)

            # Clean up temporary file
            os.unlink(temp_path)

            return transcription

        except Exception as e:
            logger.error(f"Stream transcription error: {e}")
            return None


# Global STT instance
_stt_instance: Optional[SpeechToText] = None


def get_stt() -> SpeechToText:
    """Get or create the global STT instance"""
    global _stt_instance
    if _stt_instance is None:
        _stt_instance = SpeechToText()
    return _stt_instance

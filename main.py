"""
LiveKit Voice Agent with Local Models (Advanced Implementation)
Complete audio pipeline with VAD, buffering, and streaming
"""
import asyncio
import logging
import io
import wave
import numpy as np
from typing import Optional
from collections import deque

from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
)

from config import settings, GREETING_RESPONSES
from rag import get_rag
from stt import get_stt
from llm import get_llm
from tts import get_tts

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VoiceActivityDetector:
    """Simple Voice Activity Detection using energy threshold"""
    
    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
        energy_threshold: float = 0.01,
        speech_pad_ms: int = 300,
    ):
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        self.energy_threshold = energy_threshold
        self.speech_pad_frames = int(speech_pad_ms / frame_duration_ms)
        
        self.is_speech = False
        self.speech_frames = 0
        self.silence_frames = 0
        
    def process_frame(self, audio_frame: np.ndarray) -> bool:
        """
        Process audio frame and return True if speech is detected
        
        Args:
            audio_frame: Audio data as numpy array
            
        Returns:
            True if currently in speech segment
        """
        # Calculate energy (RMS)
        energy = np.sqrt(np.mean(audio_frame ** 2))
        
        if energy > self.energy_threshold:
            self.speech_frames += 1
            self.silence_frames = 0
            
            if self.speech_frames >= 3:  # 3 frames of speech
                self.is_speech = True
        else:
            self.silence_frames += 1
            
            if self.silence_frames >= self.speech_pad_frames:
                self.is_speech = False
                self.speech_frames = 0
        
        return self.is_speech
    
    def reset(self):
        """Reset VAD state"""
        self.is_speech = False
        self.speech_frames = 0
        self.silence_frames = 0


class AudioBuffer:
    """Buffer for collecting audio frames"""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.frames = deque()
        self.max_duration_ms = 10000  # 10 seconds max
        self.max_frames = int(sample_rate * self.max_duration_ms / 1000)
        
    def add_frame(self, frame: np.ndarray):
        """Add audio frame to buffer"""
        self.frames.append(frame)
        
        # Prevent buffer overflow
        total_samples = sum(len(f) for f in self.frames)
        while total_samples > self.max_frames and len(self.frames) > 0:
            removed = self.frames.popleft()
            total_samples -= len(removed)
    
    def get_audio(self) -> Optional[bytes]:
        """Get buffered audio as WAV bytes"""
        if not self.frames:
            return None
        
        try:
            # Concatenate all frames
            audio_data = np.concatenate(list(self.frames))
            
            # Convert to int16
            audio_int16 = (audio_data * 32767).astype(np.int16)
            
            # Create WAV file in memory
            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio_int16.tobytes())
            
            return buffer.getvalue()
        
        except Exception as e:
            logger.error(f"Error converting audio buffer: {e}")
            return None
    
    def clear(self):
        """Clear buffer"""
        self.frames.clear()


class VoiceAgent:
    """Voice agent with local STT, LLM, TTS"""
    
    def __init__(self, stt, llm, tts, rag):
        self.stt = stt
        self.llm = llm
        self.tts = tts
        self.rag = rag
        
        self.vad = VoiceActivityDetector()
        self.audio_buffer = AudioBuffer()
        
        self.is_processing = False
        self.audio_source: Optional[rtc.AudioSource] = None
        self.audio_track: Optional[rtc.LocalAudioTrack] = None
        
    async def setup_audio_track(self, room: rtc.Room):
        """Setup audio track for sending responses"""
        self.audio_source = rtc.AudioSource(24000, 1)
        self.audio_track = rtc.LocalAudioTrack.create_audio_track(
            "assistant_voice",
            self.audio_source
        )
        options = rtc.TrackPublishOptions()
        options.source = rtc.TrackSource.SOURCE_MICROPHONE
        await room.local_participant.publish_track(self.audio_track, options)
        logger.info("Audio track published")
    
    async def send_greeting(self):
        """Send initial greeting"""
        await self.speak(GREETING_RESPONSES[0])
    
    async def speak(self, text: str):
        """Convert text to speech and send audio"""
        try:
            logger.info(f"Speaking: {text}")
            
            # Generate audio
            audio_bytes = self.tts.synthesize(text)
            if not audio_bytes:
                logger.error("TTS synthesis failed")
                return
            
            # Parse WAV file
            wav_io = io.BytesIO(audio_bytes)
            with wave.open(wav_io, 'rb') as wav:
                sample_rate = wav.getframerate()
                n_channels = wav.getnchannels()
                frames_data = wav.readframes(wav.getnframes())
            
            # Convert to numpy array
            audio_array = np.frombuffer(frames_data, dtype=np.int16)
            
            # Send in chunks
            chunk_size = sample_rate // 10  # 100ms chunks
            for i in range(0, len(audio_array), chunk_size):
                chunk = audio_array[i:i + chunk_size]
                
                frame = rtc.AudioFrame(
                    data=chunk.tobytes(),
                    sample_rate=sample_rate,
                    num_channels=n_channels,
                    samples_per_channel=len(chunk)
                )
                
                await self.audio_source.capture_frame(frame)
                await asyncio.sleep(0.1)  # 100ms between chunks
            
            logger.info("Audio sent successfully")
            
        except Exception as e:
            logger.error(f"Error in speak: {e}")
    
    async def process_audio_frame(self, frame: rtc.AudioFrame):
        """Process incoming audio frame"""
        try:
            # Convert to numpy array
            audio_data = np.frombuffer(frame.data, dtype=np.int16)
            audio_float = audio_data.astype(np.float32) / 32768.0
            
            # Check for speech
            is_speech = self.vad.process_frame(audio_float)
            
            if is_speech:
                self.audio_buffer.add_frame(audio_float)
            elif not is_speech and len(self.audio_buffer.frames) > 0:
                # Speech ended, process buffered audio
                if not self.is_processing:
                    await self.process_speech()
        
        except Exception as e:
            logger.error(f"Error processing audio frame: {e}")
    
    async def process_speech(self):
        """Process buffered speech"""
        self.is_processing = True
        
        try:
            # Get audio from buffer
            audio_bytes = self.audio_buffer.get_audio()
            self.audio_buffer.clear()
            
            if not audio_bytes:
                return
            
            # Transcribe
            logger.info("Transcribing...")
            transcription = self.stt.transcribe_stream(audio_bytes)
            
            if not transcription or not transcription.strip():
                logger.info("No transcription")
                return
            
            logger.info(f"User said: {transcription}")
            
            # Check for greetings
            lower_text = transcription.lower()
            if any(kw in lower_text for kw in settings.GREETING_KEYWORDS):
                await self.speak(GREETING_RESPONSES[0])
                return
            
            if any(kw in lower_text for kw in settings.THANKS_KEYWORDS):
                await self.speak("Je vous en prie!")
                return
            
            if any(kw in lower_text for kw in settings.GOODBYE_KEYWORDS):
                await self.speak("Au revoir!")
                return
            
            # Search knowledge base
            logger.info("Searching knowledge base...")
            documents = await self.rag.retrieve(transcription)
            
            context = None
            if documents:
                context = self.rag.format_context(documents)
                logger.info(f"Found {len(documents)} documents")
            
            # Generate response
            logger.info("Generating response...")
            response = await self.llm.get_response(transcription, context)
            
            # Speak response
            await self.speak(response)
            
        except Exception as e:
            logger.error(f"Error processing speech: {e}")
            await self.speak("Désolé, une erreur s'est produite.")
        
        finally:
            self.is_processing = False
            self.vad.reset()


def prewarm(proc: JobProcess):
    """Prewarm models"""
    logger.info("Prewarming models...")
    proc.userdata["stt"] = get_stt()
    proc.userdata["llm"] = get_llm()
    proc.userdata["tts"] = get_tts()
    proc.userdata["rag"] = get_rag()
    logger.info("Models prewarmed successfully")


async def entrypoint(ctx: JobContext):
    """Main agent entrypoint"""
    logger.info("Starting voice agent...")

    # Get prewarmed instances
    stt = ctx.proc.userdata["stt"]
    llm = ctx.proc.userdata["llm"]
    tts = ctx.proc.userdata["tts"]
    rag = ctx.proc.userdata["rag"]

    # Create voice agent
    agent = VoiceAgent(stt, llm, tts, rag)

    # Connect to room
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info(f"Connected to room: {ctx.room.name}")

    # Setup audio output
    await agent.setup_audio_track(ctx.room)

    # Wait for participant
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant joined: {participant.identity}")

    # Send greeting
    await agent.send_greeting()

    # Handle audio tracks
    @ctx.room.on("track_subscribed")
    def on_track_subscribed(
        track: rtc.Track,
        publication: rtc.TrackPublication,
        participant: rtc.RemoteParticipant,
    ):
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            logger.info("Audio track subscribed, starting audio processing")
            asyncio.create_task(process_track(track, agent))

    # Check existing tracks
    for publication in participant.track_publications.values():
        if publication.subscribed and publication.track.kind == rtc.TrackKind.KIND_AUDIO:
            logger.info("Processing existing audio track")
            asyncio.create_task(process_track(publication.track, agent))

    logger.info("Agent ready - waiting for voice input...")


async def process_track(track: rtc.Track, agent: VoiceAgent):
    """Process audio track"""
    try:
        audio_stream = rtc.AudioStream(track, sample_rate=16000, num_channels=1)
        
        async for frame_event in audio_stream:
            # Extract the actual frame from the event
            await agent.process_audio_frame(frame_event.frame)
    
    except Exception as e:
        logger.error(f"Error processing track: {e}")


def main():
    """Run the agent"""
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            api_key=settings.LIVEKIT_API_KEY,
            api_secret=settings.LIVEKIT_API_SECRET,
            ws_url=settings.LIVEKIT_URL,
        )
    )


if __name__ == "__main__":
    main()
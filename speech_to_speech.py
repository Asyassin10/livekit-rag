import asyncio
import json
import logging
import io
import tempfile
import os
import wave
import numpy as np
import httpx
from faster_whisper import WhisperModel
from kokoro_onnx import Kokoro
from qdrant_client import QdrantClient
from config import settings, SYSTEM_PROMPT
import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SpeechToSpeechRAG:
    def __init__(self):
        logger.info("Initializing Speech-to-Speech RAG system")

        # Whisper - optimized for speed
        self.whisper_model = WhisperModel(
            settings.WHISPER_MODEL,
            device="cpu",
            compute_type="int8",
            cpu_threads=os.cpu_count() or 4,
        )
        logger.info("Whisper model loaded")

        self.kokoro = Kokoro(settings.TTS_MODEL_PATH, settings.TTS_VOICES_PATH)
        logger.info("Kokoro TTS loaded")

        self.qdrant_client = QdrantClient(url=settings.QDRANT_URL)
        self.collection_name = settings.QDRANT_COLLECTION
        
        # Reusable HTTP client
        self.http_client = httpx.AsyncClient(timeout=60.0)
        
        # OpenRouter for embeddings
        self.openrouter_url = "https://openrouter.ai/api/v1/embeddings"
        self.openrouter_headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        
        # Ollama for LLM
        self.ollama_url = "http://localhost:11434/api/chat"
        
        logger.info("All services initialized")

    def transcribe_audio(self, audio_bytes: bytes) -> str:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name

        try:
            segments, _ = self.whisper_model.transcribe(
                temp_path,
                language="fr",
                beam_size=3,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=300),
            )
            return " ".join(s.text.strip() for s in segments).strip()
        finally:
            os.unlink(temp_path)

    async def get_embedding(self, text: str):
        response = await self.http_client.post(
            self.openrouter_url,
            headers=self.openrouter_headers,
            json={"model": settings.EMBEDDING_MODEL, "input": text},
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]

    async def search_qdrant(self, query: str):
        query_embedding = await self.get_embedding(query)
        
        results = self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=settings.RAG_TOP_K,
            score_threshold=settings.RAG_SCORE_THRESHOLD,
        )

        return [
            {"text": r.payload.get("text", ""), "score": r.score}
            for r in results.points
        ]

    def format_context(self, documents):
        if not documents:
            return None
        return "\n\n".join(
            f"[Document {i}]: {doc['text'].strip()}"
            for i, doc in enumerate(documents, 1)
            if doc.get("text", "").strip()
        )

    async def generate_response(self, user_message: str, context: str = None):
        if context:
            user_prompt = f"Contexte:\n{context}\n\nQuestion: {user_message}"
        else:
            user_prompt = user_message

        response = await self.http_client.post(
            self.ollama_url,
            json={
                "model": "qwen2.5:7b",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "options": {
                    "temperature": settings.LLM_TEMPERATURE,
                    "num_predict": settings.LLM_MAX_TOKENS,
                }
            },
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]

    def synthesize_speech(self, text: str) -> bytes:
        audio, sample_rate = self.kokoro.create(
            text,
            voice=settings.TTS_VOICE,
            speed=settings.TTS_SPEED,
            lang="fr-fr",
        )

        audio = np.clip(audio, -1.0, 1.0)
        audio_int16 = (audio * 32767).astype(np.int16)

        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(audio_int16.tobytes())
        return buffer.getvalue()

    async def process_voice(self, audio_bytes: bytes):
        logger.info("Transcribing...")
        transcription = self.transcribe_audio(audio_bytes)

        if not transcription:
            return None, None

        logger.info(f"User: {transcription}")

        logger.info("Searching...")
        documents = await self.search_qdrant(transcription)
        context = self.format_context(documents)
        
        if documents:
            logger.info(f"Found {len(documents)} docs")

        logger.info("Generating with Qwen2.5...")
        response_text = await self.generate_response(transcription, context)
        logger.info(f"Assistant: {response_text}")

        logger.info("Synthesizing...")
        audio = self.synthesize_speech(response_text)

        return audio, {"user": transcription, "assistant": response_text}


# Global instance for reuse
rag_system = None


async def get_system():
    global rag_system
    if rag_system is None:
        rag_system = SpeechToSpeechRAG()
    return rag_system


async def handle_client(websocket):
    logger.info(f"Client connected: {websocket.remote_address}")
    system = await get_system()

    try:
        async for message in websocket:
            if isinstance(message, bytes):
                logger.info("Processing audio...")
                
                audio, transcript = await system.process_voice(message)

                if audio:
                    await websocket.send(json.dumps(transcript))
                    await websocket.send(audio)
                    logger.info("Response sent")
                else:
                    await websocket.send(json.dumps({"error": "No transcription"}))

    except websockets.exceptions.ConnectionClosed:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)


async def main():
    logger.info("Starting server on port 8765")
    
    # Pre-initialize system
    await get_system()
    
    async with websockets.serve(
        handle_client,
        "0.0.0.0",
        8765,
        max_size=10 * 1024 * 1024,
    ):
        logger.info("Server ready")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
import asyncio
import json
import logging
import io
import tempfile
import os
import wave
import numpy as np
from pathlib import Path
import httpx
from faster_whisper import WhisperModel
from groq import AsyncGroq
from kokoro_onnx import Kokoro
from qdrant_client import QdrantClient
from config import settings, SYSTEM_PROMPT
import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SpeechToSpeechRAG:
    def __init__(self):
        logger.info("Initializing Speech-to-Speech RAG system")

        self.whisper_model = WhisperModel(
            settings.WHISPER_MODEL,
            device="cpu",
            compute_type=settings.WHISPER_COMPUTE_TYPE,
            cpu_threads=4,
        )
        logger.info("Whisper model loaded")

        self.groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        logger.info("Groq client initialized")

        self.kokoro = Kokoro(settings.TTS_MODEL_PATH, settings.TTS_VOICES_PATH)
        logger.info("Kokoro TTS loaded")

        self.qdrant_client = QdrantClient(url=settings.QDRANT_URL)
        self.collection_name = settings.QDRANT_COLLECTION
        self.openrouter_url = "https://openrouter.ai/api/v1/embeddings"
        self.openrouter_headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        logger.info("Qdrant client connected")

    def transcribe_audio(self, audio_bytes: bytes) -> str:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name

        try:
            segments, _ = self.whisper_model.transcribe(
                temp_path,
                language=settings.WHISPER_LANGUAGE,
                beam_size=5,
                vad_filter=True,
            )
            transcription = " ".join([segment.text.strip() for segment in segments])
            return transcription.strip()
        finally:
            os.unlink(temp_path)

    async def get_embedding(self, text: str):
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.openrouter_url,
                headers=self.openrouter_headers,
                json={
                    "model": settings.EMBEDDING_MODEL,
                    "input": text,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]

    async def search_qdrant(self, query: str):
        query_embedding = await self.get_embedding(query)

        search_results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=settings.RAG_TOP_K,
            score_threshold=settings.RAG_SCORE_THRESHOLD,
        )

        documents = []
        for result in search_results:
            documents.append({
                "text": result.payload.get("text", ""),
                "score": result.score,
            })

        return documents

    def format_context(self, documents):
        if not documents:
            return None

        context_parts = []
        for i, doc in enumerate(documents, 1):
            text = doc.get("text", "").strip()
            if text:
                context_parts.append(f"[Document {i}]: {text}")

        return "\n\n".join(context_parts)

    async def generate_response(self, user_message: str, context: str = None):
        if context:
            user_prompt = f"""Contexte:
{context}

Question: {user_message}"""
        else:
            user_prompt = user_message

        response = await self.groq_client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )

        return response.choices[0].message.content

    def synthesize_speech(self, text: str) -> bytes:
        audio, sample_rate = self.kokoro.create(
            text,
            voice=settings.TTS_VOICE,
            speed=settings.TTS_SPEED
        )

        audio = np.clip(audio, -1.0, 1.0)
        audio_int16 = (audio * 32767).astype(np.int16)

        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())

        return buffer.getvalue()

    async def process_voice(self, audio_bytes: bytes):
        logger.info("Transcribing audio")
        transcription = self.transcribe_audio(audio_bytes)

        if not transcription:
            return None

        logger.info(f"User: {transcription}")

        logger.info("Searching knowledge base")
        documents = await self.search_qdrant(transcription)
        context = self.format_context(documents)

        if documents:
            logger.info(f"Found {len(documents)} documents")

        logger.info("Generating response")
        response_text = await self.generate_response(transcription, context)
        logger.info(f"Assistant: {response_text}")

        logger.info("Synthesizing speech")
        audio_response = self.synthesize_speech(response_text)

        return audio_response


async def handle_client(websocket, path):
    logger.info(f"Client connected from {websocket.remote_address}")

    system = SpeechToSpeechRAG()

    try:
        async for message in websocket:
            if isinstance(message, bytes):
                logger.info("Received audio data")

                audio_response = await system.process_voice(message)

                if audio_response:
                    await websocket.send(audio_response)
                    logger.info("Sent audio response")
                else:
                    await websocket.send(json.dumps({"error": "No transcription"}))
            else:
                logger.warning("Received non-binary message")

    except websockets.exceptions.ConnectionClosed:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Error: {e}")


async def main():
    logger.info("Starting WebSocket server on port 8765")

    async with websockets.serve(handle_client, "0.0.0.0", 8765):
        logger.info("Server ready - waiting for connections")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())

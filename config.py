"""
Configuration settings and prompts for the Speech-to-Speech RAG AI Assistant
"""
import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # API Keys
    GROQ_API_KEY: str
    OPENROUTER_API_KEY: str
    LIVEKIT_URL: str
    LIVEKIT_API_KEY: str
    LIVEKIT_API_SECRET: str

    # Qdrant Settings
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "harvard"

    # Model Settings
    WHISPER_MODEL: str = "small"
    WHISPER_LANGUAGE: str = "fr"
    WHISPER_COMPUTE_TYPE: str = "int8"

    EMBEDDING_MODEL: str = "openai/text-embedding-3-large"

    LLM_MODEL: str = "llama-3.1-8b-instant"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 150

    # TTS Settings - Kokoro
    TTS_VOICE: str = "af_sarah"  # Kokoro French voice
    TTS_SPEED: float = 1.0
    TTS_MODEL_PATH: str = "kokoro-models/kokoro-v1.0.int8.onnx"  # ADD THIS
    TTS_VOICES_PATH: str = "kokoro-models/voices-v1.0.bin"       # ADD THIS

    # RAG Settings
    RAG_TOP_K: int = 3
    RAG_SCORE_THRESHOLD: float = 0.7

    # Conversation Detection Keywords (French)
    GREETING_KEYWORDS: List[str] = [
        "bonjour", "salut", "hello", "hey", "coucou", "bonsoir"
    ]
    THANKS_KEYWORDS: List[str] = [
        "merci", "merci beaucoup", "je te remercie", "thank you"
    ]
    GOODBYE_KEYWORDS: List[str] = [
        "au revoir", "bye", "salut", "à bientôt", "à plus", "ciao"
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True


# System Prompt for LLM (French)
SYSTEM_PROMPT = """Tu es l'assistant vocal de Harvard. Réponds en français, 1-2 phrases max. Utilise uniquement le contexte fourni. Si pas d'info, dis: Je n'ai pas cette information."""

# Response templates for conversation detection
GREETING_RESPONSES = [
    "Bonjour! Comment puis-je vous aider?",
    "Bonjour! Je suis l'assistant vocal de Harvard. Que puis-je faire pour vous?",
]

THANKS_RESPONSES = [
    "Je vous en prie!",
    "Avec plaisir!",
    "De rien!",
]

GOODBYE_RESPONSES = [
    "Au revoir! Bonne journée!",
    "À bientôt!",
    "Au revoir!",
]

# Initialize settings
settings = Settings()
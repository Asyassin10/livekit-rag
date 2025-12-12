from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Keys
    GROQ_API_KEY: str
    OPENROUTER_API_KEY: str

    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "harvard"

    # Whisper STT
    WHISPER_MODEL: str = "small"
    WHISPER_LANGUAGE: str = "fr"
    WHISPER_COMPUTE_TYPE: str = "int8"

    # Embeddings
    EMBEDDING_MODEL: str = "openai/text-embedding-3-large"

    # LLM
    LLM_MODEL: str = "llama-3.1-8b-instant"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 150

    # Kokoro TTS
    TTS_MODEL_PATH: str = "kokoro-v1.0.onnx"
    TTS_VOICES_PATH: str = "voices-v1.0.bin"
    TTS_VOICE: str = "ff_siwis"
    TTS_SPEED: float = 1.0

    # RAG
    RAG_TOP_K: int = 3
    RAG_SCORE_THRESHOLD: float = 0.7

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


SYSTEM_PROMPT = """Tu es un assistant virtuel de l'Université Harvard. Tu réponds en français de manière concise et professionnelle.

Règles:
- Réponds toujours en français
- Sois bref et direct (2-3 phrases max)
- Utilise les informations du contexte fourni
- Si tu ne sais pas, dis-le simplement
- Ton ton est chaleureux mais professionnel"""
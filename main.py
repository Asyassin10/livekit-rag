"""
Main application: FastAPI + LiveKit Agent for Speech-to-Speech RAG Assistant
"""
import asyncio
import logging
import random
from typing import Optional, Annotated
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from livekit import rtc, api
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import silero

from config import (
    settings,
    GREETING_RESPONSES,
    THANKS_RESPONSES,
    GOODBYE_RESPONSES,
)
from stt import get_stt
from rag import get_rag
from llm import get_llm
from tts import get_tts

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Initialize RAG components globally
rag_instance = None


def get_rag_instance():
    """Get or create RAG instance"""
    global rag_instance
    if rag_instance is None:
        rag_instance = get_rag()
    return rag_instance


class ConversationDetector:
    """Detect greetings, thanks, and goodbye messages"""

    @staticmethod
    def is_greeting(text: str) -> bool:
        """Check if text is a greeting"""
        text_lower = text.lower().strip()
        return any(keyword in text_lower for keyword in settings.GREETING_KEYWORDS)

    @staticmethod
    def is_thanks(text: str) -> bool:
        """Check if text is a thank you message"""
        text_lower = text.lower().strip()
        return any(keyword in text_lower for keyword in settings.THANKS_KEYWORDS)

    @staticmethod
    def is_goodbye(text: str) -> bool:
        """Check if text is a goodbye message"""
        text_lower = text.lower().strip()
        return any(keyword in text_lower for keyword in settings.GOODBYE_KEYWORDS)

    @staticmethod
    def get_response(text: str) -> Optional[str]:
        """Get appropriate response for conversation cues"""
        if ConversationDetector.is_greeting(text):
            return random.choice(GREETING_RESPONSES)
        elif ConversationDetector.is_thanks(text):
            return random.choice(THANKS_RESPONSES)
        elif ConversationDetector.is_goodbye(text):
            return random.choice(GOODBYE_RESPONSES)
        return None


@function_tool
async def search_knowledge_base(
    context: RunContext,
    query: Annotated[str, "The search query to find relevant information"],
) -> str:
    """
    Search the Harvard knowledge base for relevant information.
    Use this tool to answer questions about Harvard University.
    """
    try:
        rag = get_rag_instance()
        
        # Retrieve relevant documents
        documents = await rag.retrieve(query)
        
        # Format context
        result = rag.format_context(documents)
        
        if result:
            logger.info(f"RAG retrieved {len(documents)} documents for query: {query}")
            return result
        else:
            logger.info(f"No relevant documents found for query: {query}")
            return "No relevant information found in the knowledge base."
            
    except Exception as e:
        logger.error(f"Error in RAG search: {e}")
        return f"Error searching knowledge base: {str(e)}"


def prewarm(proc: JobProcess):
    """Prewarm function to load VAD model"""
    proc.userdata["vad"] = silero.VAD.load()
    logger.info("VAD model prewarmed")


async def entrypoint(ctx: JobContext):
    """
    LiveKit agent entrypoint

    Args:
        ctx: Job context from LiveKit
    """
    logger.info("Agent starting")

    # Connect to room
    await ctx.connect()
    logger.info(f"Connected to room: {ctx.room.name}")

    # Wait for participant
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant joined: {participant.identity}")

    # Create the agent with instructions and tools
    agent = Agent(
        instructions="""Tu es l'assistant vocal de Harvard University. Tu parles en français.
        
Ton rôle est d'aider les utilisateurs avec des informations sur Harvard University.
Utilise l'outil search_knowledge_base pour rechercher des informations pertinentes avant de répondre.

Règles importantes:
- Réponds toujours en français
- Sois concis et clair dans tes réponses vocales
- Utilise des phrases courtes adaptées à la conversation orale
- Si tu ne trouves pas l'information, dis-le poliment
- Pour les salutations simples, réponds naturellement sans utiliser l'outil de recherche
""",
        tools=[search_knowledge_base],
    )

    # Create agent session with VAD, STT, LLM, TTS
    # Using plugin strings - adjust these based on your providers
    session = AgentSession(
        vad=ctx.proc.userdata["vad"],
        # Use your preferred STT provider
        stt=settings.STT_PROVIDER if hasattr(settings, 'STT_PROVIDER') else "deepgram/nova-2",
        # Use your preferred LLM provider  
        llm=settings.LLM_PROVIDER if hasattr(settings, 'LLM_PROVIDER') else "openai/gpt-4o-mini",
        # Use your preferred TTS provider
        tts=settings.TTS_PROVIDER if hasattr(settings, 'TTS_PROVIDER') else "cartesia/sonic",
    )

    # Start the session
    await session.start(agent=agent, room=ctx.room)
    logger.info("Agent session started")

    # Send initial greeting
    await session.generate_reply(
        instructions="Salue l'utilisateur et présente-toi comme l'assistant vocal de Harvard. Demande comment tu peux aider."
    )

    logger.info("Agent running")


# FastAPI application
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting application")

    # Initialize RAG instance
    get_rag_instance()

    yield

    logger.info("Shutting down application")


app = FastAPI(
    title="Speech-to-Speech RAG Assistant",
    description="LiveKit-powered voice assistant with RAG capabilities",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware for web client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Token request model
class TokenRequest(BaseModel):
    room_name: str
    participant_name: str


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Speech-to-Speech RAG Assistant",
        "status": "running",
        "version": "1.0.0",
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/webhook")
async def webhook(request: Request):
    """LiveKit webhook endpoint"""
    try:
        body = await request.json()
        logger.info(f"Webhook received: {body}")
        return JSONResponse({"status": "ok"})
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/token")
async def generate_token(request: TokenRequest):
    """Generate LiveKit access token for client"""
    try:
        # Create access token
        token = api.AccessToken(
            api_key=settings.LIVEKIT_API_KEY,
            api_secret=settings.LIVEKIT_API_SECRET,
        )

        # Set identity and grants
        token.with_identity(request.participant_name)
        token.with_name(request.participant_name)
        token.with_grants(
            api.VideoGrants(
                room_join=True,
                room=request.room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        )

        # Generate JWT
        access_token = token.to_jwt()

        logger.info(f"Generated token for {request.participant_name} in room {request.room_name}")

        return {
            "token": access_token,
            "url": settings.LIVEKIT_URL,
            "room": request.room_name,
            "participant": request.participant_name,
        }

    except Exception as e:
        logger.error(f"Token generation error: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )


def main():
    """Main entry point"""
    # Run LiveKit agent
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
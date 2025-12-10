"""
FastAPI Server for Token Generation and API Endpoints
Run this separately from the LiveKit agent (main.py)
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from livekit import api

from config import settings
from rag import get_rag

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


# Token request model
class TokenRequest(BaseModel):
    room_name: str
    participant_name: str


# FastAPI application
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting FastAPI server")

    # Initialize RAG instance
    get_rag_instance()

    yield

    logger.info("Shutting down FastAPI server")


app = FastAPI(
    title="LiveKit RAG - Token Server",
    description="Token generation and API endpoints for LiveKit RAG Assistant",
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


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "LiveKit RAG - Token Server",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "token": "POST /token - Generate LiveKit access token",
            "health": "GET /health - Health check",
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


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


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting server on http://localhost:8000")
    logger.info("API Documentation: http://localhost:8000/docs")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )

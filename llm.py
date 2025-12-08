"""
LLM module for streaming responses using Groq API
"""
import logging
from typing import AsyncGenerator, Optional
from groq import AsyncGroq
from config import settings, SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class LLMStreamer:
    """LLM streamer using Groq API"""

    def __init__(self):
        """Initialize Groq client"""
        logger.info(f"Initializing Groq client with model: {settings.LLM_MODEL}")

        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = settings.LLM_MODEL

        logger.info("Groq client initialized")

    async def stream_response(
        self, user_message: str, context: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream LLM response with optional RAG context

        Args:
            user_message: User's question or message
            context: Retrieved context from RAG (optional)

        Yields:
            Text chunks from the LLM response
        """
        try:
            # Build the user prompt with context if available
            if context:
                user_prompt = f"""Contexte:
{context}

Question: {user_message}"""
            else:
                user_prompt = user_message

            # Create streaming chat completion
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                stream=True,
            )

            # Stream the response
            full_response = ""
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content

            logger.info(f"LLM response: {full_response}")

        except Exception as e:
            logger.error(f"LLM streaming error: {e}")
            yield "Désolé, une erreur s'est produite."

    async def get_response(
        self, user_message: str, context: Optional[str] = None
    ) -> str:
        """
        Get complete LLM response (non-streaming)

        Args:
            user_message: User's question or message
            context: Retrieved context from RAG (optional)

        Returns:
            Complete LLM response
        """
        try:
            # Build the user prompt with context if available
            if context:
                user_prompt = f"""Contexte:
{context}

Question: {user_message}"""
            else:
                user_prompt = user_message

            # Create chat completion
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
            )

            result = response.choices[0].message.content
            logger.info(f"LLM response: {result}")
            return result

        except Exception as e:
            logger.error(f"LLM error: {e}")
            return "Désolé, une erreur s'est produite."


# Global LLM instance
_llm_instance: Optional[LLMStreamer] = None


def get_llm() -> LLMStreamer:
    """Get or create the global LLM instance"""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLMStreamer()
    return _llm_instance

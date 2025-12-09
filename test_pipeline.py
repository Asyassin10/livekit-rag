"""
Test the complete pipeline without LiveKit
Just the core flow: Text → RAG → LLM → TTS
"""
import asyncio
from rag import get_rag
from llm import get_llm
from tts import get_tts


async def test_pipeline():
    """
    Simple pipeline test:
    1. User question (text)
    2. Search Qdrant for relevant docs
    3. Send docs + question to LLM
    4. LLM generates answer
    5. Convert answer to speech
    """
    print("=" * 60)
    print("🧪 Testing RAG Pipeline")
    print("=" * 60)

    # Initialize components
    print("\n📦 Loading models...")
    rag = get_rag()
    llm = get_llm()
    tts = get_tts()
    print("✅ Models loaded\n")

    # Test question
    question = "Quand Harvard a-t-elle été fondée?"
    print(f"❓ Question: {question}\n")

    # Step 1: Search knowledge base
    print("🔍 Step 1: Searching Qdrant for relevant documents...")
    documents = await rag.retrieve(question)
    print(f"   Found {len(documents)} documents:")
    for i, doc in enumerate(documents, 1):
        print(f"   {i}. {doc['text'][:100]}... (score: {doc['score']:.2f})")

    # Step 2: Format context
    print("\n📝 Step 2: Formatting context...")
    context = rag.format_context(documents)
    print(f"   Context length: {len(context)} characters")

    # Step 3: Generate answer with LLM
    print("\n🤖 Step 3: Asking LLM...")
    answer = await llm.get_response(question, context)
    print(f"   Answer: {answer}")

    # Step 4: Convert to speech
    print("\n🔊 Step 4: Converting to speech...")
    audio = tts.synthesize(answer)
    if audio:
        # Save audio
        with open("test_answer.wav", "wb") as f:
            f.write(audio)
        print(f"   ✅ Audio saved to test_answer.wav ({len(audio)} bytes)")
    else:
        print("   ❌ Failed to generate audio")

    print("\n" + "=" * 60)
    print("✅ Pipeline test complete!")
    print("=" * 60)
    print("\n💡 Play the audio: start test_answer.wav")


if __name__ == "__main__":
    asyncio.run(test_pipeline())

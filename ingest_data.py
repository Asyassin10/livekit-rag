import os
import logging
from pathlib import Path
from typing import List, Dict
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataIngestor:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.qdrant_client = QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"))
        self.collection_name = os.getenv("QDRANT_COLLECTION", "harvard")
        self.embedding_model = "text-embedding-3-large"
        self.chunk_size = 1000
        self.chunk_overlap = 200

    def chunk_text(self, text: str, filename: str) -> List[Dict]:
        chunks = []
        words = text.split()

        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = " ".join(chunk_words)

            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "source": filename,
                    "chunk_index": len(chunks)
                }
            })

        return chunks

    def get_embedding(self, text: str) -> List[float]:
        response = self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding

    def create_collection(self, vector_size: int):
        try:
            self.qdrant_client.delete_collection(self.collection_name)
            logger.info(f"Deleted existing collection: {self.collection_name}")
        except Exception:
            pass

        self.qdrant_client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
        )
        logger.info(f"Created collection: {self.collection_name}")

    def ingest_folder(self, folder_path: str):
        folder = Path(folder_path)
        all_chunks = []

        for txt_file in sorted(folder.glob("*.txt")):
            logger.info(f"Reading {txt_file.name}")

            with open(txt_file, "r", encoding="utf-8") as f:
                content = f.read()

            chunks = self.chunk_text(content, txt_file.name)
            all_chunks.extend(chunks)
            logger.info(f"Created {len(chunks)} chunks from {txt_file.name}")

        logger.info(f"Total chunks: {len(all_chunks)}")

        sample_embedding = self.get_embedding(all_chunks[0]["text"])
        self.create_collection(len(sample_embedding))

        points = []
        for idx, chunk in enumerate(all_chunks):
            logger.info(f"Processing chunk {idx + 1}/{len(all_chunks)}")

            embedding = self.get_embedding(chunk["text"])

            point = PointStruct(
                id=idx,
                vector=embedding,
                payload={
                    "text": chunk["text"],
                    "metadata": chunk["metadata"]
                }
            )
            points.append(point)

            if len(points) >= 100:
                self.qdrant_client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                logger.info(f"Uploaded batch of {len(points)} points")
                points = []

        if points:
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.info(f"Uploaded final batch of {len(points)} points")

        logger.info(f"Ingestion complete! Total vectors: {len(all_chunks)}")


if __name__ == "__main__":
    ingestor = DataIngestor()
    ingestor.ingest_folder("harvard")

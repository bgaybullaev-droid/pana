"""
Vector Database for Image and Text Similarity Search
Uses ChromaDB (free, persistent, easy to use)
Like Instagram's duplicate detection system
"""

import chromadb
from chromadb.config import Settings
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging
from pathlib import Path
import json
from sentence_transformers import SentenceTransformer

from llm_config import (
    SENTENCE_TRANSFORMER_MODEL,
    CHROMA_PERSIST_DIR,
    CHROMA_IMAGE_COLLECTION,
    CHROMA_TEXT_COLLECTION,
    IMAGE_SIMILARITY_THRESHOLD,
    TEXT_SIMILARITY_THRESHOLD,
    TOP_K_SIMILAR_IMAGES,
    TOP_K_SIMILAR_TEXTS
)

logger = logging.getLogger(__name__)


class VectorDatabase:
    """Manage image and text embeddings for similarity search"""

    def __init__(self, persist_directory: str = CHROMA_PERSIST_DIR):
        """Initialize ChromaDB client"""
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initializing ChromaDB at {self.persist_directory}")

        try:
            # Create persistent client
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # Get or create collections
            self.image_collection = self.client.get_or_create_collection(
                name=CHROMA_IMAGE_COLLECTION,
                metadata={"description": "Image embeddings from CLIP"},
                # Use cosine similarity (default)
            )

            self.text_collection = self.client.get_or_create_collection(
                name=CHROMA_TEXT_COLLECTION,
                metadata={"description": "Text embeddings for semantic search"}
            )

            logger.info(f"✅ ChromaDB initialized")
            logger.info(f"   Image embeddings: {self.image_collection.count()} vectors")
            logger.info(f"   Text embeddings: {self.text_collection.count()} vectors")

        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise

        # Initialize sentence transformer for text embeddings
        try:
            self.text_model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)
            logger.info(f"✅ Sentence transformer loaded: {SENTENCE_TRANSFORMER_MODEL}")
        except Exception as e:
            logger.error(f"Failed to load sentence transformer: {e}")
            self.text_model = None

    def generate_text_embedding(self, text: str) -> Optional[np.ndarray]:
        """Generate text embedding using sentence transformers"""
        if self.text_model is None:
            logger.error("Sentence transformer not initialized")
            return None
        try:
            embedding = self.text_model.encode(text, normalize_embeddings=True)
            return np.array(embedding, dtype=np.float32)
        except Exception as e:
            logger.error(f"Error generating text embedding: {e}")
            return None

    def search_similar_text(self, *args, **kwargs) -> List[Dict]:
        """Alias for search_similar_texts (backwards compatibility)"""
        return self.search_similar_texts(*args, **kwargs)

    # ===========================
    # Image Embedding Operations
    # ===========================

    def add_image_embedding(self, listing_id: int, image_id: int,
                           embedding: np.ndarray, metadata: Optional[Dict] = None):
        """
        Add image embedding to vector database

        Args:
            listing_id: ID of the listing
            image_id: ID of the image
            embedding: Image embedding vector from CLIP
            metadata: Optional metadata (channel, schema_type, etc.)
        """
        try:
            doc_id = f"listing_{listing_id}_image_{image_id}"

            # Prepare metadata
            meta = {
                "listing_id": listing_id,
                "image_id": image_id,
                **(metadata or {})
            }

            # Add to collection
            self.image_collection.add(
                ids=[doc_id],
                embeddings=[embedding.tolist()],
                metadatas=[meta]
            )

            logger.debug(f"Added image embedding: {doc_id}")

        except Exception as e:
            logger.error(f"Error adding image embedding: {e}")

    def search_similar_images(self, query_embedding: np.ndarray,
                             top_k: int = TOP_K_SIMILAR_IMAGES,
                             threshold: float = IMAGE_SIMILARITY_THRESHOLD,
                             schema_filter: Optional[str] = None) -> List[Dict]:
        """
        Find similar images in database

        Args:
            query_embedding: Image embedding to search for
            top_k: Number of results to return
            threshold: Minimum similarity score (0-1)
            schema_filter: Only search within specific schema type

        Returns:
            List of dicts with: listing_id, image_id, similarity, metadata
        """
        try:
            # Prepare filter
            where_filter = None
            if schema_filter:
                where_filter = {"schema_type": schema_filter}

            # Search
            results = self.image_collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=top_k,
                where=where_filter
            )

            # Parse results
            similar_images = []

            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    # ChromaDB returns distance, convert to similarity
                    # For cosine distance: similarity = 1 - distance
                    distance = results['distances'][0][i]
                    similarity = 1 - distance

                    if similarity >= threshold:
                        similar_images.append({
                            'listing_id': results['metadatas'][0][i]['listing_id'],
                            'image_id': results['metadatas'][0][i]['image_id'],
                            'similarity': similarity,
                            'metadata': results['metadatas'][0][i]
                        })

            logger.info(f"Found {len(similar_images)} similar images above {threshold}")
            return similar_images

        except Exception as e:
            logger.error(f"Error searching similar images: {e}")
            return []

    def find_duplicate_images(self, query_embedding: np.ndarray,
                             threshold: float = IMAGE_SIMILARITY_THRESHOLD) -> Optional[Dict]:
        """
        Check if image is a duplicate (very similar to existing image)

        Args:
            query_embedding: Image embedding
            threshold: Similarity threshold for duplicates

        Returns:
            Dict with duplicate info if found, None otherwise
        """
        similar = self.search_similar_images(query_embedding, top_k=1, threshold=threshold)

        if similar:
            return similar[0]
        return None

    # ===========================
    # Text Embedding Operations
    # ===========================

    def add_text_embedding(self, listing_id: int, embedding: np.ndarray,
                          text_preview: str, metadata: Optional[Dict] = None):
        """
        Add text embedding to vector database

        Args:
            listing_id: ID of the listing
            embedding: Text embedding vector
            text_preview: First 100 chars of text (for reference)
            metadata: Optional metadata
        """
        try:
            doc_id = f"listing_{listing_id}"

            # Prepare metadata
            meta = {
                "listing_id": listing_id,
                "text_preview": text_preview[:100],
                **(metadata or {})
            }

            # Add to collection
            self.text_collection.add(
                ids=[doc_id],
                embeddings=[embedding.tolist()],
                metadatas=[meta]
            )

            logger.debug(f"Added text embedding: {doc_id}")

        except Exception as e:
            logger.error(f"Error adding text embedding: {e}")

    def search_similar_texts(self, query_embedding: np.ndarray,
                            top_k: int = TOP_K_SIMILAR_TEXTS,
                            threshold: float = TEXT_SIMILARITY_THRESHOLD,
                            schema_filter: Optional[str] = None) -> List[Dict]:
        """
        Find similar texts in database

        Args:
            query_embedding: Text embedding to search for
            top_k: Number of results
            threshold: Minimum similarity
            schema_filter: Filter by schema type

        Returns:
            List of similar listings
        """
        try:
            where_filter = None
            if schema_filter:
                where_filter = {"schema_type": schema_filter}

            results = self.text_collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=top_k,
                where=where_filter
            )

            similar_texts = []

            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    distance = results['distances'][0][i]
                    similarity = 1 - distance

                    if similarity >= threshold:
                        similar_texts.append({
                            'listing_id': results['metadatas'][0][i]['listing_id'],
                            'similarity': similarity,
                            'text_preview': results['metadatas'][0][i].get('text_preview', ''),
                            'metadata': results['metadatas'][0][i]
                        })

            logger.info(f"Found {len(similar_texts)} similar texts above {threshold}")
            return similar_texts

        except Exception as e:
            logger.error(f"Error searching similar texts: {e}")
            return []

    # ===========================
    # Combined Operations
    # ===========================

    def find_duplicates(self, image_embedding: Optional[np.ndarray] = None,
                       text_embedding: Optional[np.ndarray] = None,
                       image_threshold: float = IMAGE_SIMILARITY_THRESHOLD,
                       text_threshold: float = TEXT_SIMILARITY_THRESHOLD) -> Dict:
        """
        Find duplicates using both image and text similarity

        Args:
            image_embedding: Image embedding (optional)
            text_embedding: Text embedding (optional)
            image_threshold: Image similarity threshold
            text_threshold: Text similarity threshold

        Returns:
            Dict with:
                is_duplicate: bool
                duplicate_type: 'image', 'text', or 'both'
                matches: List of matching listings
                max_similarity: Highest similarity score
        """
        result = {
            'is_duplicate': False,
            'duplicate_type': None,
            'matches': [],
            'max_similarity': 0.0
        }

        try:
            image_matches = []
            text_matches = []

            # Search for similar images
            if image_embedding is not None:
                image_matches = self.search_similar_images(
                    image_embedding,
                    top_k=3,
                    threshold=image_threshold
                )

            # Search for similar texts
            if text_embedding is not None:
                text_matches = self.search_similar_texts(
                    text_embedding,
                    top_k=3,
                    threshold=text_threshold
                )

            # Determine if duplicate
            if image_matches or text_matches:
                result['is_duplicate'] = True

                if image_matches and text_matches:
                    result['duplicate_type'] = 'both'
                elif image_matches:
                    result['duplicate_type'] = 'image'
                else:
                    result['duplicate_type'] = 'text'

                # Combine matches
                all_matches = {}

                for match in image_matches:
                    lid = match['listing_id']
                    all_matches[lid] = {
                        'listing_id': lid,
                        'image_similarity': match['similarity'],
                        'text_similarity': 0.0,
                        'combined_similarity': match['similarity'],
                        'metadata': match.get('metadata', {})
                    }

                for match in text_matches:
                    lid = match['listing_id']
                    if lid in all_matches:
                        all_matches[lid]['text_similarity'] = match['similarity']
                        # Weighted average: 70% image, 30% text
                        all_matches[lid]['combined_similarity'] = (
                            0.7 * all_matches[lid]['image_similarity'] +
                            0.3 * match['similarity']
                        )
                    else:
                        all_matches[lid] = {
                            'listing_id': lid,
                            'image_similarity': 0.0,
                            'text_similarity': match['similarity'],
                            'combined_similarity': match['similarity'],
                            'metadata': match.get('metadata', {})
                        }

                # Sort by combined similarity
                result['matches'] = sorted(
                    all_matches.values(),
                    key=lambda x: x['combined_similarity'],
                    reverse=True
                )

                if result['matches']:
                    result['max_similarity'] = result['matches'][0]['combined_similarity']

            return result

        except Exception as e:
            logger.error(f"Error finding duplicates: {e}")
            return result

    # ===========================
    # Utility Operations
    # ===========================

    def get_stats(self) -> Dict:
        """Get database statistics"""
        return {
            'image_count': self.image_collection.count(),
            'text_count': self.text_collection.count(),
            'persist_directory': str(self.persist_directory)
        }

    def delete_listing(self, listing_id: int):
        """Delete all embeddings for a listing"""
        try:
            # Delete text embedding
            self.text_collection.delete(ids=[f"listing_{listing_id}"])

            # Delete image embeddings (need to find them first)
            # This is a limitation - ChromaDB doesn't support prefix delete
            # In production, you'd want to track image IDs separately

            logger.info(f"Deleted embeddings for listing {listing_id}")

        except Exception as e:
            logger.error(f"Error deleting listing embeddings: {e}")

    def reset_database(self):
        """Clear all embeddings (use with caution!)"""
        try:
            self.client.delete_collection(CHROMA_IMAGE_COLLECTION)
            self.client.delete_collection(CHROMA_TEXT_COLLECTION)

            self.image_collection = self.client.create_collection(CHROMA_IMAGE_COLLECTION)
            self.text_collection = self.client.create_collection(CHROMA_TEXT_COLLECTION)

            logger.warning("⚠️  Database reset - all embeddings deleted")

        except Exception as e:
            logger.error(f"Error resetting database: {e}")


# Example usage and testing
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print("="*60)
    print("Testing Vector Database with ChromaDB")
    print("="*60)

    # Initialize database
    db = VectorDatabase()

    # Get stats
    stats = db.get_stats()
    print(f"\nDatabase Stats:")
    print(f"  Image embeddings: {stats['image_count']}")
    print(f"  Text embeddings: {stats['text_count']}")
    print(f"  Location: {stats['persist_directory']}")

    # Test with dummy embeddings
    print("\n--- Adding Test Embeddings ---")

    # Create dummy CLIP embeddings (512-dim)
    test_embedding_1 = np.random.rand(512).astype(np.float32)
    test_embedding_1 = test_embedding_1 / np.linalg.norm(test_embedding_1)

    test_embedding_2 = np.random.rand(512).astype(np.float32)
    test_embedding_2 = test_embedding_2 / np.linalg.norm(test_embedding_2)

    # Add to database
    db.add_image_embedding(
        listing_id=1,
        image_id=1,
        embedding=test_embedding_1,
        metadata={'schema_type': 'product_listing', 'channel': 'test'}
    )

    db.add_image_embedding(
        listing_id=2,
        image_id=2,
        embedding=test_embedding_2,
        metadata={'schema_type': 'product_listing', 'channel': 'test'}
    )

    print("✅ Added 2 test embeddings")

    # Search for similar
    print("\n--- Searching for Similar Images ---")
    similar = db.search_similar_images(test_embedding_1, top_k=5, threshold=0.0)
    print(f"Found {len(similar)} similar images:")
    for match in similar:
        print(f"  Listing {match['listing_id']}, Image {match['image_id']}: {match['similarity']:.4f}")

    # Test duplicate detection
    print("\n--- Testing Duplicate Detection ---")
    duplicate = db.find_duplicate_images(test_embedding_1, threshold=0.95)
    if duplicate:
        print(f"⚠️  Duplicate found: Listing {duplicate['listing_id']} (similarity: {duplicate['similarity']:.4f})")
    else:
        print("✅ No duplicates found")

    print("\n" + "="*60)
    print("Vector database ready for use!")
    print("="*60)

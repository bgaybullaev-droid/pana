"""
Image Embedding Generation using CLIP
Converts images to vectors for similarity search (like Instagram)
100% FREE - runs locally, no API costs
"""

import torch
import clip
from PIL import Image
import numpy as np
from typing import List, Tuple, Optional
import io
from pathlib import Path
import logging

from llm_config import (
    CLIP_MODEL_NAME,
    CLIP_DEVICE,
    RESIZE_IMAGES,
    MAX_IMAGE_SIZE,
    MIN_IMAGE_SIZE,
    IMAGE_BATCH_SIZE
)

logger = logging.getLogger(__name__)


class ImageEmbedder:
    """Generate image embeddings using CLIP"""

    def __init__(self):
        """Initialize CLIP model"""
        self.device = CLIP_DEVICE if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading CLIP model {CLIP_MODEL_NAME} on {self.device}...")

        try:
            self.model, self.preprocess = clip.load(CLIP_MODEL_NAME, device=self.device)
            self.model.eval()  # Set to evaluation mode
            logger.info(f"✅ CLIP model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load CLIP model: {e}")
            raise

    def embed_image(self, image_path: str) -> Optional[np.ndarray]:
        """
        Convert single image to embedding vector

        Args:
            image_path: Path to image file

        Returns:
            numpy array of shape (512,) or (768,) depending on model
            Returns None if image processing fails
        """
        try:
            # Load and preprocess image
            image = Image.open(image_path).convert('RGB')

            # Check minimum size
            if image.size[0] < MIN_IMAGE_SIZE[0] or image.size[1] < MIN_IMAGE_SIZE[1]:
                logger.warning(f"Image too small: {image.size}, skipping")
                return None

            # Resize if needed
            if RESIZE_IMAGES and (image.size[0] > MAX_IMAGE_SIZE[0] or image.size[1] > MAX_IMAGE_SIZE[1]):
                image.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)

            # Preprocess for CLIP
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)

            # Generate embedding
            with torch.no_grad():
                embedding = self.model.encode_image(image_input)

            # Normalize embedding (important for cosine similarity)
            embedding = embedding / embedding.norm(dim=-1, keepdim=True)

            # Convert to numpy
            embedding_np = embedding.cpu().numpy().flatten()

            logger.debug(f"Generated embedding for {image_path}: shape={embedding_np.shape}")
            return embedding_np

        except Exception as e:
            logger.error(f"Error embedding image {image_path}: {e}")
            return None

    def embed_images_batch(self, image_paths: List[str]) -> List[Optional[np.ndarray]]:
        """
        Convert multiple images to embeddings in batch (faster)

        Args:
            image_paths: List of image file paths

        Returns:
            List of numpy arrays (one per image)
        """
        embeddings = []

        try:
            # Process in batches
            for i in range(0, len(image_paths), IMAGE_BATCH_SIZE):
                batch_paths = image_paths[i:i + IMAGE_BATCH_SIZE]
                batch_images = []
                valid_indices = []

                # Load and preprocess batch
                for idx, path in enumerate(batch_paths):
                    try:
                        image = Image.open(path).convert('RGB')

                        # Check size
                        if image.size[0] < MIN_IMAGE_SIZE[0] or image.size[1] < MIN_IMAGE_SIZE[1]:
                            embeddings.append(None)
                            continue

                        # Resize
                        if RESIZE_IMAGES and (image.size[0] > MAX_IMAGE_SIZE[0] or image.size[1] > MAX_IMAGE_SIZE[1]):
                            image.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)

                        batch_images.append(self.preprocess(image))
                        valid_indices.append(i + idx)

                    except Exception as e:
                        logger.error(f"Error loading {path}: {e}")
                        embeddings.append(None)

                # Process valid images
                if batch_images:
                    batch_tensor = torch.stack(batch_images).to(self.device)

                    with torch.no_grad():
                        batch_embeddings = self.model.encode_image(batch_tensor)

                    # Normalize
                    batch_embeddings = batch_embeddings / batch_embeddings.norm(dim=-1, keepdim=True)

                    # Convert to numpy and add to results
                    batch_np = batch_embeddings.cpu().numpy()

                    for emb in batch_np:
                        embeddings.append(emb)

            logger.info(f"Generated {len([e for e in embeddings if e is not None])}/{len(image_paths)} embeddings")
            return embeddings

        except Exception as e:
            logger.error(f"Error in batch embedding: {e}")
            return [None] * len(image_paths)

    def embed_from_bytes(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """
        Convert image bytes to embedding (useful for downloaded images)

        Args:
            image_bytes: Image data as bytes

        Returns:
            numpy array embedding
        """
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')

            if RESIZE_IMAGES and (image.size[0] > MAX_IMAGE_SIZE[0] or image.size[1] > MAX_IMAGE_SIZE[1]):
                image.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)

            image_input = self.preprocess(image).unsqueeze(0).to(self.device)

            with torch.no_grad():
                embedding = self.model.encode_image(image_input)

            embedding = embedding / embedding.norm(dim=-1, keepdim=True)
            return embedding.cpu().numpy().flatten()

        except Exception as e:
            logger.error(f"Error embedding image from bytes: {e}")
            return None

    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score between 0 and 1 (1 = identical)
        """
        try:
            # Cosine similarity (already normalized, so just dot product)
            similarity = np.dot(embedding1, embedding2)
            return float(similarity)

        except Exception as e:
            logger.error(f"Error computing similarity: {e}")
            return 0.0

    def find_similar_embeddings(self, query_embedding: np.ndarray,
                                database_embeddings: List[np.ndarray],
                                top_k: int = 5) -> List[Tuple[int, float]]:
        """
        Find top-k most similar embeddings from database

        Args:
            query_embedding: Embedding to search for
            database_embeddings: List of embeddings to search in
            top_k: Number of results to return

        Returns:
            List of (index, similarity_score) tuples, sorted by similarity
        """
        try:
            similarities = []

            for idx, db_embedding in enumerate(database_embeddings):
                if db_embedding is not None:
                    sim = self.compute_similarity(query_embedding, db_embedding)
                    similarities.append((idx, sim))

            # Sort by similarity (descending)
            similarities.sort(key=lambda x: x[1], reverse=True)

            return similarities[:top_k]

        except Exception as e:
            logger.error(f"Error finding similar embeddings: {e}")
            return []

    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model"""
        if 'ViT-L' in CLIP_MODEL_NAME:
            return 768
        else:
            return 512


# Example usage and testing
if __name__ == '__main__':
    import sys

    logging.basicConfig(level=logging.INFO)

    print("="*60)
    print("Testing Image Embedder with CLIP")
    print("="*60)

    # Initialize embedder
    embedder = ImageEmbedder()
    print(f"\n✅ CLIP loaded successfully")
    print(f"Device: {embedder.device}")
    print(f"Embedding dimension: {embedder.get_embedding_dimension()}")

    # Test with images if provided
    if len(sys.argv) > 1:
        test_images = sys.argv[1:]
        print(f"\nProcessing {len(test_images)} images...")

        # Single image test
        print("\n--- Single Image Test ---")
        emb1 = embedder.embed_image(test_images[0])
        if emb1 is not None:
            print(f"✅ Image 1: {test_images[0]}")
            print(f"   Embedding shape: {emb1.shape}")
            print(f"   Embedding norm: {np.linalg.norm(emb1):.4f}")

        if len(test_images) > 1:
            # Batch test
            print("\n--- Batch Test ---")
            embeddings = embedder.embed_images_batch(test_images)
            print(f"Generated {len([e for e in embeddings if e is not None])} embeddings")

            # Similarity test
            if len(embeddings) >= 2 and embeddings[0] is not None and embeddings[1] is not None:
                print("\n--- Similarity Test ---")
                sim = embedder.compute_similarity(embeddings[0], embeddings[1])
                print(f"Similarity between image 1 and 2: {sim:.4f}")

                if sim > 0.9:
                    print("  ⚠️  Very similar (likely duplicates)")
                elif sim > 0.75:
                    print("  📸 Same object, different angle")
                else:
                    print("  ✅ Different images")
    else:
        print("\n💡 Usage: python image_embeddings.py <image1.jpg> <image2.jpg> ...")
        print("   Provide image paths to test embedding generation")

    print("\n" + "="*60)
    print("Image embedder ready for use!")
    print("="*60)

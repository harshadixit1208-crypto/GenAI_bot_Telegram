# app/vision/blip_service.py
"""
BLIP-2 image captioning service.
Generates captions and tags for images using Hugging Face transformers.
"""
from typing import Dict, List, Optional
import logging
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)


class BLIPCaptioningService:
    """Image captioning service using BLIP-2 model."""

    def __init__(self, model_name: str = "Salesforce/blip-image-captioning-base"):
        """Initialize BLIP captioning service.

        Args:
            model_name: HuggingFace model name for BLIP.
        """
        self.model_name = model_name
        self.device = "cuda" if self._has_cuda() else "cpu"
        self.processor = None
        self.model = None
        self._initialize_model()

    def _has_cuda(self) -> bool:
        """Check if CUDA is available."""
        try:
            import torch

            return torch.cuda.is_available()
        except ImportError:
            return False

    def _initialize_model(self) -> None:
        """Initialize BLIP model and processor."""
        try:
            from transformers import BlipProcessor, BlipForConditionalGeneration

            logger.info(f"Loading BLIP model: {self.model_name} on {self.device}")
            self.processor = BlipProcessor.from_pretrained(self.model_name)
            self.model = BlipForConditionalGeneration.from_pretrained(
                self.model_name, torch_dtype="auto"
            ).to(self.device)
            logger.info("BLIP model loaded successfully")
        except ImportError as e:
            logger.error(f"transformers library not installed: {e}")
        except Exception as e:
            logger.error(f"Error loading BLIP model: {e}")

    def _extract_keywords(self, caption: str) -> List[str]:
        """Extract keywords from caption.

        Simple heuristic: extract noun phrases (words > 3 chars, excluding common words).

        Args:
            caption: Generated caption text.

        Returns:
            List of keyword tags (max 3).
        """
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "is",
            "are",
            "was",
            "were",
        }

        words = caption.lower().split()
        keywords = [w.strip(".,!?;:") for w in words if len(w) > 3 and w.lower() not in stop_words]

        # Return top 3 unique keywords
        return list(set(keywords))[:3]

    def caption_image(self, image_path: str) -> Dict[str, any]:
        """Generate caption and tags for an image.

        Args:
            image_path: Path to image file.

        Returns:
            Dict with keys:
                - caption: Short caption (<= 20 words)
                - tags: List of 3 tags
                - description: Optional detailed description
                - success: Boolean indicating if captioning succeeded
        """
        if not self.model or not self.processor:
            logger.error("BLIP model not initialized")
            return {
                "caption": "Error: BLIP model not initialized",
                "tags": [],
                "description": "",
                "success": False,
            }

        try:
            from PIL import Image

            # Load image
            image = Image.open(image_path).convert("RGB")

            # Process and generate caption
            inputs = self.processor(image, return_tensors="pt").to(self.device)

            # Generate caption (max 30 tokens to keep it short)
            caption_ids = self.model.generate(**inputs, max_new_tokens=30, min_length=5)
            caption = self.processor.decode(caption_ids[0], skip_special_tokens=True)

            # Truncate to ~20 words
            caption_words = caption.split()[:20]
            caption_short = " ".join(caption_words)

            # Extract tags
            tags = self._extract_keywords(caption)

            # If we need exactly 3 tags, add generic ones
            while len(tags) < 3:
                tags.append("image")

            return {
                "caption": caption_short,
                "tags": tags[:3],
                "description": caption,
                "success": True,
            }

        except Exception as e:
            logger.error(f"Error captioning image {image_path}: {e}")
            return {
                "caption": f"Error: {str(e)[:50]}",
                "tags": [],
                "description": "",
                "success": False,
            }

    async def caption_image_async(self, image_path: str) -> Dict[str, any]:
        """Asynchronous version of caption_image.

        Args:
            image_path: Path to image file.

        Returns:
            Caption result dict.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.caption_image(image_path))

    def get_stats(self) -> Dict:
        """Get service statistics.

        Returns:
            Stats dict.
        """
        return {
            "model_name": self.model_name,
            "device": self.device,
            "initialized": self.model is not None,
        }

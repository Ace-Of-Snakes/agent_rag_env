"""
Vision LLM service for image analysis.
"""

import base64
from pathlib import Path
from typing import Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.llm.client import ollama_client

logger = get_logger(__name__)

# Vision prompts
VISION_SYSTEM_PROMPT = """You are an expert at analyzing images and documents. 
Your task is to describe the visual content in detail, including:
- Any text visible in the image
- Diagrams, charts, or figures with their meaning
- Tables with their structure and data
- Any other relevant visual elements

Be thorough but concise. Focus on information that would be useful for understanding the document."""

FIGURE_DESCRIPTION_PROMPT = """Analyze this image from a document page. Describe:
1. What type of visual element this is (chart, diagram, photo, table, etc.)
2. The key information it conveys
3. Any text or labels present
4. How it relates to document content

Provide a clear, searchable description."""


class VisionService:
    """Service for vision model operations."""
    
    def __init__(self):
        self._settings = get_settings()
    
    @property
    def model(self) -> str:
        """Get the vision model name."""
        return self._settings.ollama.vision_model
    
    async def describe_image(
        self,
        image_data: bytes | str,
        prompt: Optional[str] = None,
        context: Optional[str] = None
    ) -> str:
        """
        Describe an image using the vision model.
        
        Args:
            image_data: Image bytes or base64 string
            prompt: Custom prompt (defaults to figure description)
            context: Additional context about the image
            
        Returns:
            Description of the image
        """
        # Convert to base64 if bytes
        if isinstance(image_data, bytes):
            image_b64 = base64.b64encode(image_data).decode("utf-8")
        else:
            image_b64 = image_data
        
        # Build prompt
        user_prompt = prompt or FIGURE_DESCRIPTION_PROMPT
        if context:
            user_prompt = f"Context: {context}\n\n{user_prompt}"
        
        # Call vision model with image
        # Ollama expects images in the format for multimodal models
        messages = [
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": user_prompt,
                "images": [image_b64]
            }
        ]
        
        response = await ollama_client.chat(
            model=self.model,
            messages=messages,
            temperature=0.3,  # Lower temperature for more factual descriptions
        )
        
        logger.debug("Image described", response_length=len(response))
        return response
    
    async def describe_image_file(
        self,
        image_path: Path | str,
        prompt: Optional[str] = None,
        context: Optional[str] = None
    ) -> str:
        """
        Describe an image from a file path.
        
        Args:
            image_path: Path to image file
            prompt: Custom prompt
            context: Additional context
            
        Returns:
            Description of the image
        """
        path = Path(image_path)
        with open(path, "rb") as f:
            image_data = f.read()
        
        return await self.describe_image(image_data, prompt, context)
    
    async def analyze_page(
        self,
        page_image: bytes,
        page_number: int,
        extracted_text: str
    ) -> str:
        """
        Analyze a document page image with context from extracted text.
        
        Args:
            page_image: Page rendered as image bytes
            page_number: Page number for context
            extracted_text: Text already extracted from the page
            
        Returns:
            Enhanced description including visual elements
        """
        prompt = f"""This is page {page_number} of a document.

The following text was extracted from this page:
---
{extracted_text[:500]}...
---

Please analyze any visual elements (figures, charts, tables, diagrams) that appear on this page.
For each visual element, provide:
1. Type of element
2. Key information it conveys
3. Any data or labels shown

If there are no significant visual elements, respond with "No significant visual elements on this page."
"""
        
        return await self.describe_image(page_image, prompt)
    
    def should_analyze_page(
        self,
        page_image_bytes: bytes,
        page_area: float,
        image_areas: list[float]
    ) -> bool:
        """
        Determine if a page should be analyzed with vision model.
        
        Uses vision gating to skip pages with minimal visual content.
        
        Args:
            page_image_bytes: Page image bytes
            page_area: Total page area
            image_areas: List of image areas on the page
            
        Returns:
            True if page should be analyzed
        """
        settings = self._settings.performance
        
        if not settings.vision_gating_enabled:
            return True
        
        if not image_areas:
            return False
        
        total_image_area = sum(image_areas)
        ratio = total_image_area / page_area if page_area > 0 else 0
        
        should_analyze = ratio >= settings.vision_gating_min_image_ratio
        
        logger.debug(
            "Vision gating decision",
            ratio=ratio,
            threshold=settings.vision_gating_min_image_ratio,
            should_analyze=should_analyze
        )
        
        return should_analyze


# Singleton instance
vision_service = VisionService()
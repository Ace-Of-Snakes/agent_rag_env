"""
Vision LLM service for image analysis.

UPDATED: 
- Added describe_document_image method for processing PDF images.
- Added image preprocessing to handle small images (padding to minimum size)
"""

import base64
import io
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.llm.client import ollama_client

logger = get_logger(__name__)

# Minimum image dimensions required by Qwen3 VL model
MIN_IMAGE_SIZE = 32


def preprocess_image_for_vision(image_data: bytes) -> bytes:
    """
    Preprocess an image to ensure it meets the vision model's requirements.
    
    The Qwen3 VL model requires images to be at least 32x32 pixels.
    This function pads small images to meet the minimum size requirement.
    
    Args:
        image_data: Raw image bytes
        
    Returns:
        Processed image bytes (PNG format)
    """
    try:
        # Load image
        img = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if necessary (handles RGBA, P mode, etc.)
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        
        width, height = img.size
        
        # Check if padding is needed
        needs_padding = width < MIN_IMAGE_SIZE or height < MIN_IMAGE_SIZE
        
        if needs_padding:
            # Calculate new dimensions (at least MIN_IMAGE_SIZE)
            new_width = max(width, MIN_IMAGE_SIZE)
            new_height = max(height, MIN_IMAGE_SIZE)
            
            # Create a new image with padding (white background)
            padded_img = Image.new('RGB', (new_width, new_height), (255, 255, 255))
            
            # Center the original image on the padded canvas
            paste_x = (new_width - width) // 2
            paste_y = (new_height - height) // 2
            
            # Handle images with alpha channel
            if img.mode == 'RGBA':
                padded_img.paste(img, (paste_x, paste_y), img)
            else:
                padded_img.paste(img, (paste_x, paste_y))
            
            img = padded_img
            
            logger.debug(
                "Padded small image",
                original_size=(width, height),
                new_size=(new_width, new_height)
            )
        
        # Convert back to bytes
        output = io.BytesIO()
        img.save(output, format='PNG')
        return output.getvalue()
        
    except Exception as e:
        logger.warning(f"Image preprocessing failed: {e}, using original image")
        return image_data


def get_image_dimensions(image_data: bytes) -> Tuple[int, int]:
    """Get the dimensions of an image."""
    try:
        img = Image.open(io.BytesIO(image_data))
        return img.size
    except Exception:
        return (0, 0)


def is_meaningful_image(image_data: bytes, min_pixels: int = 1000) -> bool:
    """
    Check if an image is likely to contain meaningful content.
    
    Filters out tiny images that are probably icons, bullets, or decorations.
    
    Args:
        image_data: Raw image bytes
        min_pixels: Minimum total pixels (width * height) to be considered meaningful
        
    Returns:
        True if image appears to be meaningful content
    """
    try:
        width, height = get_image_dimensions(image_data)
        total_pixels = width * height
        
        # Skip very small images (likely icons, bullets, etc.)
        if total_pixels < min_pixels:
            return False
        
        # Skip extremely narrow images (likely lines/separators)
        if width < 20 or height < 20:
            return False
            
        return True
    except Exception:
        return True  # Process if we can't determine size


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

DOCUMENT_IMAGE_PROMPT = """You are analyzing an image extracted from a PDF document.

Page: {page_number}
Image: {image_index} of {total_images} on this page
{context_section}

Please provide a detailed description of this image that captures:

1. **Type**: What kind of visual element is this? (chart, graph, diagram, photo, screenshot, table, logo, illustration, etc.)

2. **Content**: What does the image show? Be specific about:
   - Any text, labels, or captions visible in the image
   - Data values, numbers, or measurements shown
   - Names, titles, or identifiers
   - Colors, patterns, or visual distinctions that carry meaning

3. **Information**: What information or message does this image convey?
   - Key takeaways or insights
   - Relationships or comparisons shown
   - Trends or patterns (for charts/graphs)

4. **Structure** (if applicable):
   - For tables: describe rows, columns, and notable data
   - For diagrams: describe components and their connections
   - For charts: describe axes, legends, and data series

Provide a clear, detailed description that would allow someone to understand this image without seeing it. 
Focus on factual content rather than aesthetic qualities."""


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
        # Handle base64 string input
        if isinstance(image_data, str):
            image_bytes = base64.b64decode(image_data)
        else:
            image_bytes = image_data
        
        # Preprocess image to handle small images
        processed_image = preprocess_image_for_vision(image_bytes)
        
        # Convert to base64
        image_b64 = base64.b64encode(processed_image).decode("utf-8")
        
        # Build prompt
        user_prompt = prompt or FIGURE_DESCRIPTION_PROMPT
        if context:
            user_prompt = f"Context: {context}\n\n{user_prompt}"
        
        # Call vision model with image
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
    
    async def describe_document_image(
        self,
        image_data: bytes | str,
        page_number: int,
        image_index: int = 1,
        total_images_on_page: int = 1,
        text_context: Optional[str] = None
    ) -> str:
        """
        Describe an image extracted from a PDF document.
        
        This method is optimized for document images like charts, diagrams,
        tables, and figures that need detailed, searchable descriptions.
        
        Args:
            image_data: Image bytes or base64 string
            page_number: The page number this image is from
            image_index: Which image on the page (1-indexed)
            total_images_on_page: Total number of images on this page
            text_context: Surrounding text from the page for context
            
        Returns:
            Detailed description of the image content
        """
        # Handle base64 string input
        if isinstance(image_data, str):
            image_bytes = base64.b64decode(image_data)
        else:
            image_bytes = image_data
        
        # Get original dimensions for logging
        orig_width, orig_height = get_image_dimensions(image_bytes)
        
        # Preprocess image to handle small images
        processed_image = preprocess_image_for_vision(image_bytes)
        
        # Convert to base64
        image_b64 = base64.b64encode(processed_image).decode("utf-8")
        
        # Build context section
        context_section = ""
        if text_context and text_context.strip():
            # Truncate context if too long
            truncated_context = text_context[:500]
            if len(text_context) > 500:
                truncated_context += "..."
            context_section = f"\nSurrounding text context:\n\"\"\"\n{truncated_context}\n\"\"\"\n"
        
        # Build the prompt
        prompt = DOCUMENT_IMAGE_PROMPT.format(
            page_number=page_number,
            image_index=image_index,
            total_images=total_images_on_page,
            context_section=context_section
        )
        
        # Call vision model
        messages = [
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": prompt,
                "images": [image_b64]
            }
        ]
        
        response = await ollama_client.chat(
            model=self.model,
            messages=messages,
            temperature=0.2,  # Even lower temperature for document analysis
        )
        
        logger.debug(
            "Document image described",
            page=page_number,
            image_index=image_index,
            original_size=(orig_width, orig_height),
            response_length=len(response)
        )
        
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
        
        Note: This method analyzes the entire page as an image.
        For individual images extracted from the page, use describe_document_image.
        
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
        
        DEPRECATED: We now process ALL images regardless of size.
        This method is kept for backward compatibility but always returns True
        if there are any images.
        
        Args:
            page_image_bytes: Page image bytes (unused)
            page_area: Total page area (unused)
            image_areas: List of image areas on the page
            
        Returns:
            True if there are any images on the page
        """
        # Process ALL images - even small images can contain important info
        return len(image_areas) > 0
    
    async def describe_images_batch(
        self,
        images: List[Tuple[bytes, int, int]],  # (image_bytes, page_number, image_index)
        text_context: Optional[str] = None,
        batch_size: int = 4
    ) -> List[Tuple[int, int, str]]:
        """
        Describe multiple images in batches for better performance.
        
        Qwen3 VL supports multiple images in a single request, which is
        much faster than processing each image individually.
        
        Args:
            images: List of tuples (image_bytes, page_number, image_index)
            text_context: Optional surrounding text context
            batch_size: Number of images to process per API call (2-4 recommended)
            
        Returns:
            List of tuples (page_number, image_index, description)
        """
        results = []
        
        # Process images in batches
        for i in range(0, len(images), batch_size):
            batch = images[i:i + batch_size]
            
            try:
                batch_results = await self._process_image_batch(batch, text_context)
                results.extend(batch_results)
            except Exception as e:
                logger.warning(f"Batch processing failed, falling back to individual: {e}")
                # Fallback to individual processing
                for image_bytes, page_num, img_idx in batch:
                    try:
                        desc = await self.describe_document_image(
                            image_data=image_bytes,
                            page_number=page_num,
                            image_index=img_idx,
                            text_context=text_context
                        )
                        results.append((page_num, img_idx, desc))
                    except Exception as inner_e:
                        logger.warning(f"Individual image failed: {inner_e}")
                        results.append((page_num, img_idx, ""))
        
        return results
    
    async def _process_image_batch(
        self,
        batch: List[Tuple[bytes, int, int]],
        text_context: Optional[str] = None
    ) -> List[Tuple[int, int, str]]:
        """
        Process a batch of images in a single API call.
        
        Args:
            batch: List of (image_bytes, page_number, image_index) tuples
            text_context: Optional context
            
        Returns:
            List of (page_number, image_index, description) tuples
        """
        if not batch:
            return []
        
        # Preprocess and encode all images
        image_b64_list = []
        image_info = []
        
        for image_bytes, page_num, img_idx in batch:
            processed = preprocess_image_for_vision(image_bytes)
            image_b64 = base64.b64encode(processed).decode("utf-8")
            image_b64_list.append(image_b64)
            image_info.append((page_num, img_idx))
        
        # Build prompt for batch processing
        context_section = ""
        if text_context and text_context.strip():
            truncated = text_context[:300] + "..." if len(text_context) > 300 else text_context
            context_section = f"\nDocument context: {truncated}\n"
        
        prompt = f"""You are analyzing {len(batch)} images extracted from a PDF document.
{context_section}
For EACH image (numbered 1 to {len(batch)}), provide a brief but informative description.

Format your response EXACTLY as follows:
[IMAGE 1]
(description of first image)

[IMAGE 2]
(description of second image)

{"[IMAGE 3]" + chr(10) + "(description of third image)" + chr(10) + chr(10) if len(batch) > 2 else ""}{"[IMAGE 4]" + chr(10) + "(description of fourth image)" + chr(10) + chr(10) if len(batch) > 3 else ""}
For each image, describe:
- Type (chart, diagram, photo, table, equation, etc.)
- Key content and information conveyed
- Any text, labels, or data shown"""

        # Call vision model with multiple images
        messages = [
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": prompt,
                "images": image_b64_list
            }
        ]
        
        response = await ollama_client.chat(
            model=self.model,
            messages=messages,
            temperature=0.2,
        )
        
        # Parse the response to extract individual descriptions
        descriptions = self._parse_batch_response(response, len(batch))
        
        # Combine with image info
        results = []
        for (page_num, img_idx), desc in zip(image_info, descriptions):
            results.append((page_num, img_idx, desc))
        
        logger.debug(
            "Batch processed",
            batch_size=len(batch),
            response_length=len(response)
        )
        
        return results
    
    def _parse_batch_response(self, response: str, expected_count: int) -> List[str]:
        """
        Parse a batch response to extract individual image descriptions.
        
        Args:
            response: Raw response from the model
            expected_count: Number of descriptions expected
            
        Returns:
            List of description strings
        """
        import re
        
        descriptions = []
        
        # Try to split by [IMAGE N] markers
        pattern = r'\[IMAGE\s*\d+\]'
        parts = re.split(pattern, response, flags=re.IGNORECASE)
        
        # First part is usually empty or preamble, skip it
        desc_parts = [p.strip() for p in parts[1:] if p.strip()]
        
        if len(desc_parts) >= expected_count:
            descriptions = desc_parts[:expected_count]
        else:
            # Fallback: just split evenly or use entire response
            if desc_parts:
                descriptions = desc_parts
            else:
                # Use entire response for all images (not ideal but better than nothing)
                descriptions = [response.strip()] * expected_count
        
        # Pad with empty strings if needed
        while len(descriptions) < expected_count:
            descriptions.append("")
        
        return descriptions


# Singleton instance
vision_service = VisionService()
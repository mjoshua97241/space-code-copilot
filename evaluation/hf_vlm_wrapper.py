"""
Hugging Face VLM Wrapper for Evaluation Framework

Adapts the Hugging Face FloorPlanVisionAIAdaptor model to the evaluation framework interface.
This allows the specialized floor plan VLM to be evaluated alongside GPT-4o and Gemini 2.0 Flash.

Usage:
    from evaluation.hf_vlm_wrapper import create_hf_extractor
    
    extractor = create_hf_extractor()
    result = extractor("path/to/blueprint.pdf", scale_override=1.0)
"""

import io
import json
import re
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add backend to path for imports
repo_root = Path(__file__).parent.parent
backend_path = repo_root / "backend"
sys.path.insert(0, str(backend_path))

try:
    from unsloth import FastVisionModel
    from transformers import AutoTokenizer
    from PIL import Image
    import torch
except ImportError as e:
    raise ImportError(
        f"Required packages missing for Hugging Face VLM: {e}\n"
        "Install: pip install unsloth transformers torch pillow"
    )

# Import from blueprint_extractor for prompt building and validation
from app.services.blueprint_extractor import (
    _build_extraction_prompt,
    _parse_llm_response,
    _validate_and_convert_rooms,
    _calculate_confidence_scores,
    _get_image_dimensions,
    _create_overlays_from_label_bbox,
)
from app.models.domain import Room, ExtractionConfidence, BlueprintExtractionResult


def create_hf_extractor(
    model_name: str = "sabaridsnfuji/FloorPlanVisionAIAdaptor",
    device: Optional[str] = None
):
    """
    Create extractor function compatible with evaluation framework.
    
    The returned function matches the signature:
    extract_rooms_from_blueprint(image_path, scale_override) -> BlueprintExtractionResult
    
    Args:
        model_name: Hugging Face model identifier
        device: Device to use ("cuda", "cpu", or None for auto-detect)
        
    Returns:
        Function that takes (image_path: str, scale_override: float) and returns BlueprintExtractionResult
        
    Raises:
        ImportError: If required packages are missing
        RuntimeError: If model loading fails
    """
    # Auto-detect device if not specified
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA requested but not available. "
            "Hugging Face VLM requires GPU for inference. "
            "Set device='cpu' to use CPU (may be very slow)."
        )
    
    print(f"🔄 Loading Hugging Face model: {model_name}")
    print(f"   Device: {device}")
    
    try:
        # Load model and tokenizer with 4-bit quantization for memory efficiency
        model, tokenizer = FastVisionModel.from_pretrained(
            model_name,
            load_in_4bit=True,
            use_gradient_checkpointing="unsloth"
        )
        FastVisionModel.for_inference(model)
        model = model.to(device)
        print(f"   ✓ Model loaded successfully")
    except Exception as e:
        raise RuntimeError(f"Failed to load Hugging Face model: {e}")
    
    def extractor(image_path: str, scale_override: float = 1.0) -> BlueprintExtractionResult:
        """
        Extract rooms from blueprint image using Hugging Face VLM.
        
        Args:
            image_path: Path to blueprint image (PNG, JPG, or PDF)
            scale_override: Scale factor (e.g., 1.0 for 1:100 scale)
            
        Returns:
            BlueprintExtractionResult with extracted rooms, confidence, and metadata
        """
        # Step 1: Load and prepare image
        image_path_obj = Path(image_path)
        if not image_path_obj.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Load image (handle PDF by converting first page to image)
        try:
            if image_path_obj.suffix.lower() == '.pdf':
                import fitz  # PyMuPDF
                pdf_doc = fitz.open(image_path)
                if len(pdf_doc) == 0:
                    raise ValueError("PDF has no pages")
                
                # Render first page to image
                page = pdf_doc[0]
                zoom = 2.0  # Match blueprint_extractor zoom
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                pdf_doc.close()
            else:
                image = Image.open(image_path)
        except Exception as e:
            raise ValueError(f"Failed to load image: {e}")
        
        # Step 2: Build prompt (reuse from blueprint_extractor)
        prompt = _build_extraction_prompt(scale_override)
        
        # Step 3: Format messages for HF model
        # HF models expect chat template format
        messages_hf = [
            {"role": "user", "content": [
                {"type": "image"},
                {"type": "text", "text": prompt}
            ]}
        ]
        
        # Step 4: Tokenize
        try:
            input_text = tokenizer.apply_chat_template(
                messages_hf,
                add_generation_prompt=True
            )
            inputs = tokenizer(
                image,
                input_text,
                add_special_tokens=False,
                return_tensors="pt",
            ).to(device)
        except Exception as e:
            raise RuntimeError(f"Tokenization failed: {e}")
        
        # Step 5: Generate response
        try:
            with torch.no_grad():
                output = model.generate(
                    **inputs,
                    max_new_tokens=2048,
                    use_cache=True,
                    temperature=0.0,  # Match current VLM settings (deterministic)
                )
        except Exception as e:
            raise RuntimeError(f"Model generation failed: {e}")
        
        # Step 6: Decode response
        response_text = tokenizer.decode(output[0], skip_special_tokens=True)
        
        # Step 7: Extract JSON from response (HF model may return extra text)
        # Try to find JSON object in response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(0)
        else:
            # If no JSON found, try parsing entire response
            # This may fail, but let _parse_llm_response handle it
            pass
        
        # Step 8: Parse JSON response (reuse from blueprint_extractor)
        try:
            parsed_response = _parse_llm_response(response_text)
        except Exception as e:
            raise ValueError(f"Failed to parse model response: {e}\nResponse: {response_text[:500]}")
        
        # Step 9: Extract rooms and plan metadata
        raw_rooms = parsed_response.get("rooms", [])
        if not raw_rooms:
            raise ValueError("No rooms extracted from blueprint")
        
        plan_title = parsed_response.get("plan_title", "") or parsed_response.get("title", "")
        
        # Step 10: Validate and convert to Room models (reuse from blueprint_extractor)
        validated_rooms = _validate_and_convert_rooms(raw_rooms, plan_title=plan_title)
        if not validated_rooms:
            raise ValueError("No valid rooms extracted after validation")
        
        # Step 11: Calculate confidence scores (reuse from blueprint_extractor)
        confidence = _calculate_confidence_scores(validated_rooms, parsed_response)
        
        # Step 12: Create overlays from label_bbox (if provided)
        overlays = []
        try:
            image_width, image_height = _get_image_dimensions(image_path)
            overlays = _create_overlays_from_label_bbox(
                raw_rooms=raw_rooms,
                validated_rooms=validated_rooms,
                image_width=image_width,
                image_height=image_height
            )
        except Exception as e:
            # Log but don't fail extraction if overlay creation fails
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to create overlays from label_bbox: {e}")
            overlays = []
        
        # Step 13: Build result
        confidence_obj = ExtractionConfidence(**confidence)
        
        result = BlueprintExtractionResult(
            rooms=validated_rooms,
            confidence=confidence_obj,
            scale_used=scale_override,
            scale_source="user_override",
            overlays=overlays,
            extraction_metadata={
                "model_used": model_name,
                "provider": "huggingface",
                "device": device,
            }
        )
        
        return result
    
    return extractor

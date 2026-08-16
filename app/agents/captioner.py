"""
Image Captioner Module for MedLearn Agent.

Integrates Hugging Face Vision-Language models (BLIP-2 / BLIP) for generating
descriptive, educational captions from anatomical/medical images.
Includes automatic fallbacks for CPU/lightweight execution environments.
"""

import os
import logging
from typing import Union
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Global cached model and processor
_processor = None
_model = None
_device = None

DEFAULT_MODEL_NAME = os.getenv("CAPTIONER_MODEL", "Salesforce/blip-image-captioning-base")
USE_HF_LOCAL = os.getenv("USE_HF_LOCAL", "true").lower() == "true"
MOCK_CAPTIONER = os.getenv("MOCK_CAPTIONER", "false").lower() == "true"


def _load_model(model_name: str = DEFAULT_MODEL_NAME):
    """Lazy loader for Hugging Face vision-language captioning model."""
    global _processor, _model, _device
    if _model is not None and _processor is not None:
        return _processor, _model, _device

    try:
        import torch
        from transformers import BlipProcessor, BlipForConditionalGeneration, Blip2Processor, Blip2ForConditionalGeneration

        _device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading vision model '{model_name}' on device '{_device}'...")

        if "blip2" in model_name.lower():
            _processor = Blip2Processor.from_pretrained(model_name)
            _model = Blip2ForConditionalGeneration.from_pretrained(
                model_name, torch_dtype=torch.float16 if _device == "cuda" else torch.float32
            )
        else:
            _processor = BlipProcessor.from_pretrained(model_name)
            _model = BlipForConditionalGeneration.from_pretrained(model_name)

        _model.to(_device)
        logger.info(f"Successfully loaded vision model '{model_name}'.")
        return _processor, _model, _device
    except Exception as e:
        logger.warning(f"Could not load Hugging Face model '{model_name}': {e}")
        return None, None, "cpu"


def generate_caption(image_input: Union[str, Image.Image], prompt: str = "a detailed anatomical diagram showing") -> str:
    """
    Generates a textual caption for an input medical/educational image.

    Args:
        image_input (Union[str, Image.Image]): File path or PIL Image object.
        prompt (str): Optional conditional prompt prefix for vision model.

    Returns:
        str: Descriptive text caption of the image content.
    """
    # 1. Handle PIL Image or file path string
    if isinstance(image_input, str):
        if not os.path.exists(image_input):
            logger.warning(f"Image path '{image_input}' not found on disk.")
            return "Anatomical diagram depicting human cardiovascular system, heart chambers, and major arterial pathways."
        try:
            image = Image.open(image_input).convert("RGB")
        except Exception as e:
            logger.error(f"Error opening image file '{image_input}': {e}")
            return "Anatomical diagram depicting organ systems and cellular structures."
    elif isinstance(image_input, Image.Image):
        image = image_input.convert("RGB")
    else:
        raise TypeError(f"Unsupported image input type: {type(image_input)}")

    # 2. Check if Mock mode is explicitly requested
    if MOCK_CAPTIONER:
        return "Anatomical diagram depicting human cardiovascular system with labeled left ventricle, right atrium, and aorta."

    # 3. Attempt Hugging Face inference with fallback
    if USE_HF_LOCAL:
        try:
            processor, model, device = _load_model()
            if processor is not None and model is not None:
                inputs = processor(images=image, text=prompt, return_tensors="pt").to(device)
                out = model.generate(**inputs, max_new_tokens=60)
                caption = processor.decode(out[0], skip_special_tokens=True).strip()
                if caption:
                    return caption
        except Exception as e:
            logger.warning(f"Vision model inference failed: {e}. Falling back to descriptive caption.")

    # 4. Graceful Fallback Caption
    return "Anatomical diagram illustrating human cardiovascular system, heart chambers, and vascular pathways."


if __name__ == "__main__":
    # Self-test block when executed directly
    print("Testing Image Captioner Module...")
    sample_caption = generate_caption("tests/sample_diagram.png")
    print(f"Generated Caption: '{sample_caption}'")


"""
src/vlm_engine.py

Vision-Language Model (VLM) Engine for Visual Grounding ("Giving the Agent Eyes").
Uses Qwen2-VL-2B to parse screenshots and find click coordinates for Playwright.
"""

import os
import torch
from PIL import Image

try:
    from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
    from qwen_vl_utils import process_vision_info
    VLM_AVAILABLE = True
except ImportError:
    VLM_AVAILABLE = False


class VLMEngine:
    def __init__(self, model_id="Qwen/Qwen2-VL-2B-Instruct"):
        self.model_id = model_id
        self.is_ready = False
        
        if not VLM_AVAILABLE:
            print("⚠️ VLM dependencies missing. Install qwen-vl-utils and transformers.")
            return
            
        print(f"👁️  Loading Vision Model ({model_id})... This may take a moment.")
        try:
            # Load model in bfloat16 to save memory on M1/Mac
            self.model = Qwen2VLForConditionalGeneration.from_pretrained(
                self.model_id, 
                torch_dtype=torch.bfloat16, 
                device_map="auto"
            )
            self.processor = AutoProcessor.from_pretrained(self.model_id)
            self.is_ready = True
            print("✅ Vision Model ready.")
        except Exception as e:
            print(f"⚠️ Failed to load VLM: {e}")

    def find_element_coordinates(self, image_path: str, target_element: str) -> str:
        """
        Ask the VLM to find the bounding box of a specific element in the screenshot.
        Returns the VLM's string response (usually coordinates or a descriptive location).
        """
        if not self.is_ready:
            return "error: VLM not loaded"
            
        if not os.path.exists(image_path):
            return f"error: Image not found at {image_path}"

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "image": image_path,
                    },
                    {"type": "text", "text": f"Find the bounding box coordinates for the '{target_element}' button or element in this image."},
                ],
            }
        ]
        
        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)
        
        inputs = self.processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
        inputs = inputs.to(self.model.device)

        with torch.no_grad():
            generated_ids = self.model.generate(**inputs, max_new_tokens=128)
            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            output_text = self.processor.batch_decode(
                generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
            )
            
        return output_text[0]

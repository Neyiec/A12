import base64
import mimetypes
from pathlib import Path

from langchain_core.messages import HumanMessage

from ...config import get_settings
from ...llm.model_factory import create_chat_model_from_settings


async def parse_image(path: Path, prompt: str | None = None) -> tuple[str, dict]:
    ocr_text = _ocr_image(path)
    vision_text = await describe_image(path, prompt)
    blocks = []
    if ocr_text:
        blocks.append(f"图片 OCR 文本:\n{ocr_text}")
    if vision_text:
        blocks.append(f"图片视觉理解:\n{vision_text}")
    return "\n\n".join(blocks), {
        "modality": "image",
        "ocr_available": bool(ocr_text),
        "vision_available": bool(vision_text),
    }


async def describe_image(path: Path, prompt: str | None = None) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        return ""
    try:
        model = create_chat_model_from_settings(settings, temperature=0.1)
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        data_url = f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"
        message = HumanMessage(content=[
            {
                "type": "text",
                "text": prompt or "请提取这张图片中可用于教学课件生成的文字、图表含义、知识点和可引用的信息，使用中文，简洁但完整。",
            },
            {"type": "image_url", "image_url": {"url": data_url}},
        ])
        response = await model.ainvoke([message])
        return str(response.content or "").strip()
    except Exception:
        return ""


def _ocr_image(path: Path) -> str:
    try:
        from PIL import Image
        import pytesseract

        return pytesseract.image_to_string(Image.open(path), lang="chi_sim+eng").strip()
    except Exception:
        return ""

import base64
import logging
import mimetypes
from pathlib import Path

from langchain_core.messages import HumanMessage

from ...config import get_settings
from ...llm.model_factory import create_chat_model_from_settings

# 统一日志约定（main.py 启动时 basicConfig）
logger = logging.getLogger("a12_ppt.resources.parsers.vision")

# 视觉理解单次调用耗时 = settings.request_timeout_seconds（逐图串行），
# 由 ENABLE_VISION_PARSE 总开关控制；LongCat 等不支持图片输入的模型务必保持关闭


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
    # 开关关闭时直接跳过视觉调用（纯文本模型/未配 key 场景），避免逐图烧满超时
    if not settings.enable_vision_parse:
        return ""
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
    except Exception as exc:
        # 视觉理解是增强项，失败降级为空文本，但必须留下原因（模型不支持图片/超时/限流等）
        logger.warning("视觉理解调用失败 model=%s file=%s: %s", settings.openai_model, path.name, exc)
        return ""


def _ocr_image(path: Path) -> str:
    try:
        from PIL import Image
        import pytesseract

        return pytesseract.image_to_string(Image.open(path), lang="chi_sim+eng").strip()
    except Exception as exc:
        # OCR 依赖 tesseract 可执行文件，缺失时提示一次便于诊断
        logger.warning("图片 OCR 不可用（请检查 tesseract 安装与 PATH）: %s", exc)
        return ""

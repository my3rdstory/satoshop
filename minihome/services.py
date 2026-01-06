import io
import os
from typing import Dict, Any, Optional, Tuple

from django.core.files.base import ContentFile

from storage.utils import upload_file_to_s3

try:
    from PIL import Image, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def _open_image(image_file):
    if not PIL_AVAILABLE:
        return None, "Pillow 패키지가 설치되지 않았습니다."

    image = Image.open(image_file)
    image = ImageOps.exif_transpose(image)
    if image.mode == "RGBA":
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[-1])
        image = background
    elif image.mode != "RGB":
        image = image.convert("RGB")
    return image, None


def _resize_to_width(image, target_width: int):
    if image.width <= target_width:
        return image
    target_height = int(image.height * (target_width / image.width))
    return image.resize((target_width, target_height), Image.Resampling.LANCZOS)


def _resize_to_max(image, max_size: Tuple[int, int]):
    max_width, max_height = max_size
    scale = min(max_width / image.width, max_height / image.height, 1.0)
    new_width = int(image.width * scale)
    new_height = int(image.height * scale)
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)


def process_minihome_image(
    image_file,
    *,
    target_width: Optional[int] = None,
    max_size: Optional[Tuple[int, int]] = None,
) -> Dict[str, Any]:
    image, error = _open_image(image_file)
    if error:
        return {"success": False, "error": error}

    if target_width:
        image = _resize_to_width(image, target_width)
    if max_size:
        image = _resize_to_max(image, max_size)

    output = io.BytesIO()
    image.save(output, format="WEBP", quality=85, method=6)
    output.seek(0)

    base_name = os.path.splitext(image_file.name)[0] or "minihome"
    filename = f"{base_name}.webp"
    processed_file = ContentFile(output.getvalue(), name=filename)

    return {
        "success": True,
        "processed_file": processed_file,
        "width": image.width,
        "height": image.height,
        "filename": filename,
    }


def upload_minihome_image(
    image_file,
    *,
    prefix: str,
    target_width: Optional[int] = None,
    max_size: Optional[Tuple[int, int]] = None,
) -> Dict[str, Any]:
    process_result = process_minihome_image(
        image_file,
        target_width=target_width,
        max_size=max_size,
    )
    if not process_result["success"]:
        return process_result

    upload_result = upload_file_to_s3(process_result["processed_file"], prefix=prefix)
    if not upload_result["success"]:
        return upload_result

    return {
        "success": True,
        "file_path": upload_result["file_path"],
        "file_url": upload_result["file_url"],
        "width": process_result["width"],
        "height": process_result["height"],
    }

from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import BinaryIO

from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.datastructures import FileStorage


class UploadProblem(ValueError):
    pass


ALLOWED_INPUT_FORMATS = {"JPEG", "PNG", "WEBP", "HEIF", "HEIC"}


def save_photo(photo: FileStorage | None, namespace: str, submission_id: str) -> str | None:
    if photo is None or not photo.filename:
        return None

    raw = photo.read()
    if not raw:
        return None
    if len(raw) > current_app.config["MAX_CONTENT_LENGTH"]:
        raise UploadProblem("The photo exceeds the configured upload limit.")

    try:
        image = Image.open(io.BytesIO(raw))
        image.verify()
        image = Image.open(io.BytesIO(raw))
    except (UnidentifiedImageError, OSError) as exc:
        raise UploadProblem("The uploaded file is not a supported image.") from exc

    fmt = (image.format or "").upper()
    if fmt not in ALLOWED_INPUT_FORMATS:
        raise UploadProblem("Use a JPEG, PNG or WebP photo.")

    image = ImageOps.exif_transpose(image)
    if image.mode not in {"RGB", "RGBA"}:
        image = image.convert("RGB")
    if image.mode == "RGBA":
        background = Image.new("RGB", image.size, (243, 241, 234))
        background.paste(image, mask=image.getchannel("A"))
        image = background

    max_edge = int(current_app.config["PHOTO_MAX_EDGE"])
    image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)

    digest = hashlib.sha256(raw + submission_id.encode("utf-8")).hexdigest()[:24]
    relative = Path(namespace) / f"{digest}.webp"
    destination = Path(current_app.config["UPLOAD_FOLDER"]) / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(
        destination,
        format="WEBP",
        quality=int(current_app.config["PHOTO_WEBP_QUALITY"]),
        method=6,
        optimize=True,
    )
    return relative.as_posix()


def delete_photo(relative_path: str | None) -> None:
    if not relative_path:
        return
    base = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    candidate = (base / relative_path).resolve()
    if base not in candidate.parents:
        raise UploadProblem("Invalid photo path.")
    candidate.unlink(missing_ok=True)

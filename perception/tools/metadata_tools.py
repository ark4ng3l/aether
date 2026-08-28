"""
MetadataTools — EXIF and file metadata extraction.
"""

import os

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


class MetadataTools(BaseTool):
    """Extracts EXIF and basic metadata from images and files."""

    def __init__(self):
        super().__init__(
            name="metadata_extractor",
            description="Extracts forensic metadata (EXIF, format, resolution) from local files.",
            category="File Forensics",
            icon="document_scanner",
            default_param_key="file_path",
            example_input="ui/index.html",
        )

    async def execute(self, file_path: str = "", **kwargs) -> ToolResult:  # noqa: D401
        file_path = file_path or kwargs.get("query", "")
        if not file_path:
            return ToolResult(success=False, data={}, error="No file path provided")

        logger.info(f"Extracting metadata from: {file_path}")

        if not os.path.exists(file_path):
            return ToolResult(success=False, data={}, error="File not found")

        try:
            metadata: dict = {
                "file_size": os.path.getsize(file_path),
                "last_modified": os.path.getmtime(file_path),
            }

            ext = os.path.splitext(file_path)[1].lower()
            if ext in {".jpg", ".jpeg", ".png", ".tiff", ".webp"} and _HAS_PIL:
                img = Image.open(file_path)
                metadata["format"] = img.format
                metadata["size"] = list(img.size)
                metadata["mode"] = img.mode

                exif_data = img.getexif()
                if exif_data:
                    readable: dict[str, str] = {}
                    for tag_id, value in exif_data.items():
                        tag_name = TAGS.get(tag_id, str(tag_id))
                        readable[tag_name] = str(value)
                    metadata["exif"] = readable

            return ToolResult(success=True, data=metadata)
        except Exception as exc:
            logger.error(f"Metadata extraction failed: {exc}")
            return ToolResult(success=False, data={}, error=str(exc))


metadata_tools = MetadataTools()

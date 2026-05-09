"""
Image Parser Module

This module handles image parsing using Tesseract OCR and PIL for text extraction
and image analysis, including metadata extraction and OCR processing.

Key Features:
    - Image metadata extraction (EXIF, format, size)
    - OCR text extraction using Tesseract
    - Image format support (JPEG, PNG, GIF, BMP, TIFF)
    - Image analysis and properties
    - Optional Tesseract OCR integration
    - PIL/Pillow integration

Main Classes:
    - ImageParser: Image parser for OCR and metadata extraction
    - ImageMetadata: Dataclass for image metadata representation
    - OCRResult: Dataclass for OCR result representation

Example Usage:
    >>> from veritasreason.parse import ImageParser
    >>> parser = ImageParser()
    >>> metadata = parser.extract_metadata("image.jpg")
    >>> ocr_result = parser.extract_text("image.jpg")
    >>> text = ocr_result.text

Author: VeritasReason Contributors
License: MIT
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from PIL import ExifTags, Image
from PIL.Image import Image as PILImage

from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker

from ..utils.helpers import safe_import

pytesseract, TESSERACT_AVAILABLE = safe_import("pytesseract")


@dataclass
class ImageMetadata:
    """Image metadata representation."""

    format: Optional[str] = None
    mode: Optional[str] = None
    size: tuple = (0, 0)
    width: int = 0
    height: int = 0
    exif: Dict[str, Any] = field(default_factory=dict)
    info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OCRResult:
    """OCR result representation."""

    text: str
    confidence: float = 0.0
    language: str = "eng"
    boxes: List[Dict[str, Any]] = field(default_factory=list)


class ImageParser:
    """Image parser for OCR and metadata extraction."""

    def __init__(self, **config):
        """
        Initialize image parser.

        Args:
            **config: Parser configuration
        """
        self.logger = get_logger("image_parser")
        self.config = config
        self.progress_tracker = get_progress_tracker()
        self.tesseract_path = config.get("tesseract_path")
        if self.tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path

    def parse(self, file_path: Union[str, Path], **options) -> Dict[str, Any]:
        """
        Parse image file.

        Args:
            file_path: Path to image file
            **options: Parsing options:
                - extract_text: Whether to extract text using OCR (default: False)
                - ocr_language: OCR language code (default: "eng")
                - extract_metadata: Whether to extract metadata (default: True)

        Returns:
            dict: Parsed image data
        """
        file_path = Path(file_path)

        # Track image parsing
        tracking_id = self.progress_tracker.start_tracking(
            file=str(file_path),
            module="parse",
            submodule="ImageParser",
            message=f"Image: {file_path.name}",
        )

        try:
            if not file_path.exists():
                raise ValidationError(f"Image file not found: {file_path}")

            # Validate image file
            try:
                with Image.open(file_path) as img:
                    img.verify()
            except Exception as e:
                raise ValidationError(f"Invalid image file: {e}")

            try:
                with Image.open(file_path) as img:
                    # Extract metadata
                    metadata = None
                    if options.get("extract_metadata", True):
                        self.progress_tracker.update_tracking(
                            tracking_id, message="Extracting metadata..."
                        )
                        metadata = self._extract_metadata(img, file_path)

                    # Extract text using OCR
                    ocr_result = None
                    if options.get("extract_text", False) and TESSERACT_AVAILABLE:
                        self.progress_tracker.update_tracking(
                            tracking_id, message="Running OCR..."
                        )
                        ocr_result = self.extract_text(
                            file_path, language=options.get("ocr_language", "eng")
                        )

                    self.progress_tracker.stop_tracking(
                        tracking_id,
                        status="completed",
                        message="Image parsed successfully",
                    )
                    return {
                        "metadata": metadata.__dict__ if metadata else None,
                        "ocr": ocr_result.__dict__ if ocr_result else None,
                        "text": ocr_result.text if ocr_result else None,
                    }

            except Exception as e:
                self.progress_tracker.stop_tracking(
                    tracking_id, status="failed", message=str(e)
                )
                self.logger.error(f"Failed to parse image {file_path}: {e}")
                raise ProcessingError(f"Failed to parse image: {e}")

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def extract_text(
        self, file_path: Union[str, Path], language: str = "eng", **options
    ) -> OCRResult:
        """
        Extract text from image using OCR.

        Args:
            file_path: Path to image file
            language: OCR language code
            **options: OCR options

        Returns:
            OCRResult: Extracted text and confidence
        """
        if not TESSERACT_AVAILABLE:
            raise ProcessingError(
                "Tesseract OCR is not available. Install pytesseract and tesseract."
            )

        file_path = Path(file_path)

        if not file_path.exists():
            raise ValidationError(f"Image file not found: {file_path}")

        try:
            # Extract text
            text = pytesseract.image_to_string(str(file_path), lang=language)

            # Get detailed data with boxes
            data = pytesseract.image_to_data(
                str(file_path), lang=language, output_type=pytesseract.Output.DICT
            )

            # Calculate average confidence
            confidences = [conf for conf in data["conf"] if conf != -1]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            # Extract boxes
            boxes = []
            n_boxes = len(data["level"])
            for i in range(n_boxes):
                if data["text"][i].strip():
                    boxes.append(
                        {
                            "text": data["text"][i],
                            "confidence": data["conf"][i],
                            "left": data["left"][i],
                            "top": data["top"][i],
                            "width": data["width"][i],
                            "height": data["height"][i],
                        }
                    )

            return OCRResult(
                text=text.strip(),
                confidence=avg_confidence / 100.0,
                language=language,
                boxes=boxes,
            )

        except Exception as e:
            self.logger.error(f"Failed to extract text from image {file_path}: {e}")
            raise ProcessingError(f"Failed to extract text from image: {e}")

    def extract_metadata(self, file_path: Union[str, Path]) -> ImageMetadata:
        """
        Extract metadata from image.

        Args:
            file_path: Path to image file

        Returns:
            ImageMetadata: Image metadata
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise ValidationError(f"Image file not found: {file_path}")

        try:
            with Image.open(file_path) as img:
                # Extract EXIF data
                exif_data = {}
                if hasattr(img, "_getexif") and img._getexif():
                    exif_dict = img._getexif()
                    for tag_id, value in exif_dict.items():
                        tag = ExifTags.TAGS.get(tag_id, tag_id)
                        exif_data[str(tag)] = str(value)

                return ImageMetadata(
                    format=img.format,
                    mode=img.mode,
                    size=img.size,
                    width=img.width,
                    height=img.height,
                    exif=exif_data,
                    info=img.info or {},
                )

        except Exception as e:
            self.logger.error(f"Failed to extract metadata from image {file_path}: {e}")
            raise ProcessingError(f"Failed to extract metadata from image: {e}")

    def preprocess_image(self, file_path: Union[str, Path], **options) -> Path:
        """
        Preprocess image for better OCR results.

        Args:
            file_path: Path to image file
            **options: Preprocessing options:
                - resize: Resize factor
                - grayscale: Convert to grayscale
                - enhance_contrast: Enhance contrast

        Returns:
            Path: Path to preprocessed image
        """
        file_path = Path(file_path)

        with Image.open(file_path) as img:
            # Convert to grayscale if requested
            if options.get("grayscale", True):
                img = img.convert("L")

            # Resize if requested
            if options.get("resize"):
                resize_factor = options["resize"]
                new_size = (
                    int(img.width * resize_factor),
                    int(img.height * resize_factor),
                )
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # Enhance contrast if requested
            if options.get("enhance_contrast", True):
                from PIL import ImageEnhance

                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.5)

            # Save preprocessed image
            output_path = (
                file_path.parent / f"{file_path.stem}_preprocessed{file_path.suffix}"
            )
            img.save(output_path)

            return output_path

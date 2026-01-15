"""
Text extraction utilities for .docx and .txt files.
Used for direct report generation without transcription.
"""
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def extract_text_from_file(file_path: Path) -> Optional[str]:
    """
    Extract text content from .txt or .docx file.

    Args:
        file_path: Path to the file

    Returns:
        Extracted text or None if extraction fails
    """
    suffix = file_path.suffix.lower()

    try:
        if suffix == '.txt':
            return _extract_from_txt(file_path)
        elif suffix == '.docx':
            return _extract_from_docx(file_path)
        else:
            logger.warning(f"Unsupported file type for text extraction: {suffix}")
            return None
    except Exception as e:
        logger.error(f"Text extraction failed for {file_path}: {e}")
        return None


def _extract_from_txt(file_path: Path) -> str:
    """Extract text from .txt file."""
    # Try different encodings
    for encoding in ['utf-8', 'utf-8-sig', 'cp1251', 'latin-1']:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue

    # Fallback: read as binary and decode with errors='replace'
    with open(file_path, 'rb') as f:
        return f.read().decode('utf-8', errors='replace')


def _extract_from_docx(file_path: Path) -> str:
    """Extract text from .docx file."""
    try:
        from docx import Document
    except ImportError:
        logger.error("python-docx not installed. Run: pip install python-docx")
        raise ImportError("python-docx required for .docx extraction")

    doc = Document(file_path)

    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)

    # Also extract text from tables
    for table in doc.tables:
        for row in table.rows:
            row_text = []
            for cell in row.cells:
                cell_text = cell.text.strip()
                if cell_text:
                    row_text.append(cell_text)
            if row_text:
                paragraphs.append(" | ".join(row_text))

    return "\n\n".join(paragraphs)


def is_text_file(filename: str) -> bool:
    """Check if file is a text file (.txt or .docx)."""
    suffix = Path(filename).suffix.lower()
    return suffix in ['.txt', '.docx']

# app/ingestion.py
from __future__ import annotations

import io
from typing import Callable

from fastapi import UploadFile
from pypdf import PdfReader
import docx  # python-docx


def extract_text_from_pdf(file: UploadFile) -> str:
    """
    Read a PDF UploadFile and extract text from all pages.
    """
    # Read entire file into memory
    data = file.file.read()
    pdf_reader = PdfReader(io.BytesIO(data))
    texts = []

    for page in pdf_reader.pages:
        page_text = page.extract_text() or ""
        texts.append(page_text)

    # Join pages with some spacing
    return "\n\n".join(texts)


def extract_text_from_docx(file: UploadFile) -> str:
    """
    Read a DOCX UploadFile and extract paragraph text.
    """
    data = file.file.read()
    document = docx.Document(io.BytesIO(data))

    paragraphs = [p.text for p in document.paragraphs if p.text]
    return "\n".join(paragraphs)


def extract_contract_text(file: UploadFile) -> str:
    """
    Main dispatcher: choose extraction based on file extension / content type.
    If it's not PDF or DOCX, fall back to treating it as plain text.
    """
    filename = (file.filename or "").lower()
    content_type = (file.content_type or "").lower()

    extractor: Callable[[UploadFile], str]

    if filename.endswith(".pdf") or "pdf" in content_type:
        extractor = extract_text_from_pdf
    elif filename.endswith(".docx") or "word" in content_type:
        extractor = extract_text_from_docx
    else:
        # Fallback: assume it's text-like
        data = file.file.read()
        return data.decode("utf-8", errors="ignore")

    return extractor(file)

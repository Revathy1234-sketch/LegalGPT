import fitz  # PyMuPDF
import os
import re
import uuid
from typing import List, Dict, Any

class DocumentParser:
    REFERENCE_KEYWORDS = [
        "references",
        "bibliography",
        "doi.org",
        "visited on"
    ]

    URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.I)
    DOI_PATTERN = re.compile(r"\bdoi\s*:\s*\S+|\bdoi\.org\S*", re.I)
    CITATION_PATTERN = re.compile(
        r"(\[\d+\]|\(\d{4}\)|\(\d+[,;]\d*\)|et al\.|doi:|doi\.org)",
        re.I
    )
    AUTHOR_LIST_PATTERN = re.compile(
        r"\b[A-Z][a-z]+,?\s+[A-Z](?:\.|[A-Z])?\b"
    )
    PAGE_PATTERN = re.compile(r"\b(page|pp|p)\.?\s*\d+\b", re.I)

    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        doc = fitz.open(file_path)
        full_text = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            full_text.append(page.get_text())
        return "\n".join(full_text)

    @staticmethod
    def _is_reference_text(text: str) -> bool:
        return False

    @staticmethod
    def get_parent_child_chunks(text: str, parent_size: int = 1800, child_size: int = 400) -> List[Dict[str, Any]]:
        """
        Splits text into chunks. Each parent chunk contains multiple child chunks.
        """
        chunks = []
        text_length = len(text)

        parent_step = max(1, int(parent_size * 0.8))
        for p_start in range(0, text_length, parent_step):
            p_end = min(p_start + parent_size, text_length)
            parent_text = text[p_start:p_end].strip()
            if len(parent_text) < 100:
                continue
            if DocumentParser._is_reference_text(parent_text):
                continue

            parent_id = str(uuid.uuid4())
            child_step = max(1, int(child_size * 0.8))
            for c_start in range(p_start, p_end, child_step):
                c_end = min(c_start + child_size, p_end)
                if c_end - c_start < 100:
                    continue
                child_text = text[c_start:c_end].strip()
                if len(child_text) < 100:
                    continue
                if DocumentParser._is_reference_text(child_text):
                    continue

                chunks.append({
                    "child_id": str(uuid.uuid4()),
                    "parent_id": parent_id,
                    "child_text": child_text,
                    "parent_text": parent_text
                })

        return chunks

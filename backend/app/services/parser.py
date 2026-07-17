import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from ..config import get_settings


def _ocr(image: Image.Image) -> str:
    try:
        import pytesseract

        return pytesseract.image_to_string(image).strip()
    except Exception:
        return ""


def _save_page_image(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(path, "PNG", optimize=True)


def _text_page_image(text: str, path: Path) -> None:
    image = Image.new("RGB", (1240, 1754), "white")
    draw = ImageDraw.Draw(image)
    margin, y = 80, 80
    words = text.replace("\t", "    ").split()
    line = ""
    lines: list[str] = []
    for word in words:
        candidate = f"{line} {word}".strip()
        if len(candidate) > 95:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    for line in lines[:75]:
        draw.text((margin, y), line, fill="#172033")
        y += 21
    _save_page_image(image, path)


def parse_document(file_path: Path, file_type: str, doc_id: str) -> list[dict[str, Any]]:
    pages_dir = get_settings().storage_dir / "pages" / doc_id
    pages_dir.mkdir(parents=True, exist_ok=True)

    if file_type == "txt":
        text = file_path.read_text(encoding="utf-8", errors="replace").strip()
        image_path = pages_dir / "page_1.png"
        _text_page_image(text, image_path)
        return [{"page_number": 1, "text": text, "tables": [], "image_path": str(image_path)}]

    if file_type in {"png", "jpg", "jpeg"}:
        Image.MAX_IMAGE_PIXELS = get_settings().max_image_pixels
        with Image.open(file_path) as image:
            image.verify()
        with Image.open(file_path) as image:
            image.load()
            text = _ocr(image)
            image_path = pages_dir / "page_1.png"
            _save_page_image(image, image_path)
        return [{"page_number": 1, "text": text, "tables": [], "image_path": str(image_path)}]

    return _parse_pdf(file_path, pages_dir)


def _parse_pdf(file_path: Path, pages_dir: Path) -> list[dict[str, Any]]:
    import pdfplumber

    settings = get_settings()
    records: list[dict[str, Any]] = []
    with pdfplumber.open(file_path) as pdf:
        if len(pdf.pages) > settings.max_pdf_pages:
            raise ValueError(f"PDF exceeds the {settings.max_pdf_pages}-page limit")

        for index, page in enumerate(pdf.pages):
            page_number = index + 1
            image_path = pages_dir / f"page_{page_number}.png"

            text = (page.extract_text() or "").strip()
            tables = []
            try:
                for table in page.extract_tables() or []:
                    if not table:
                        continue
                    tables.append({"rows": [[cell or "" for cell in row] for row in table]})
            except Exception:
                tables = []

            if len(text) < 40:
                image = _render_pdf_page(file_path, page_number, settings.pdf_render_dpi)
                _save_page_image(image, image_path)
                ocr_text = _ocr(image)
                if len(ocr_text) > len(text):
                    text = ocr_text

            records.append(
                {
                    "page_number": page_number,
                    "text": text,
                    "tables": tables,
                    "image_path": str(image_path),
                }
            )
    return records


def _render_pdf_page(
    file_path: Path,
    page_number: int,
    dpi: int | None = None,
) -> Image.Image:
    if dpi is None:
        dpi = get_settings().pdf_render_dpi
    dpi = max(72, min(dpi, 150))
    try:
        import pypdfium2 as pdfium

        document = pdfium.PdfDocument(str(file_path))
        page = document[page_number - 1]
        bitmap = page.render(scale=dpi / 72)
        image = bitmap.to_pil().convert("RGB")
        bitmap.close()
        page.close()
        document.close()
        return image
    except Exception:
        pass

    try:
        from pdf2image import convert_from_path

        rendered = convert_from_path(
            str(file_path),
            dpi=dpi,
            first_page=page_number,
            last_page=page_number,
            fmt="png",
            thread_count=1,
        )
        if rendered:
            return rendered[0]
    except Exception as exc:
        raise ValueError(f"Unable to render PDF page {page_number}") from exc


def serialize_tables(tables: list[dict[str, Any]]) -> str:
    return json.dumps(tables, ensure_ascii=False)

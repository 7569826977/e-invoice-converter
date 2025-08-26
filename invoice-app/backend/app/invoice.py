import os
import re
import uuid
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import xml.etree.ElementTree as ET
from xml.dom import minidom
import pdfplumber

# --- Tesseract yolu (Windows) ---
# Kurulumun farklıysa burayı güncelle:
DEFAULT_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.name == "nt" and os.path.exists(DEFAULT_TESSERACT):
    pytesseract.pytesseract.tesseract_cmd = DEFAULT_TESSERACT

ALLOWED_EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}

def read_invoice(file_path: str) -> str:
    """PDF ise önce metin dene; boşsa OCR.
       Görsel ise direkt OCR (TR+EN)."""
    text = ""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""

        if not text.strip():
            # scan PDF → OCR
            pages = convert_from_path(file_path)  # Poppler lazım olabilir
            for page in pages:
                text += pytesseract.image_to_string(page, lang="tur+eng")
    else:
        img = Image.open(file_path)
        text = pytesseract.image_to_string(img, lang="tur+eng")

    return text


def extract_invoice_data(text: str) -> dict:
    """Regex ile alanlar. Harf büyüklüğünü önemseme."""
    data = {
        "FaturaNo": re.search(r"Seri No:\s*([A-Z0-9]+)", text, re.IGNORECASE),
        "VergiNo": re.search(r"Vergi No:\s*(\d+)", text, re.IGNORECASE),
        "MükellefNo": re.search(r"Mükellef No:\s*(\d+)", text, re.IGNORECASE),
        "MükellefAdi": re.search(r"Mükellef Adi:\s*(.+)", text, re.IGNORECASE),
        "VergiDairesiNo": re.search(r"Vergi Dairesi No:\s*(\d+)", text, re.IGNORECASE),
        "TicariUnvan": re.search(r"Ticari Ünvan:\s*(.+)", text, re.IGNORECASE),
        "Tutar": re.search(r"Fatura Tutari:\s*([\d.,]+)", text, re.IGNORECASE),
    }
    return {k: (m.group(1).strip() if m else "Bulunamadı") for k, m in data.items()}


def _prettify(elem: ET.Element) -> str:
    xml_bytes = ET.tostring(elem, encoding="utf-8")
    pretty = minidom.parseString(xml_bytes).toprettyxml(indent="  ")
    # boş satırları temizle
    lines = [ln for ln in pretty.splitlines() if ln.strip()]
    return "\n".join(lines)


def save_single_xml(data: dict, path: str) -> None:
    """Tek fatura için tek dosya (root=EInvoice)."""
    root = ET.Element("EInvoice")
    for k, v in data.items():
        ET.SubElement(root, k).text = v
    pretty = _prettify(root)
    with open(path, "w", encoding="utf-8") as f:
        f.write(pretty)


def append_to_master(data: dict, master_path: str) -> None:
    """Hepsini tek dosyada toplayan <Invoices> altına ekle."""
    if os.path.exists(master_path):
        try:
            tree = ET.parse(master_path)
            root = tree.getroot()
            if root.tag == "EInvoice":
                # eski formatı dönüştür
                old = root
                root = ET.Element("Invoices")
                root.append(old)
        except ET.ParseError:
            root = ET.Element("Invoices")
    else:
        root = ET.Element("Invoices")

    inv = ET.SubElement(root, "EInvoice")
    for k, v in data.items():
        ET.SubElement(inv, k).text = v

    pretty = _prettify(root)
    with open(master_path, "w", encoding="utf-8") as f:
        f.write(pretty)


def generate_unique_name(prefix: str, ext: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}{ext}"
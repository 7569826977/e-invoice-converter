import os
import re
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import xml.etree.ElementTree as ET
from xml.dom import minidom
import pdfplumber  # PDF text okuma
from tkinter import Tk, filedialog

# Eğer Windows kullanıyorsan Tesseract yolunu belirt
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
a = True

def read_invoice(file_path):
    text = ""

    if file_path.lower().endswith(".pdf"):
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""

        if not text.strip():
            print("[!] PDF metin tabanlı değil, OCR uygulanıyor...")
            pages = convert_from_path(file_path)
            for page in pages:
                text += pytesseract.image_to_string(page, lang="tur")
    else:
        text = pytesseract.image_to_string(Image.open(file_path), lang="tur+eng")

    return text


def choose_file():
    root = Tk()
    root.withdraw()  # Tk pencereyi gizle
    file_path = filedialog.askopenfilename(
        title="Bir dosya seçin",
        filetypes=[("PDF ve Resimler", "*.pdf;*.png;*.jpg;*.jpeg;*.tiff;*.bmp"), ("Tüm Dosyalar", "*.*")]
    )
    return file_path

def extract_invoice_data(text):
    """Regex ile fatura verilerini ayıkla"""
    data = {
        "FaturaNo": re.search(r"Seri No:\s*([A-Z0-9]+)", text, re.IGNORECASE),
        "VergiNo": re.search(r"Vergi No:\s*(\d+)", text, re.IGNORECASE),
        "MükellefNo": re.search(r"Mükellef No:\s*(\d+)", text, re.IGNORECASE),
        "MükellefAdi": re.search(r"Mükellef Adi:\s*(.+)", text, re.IGNORECASE),
        "VergiDairesiNo": re.search(r"Vergi Dairesi No:\s*(\d+)", text, re.IGNORECASE),
        "TicariUnvan": re.search(r"Ticari Ünvan:\s*(.+)", text, re.IGNORECASE),
        "Tutar": re.search(r"Fatura Tutari:\s*([\d.,]+)", text, re.IGNORECASE),
    }

    return {k: (v.group(1).strip() if v else "Bulunamadı") for k, v in data.items()}


def prettify_xml(elem):
    """Pretty-print yapar ve gereksiz boş satırları temizler"""
    rough_string = ET.tostring(elem, encoding='utf-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")
    # Boş satırları temizle
    lines = [line for line in pretty_xml.split('\n') if line.strip()]
    return '\n'.join(lines)


def save_to_xml(data, output_file="efaturalar.xml"):
    """XML’e yeni fatura ekleyerek kaydeder (pretty-print)"""
    # 1️⃣ Dosya varsa aç, yoksa yeni root oluştur
    if os.path.exists(output_file):
        try:
            tree = ET.parse(output_file)
            root = tree.getroot()
            if root.tag == "EInvoice":
                old_invoice = root
                root = ET.Element("Invoices")
                root.append(old_invoice)
        except ET.ParseError:
            # Dosya bozuk veya boşsa yeni root oluştur
            root = ET.Element("Invoices")
    else:
        root = ET.Element("Invoices")

    # 2️⃣ Yeni fatura ekle
    invoice_elem = ET.SubElement(root, "EInvoice")
    for key, value in data.items():
        ET.SubElement(invoice_elem, key).text = value

    # 3️⃣ Pretty-print ve boş satır temizleme
    xml_str = ET.tostring(root, encoding='utf-8')
    parsed = minidom.parseString(xml_str)
    lines = [line for line in parsed.toprettyxml(indent="  ").split('\n') if line.strip()]
    pretty_xml = '\n'.join(lines)

    # 4️⃣ Dosyaya kaydet
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(pretty_xml)

    print(f"[+] XML kaydedildi: {output_file}")
    
if __name__ == "__main__":
    while a:
        choice = input("Dosya gezgini için 1 terminalden seçmek için 2 çıkmak için q giriniz ").strip()
        if choice == 'q':
            print("Çıkılıyor...")
            break
        elif choice == '1':
            file_path = choose_file()
        elif choice == '2':
            file_path = input("PDF veya resim dosyasının yolunu girin: ")
        else:
            print("Geçersiz seçim! Lütfen 1, 2 veya q girin.")
            
        if not file_path:
            print("Dosya seçilmedi!")
            continue
        elif not os.path.exists(file_path):
            print("Dosya bulunamadı!")
            continue
        elif os.path.isdir(file_path):
            print("HATA: Lütfen dosyanın tam yolunu girin, klasör değil.")
            continue
        else:
            print("[*] Fatura okunuyor...")
            text = read_invoice(file_path)

            print("[*] Bilgiler ayıklanıyor...")
            data = extract_invoice_data(text)

            # 🔹 Sabit dosya adı kullan
            output_file = "efaturalar.xml"
            print("[*] XML kaydediliyor...")
            save_to_xml(data, output_file)
        
        continue_choice = input("Başka bir dosya işlemek ister misiniz? (E/H): ").strip().upper()
        if continue_choice != 'E':
            a = False
            print("Çıkılıyor...")
        else:
            print("Yeni dosya için devam ediliyor...")

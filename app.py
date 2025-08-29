from flask import Flask, render_template, request, jsonify
import os
import re
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import xml.etree.ElementTree as ET
from xml.dom import minidom
import pdfplumber

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def read_invoice(file_path):
    text = ""
    if file_path.lower().endswith(".pdf"):
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        if not text.strip():
            pages = convert_from_path(file_path)
            for page in pages:
                text += pytesseract.image_to_string(page, lang="tur")
    else:
        text = pytesseract.image_to_string(Image.open(file_path), lang="tur+eng")
    return text

def extract_invoice_data(text):
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

def save_to_xml(data, output_file="efaturalar.xml"):
    if os.path.exists(output_file):
        try:
            tree = ET.parse(output_file)
            root = tree.getroot()
        except ET.ParseError:
            root = ET.Element("Invoices")
    else:
        root = ET.Element("Invoices")

    invoice_elem = ET.SubElement(root, "EInvoice")
    for key, value in data.items():
        ET.SubElement(invoice_elem, key).text = value

    xml_str = ET.tostring(root, encoding='utf-8')
    parsed = minidom.parseString(xml_str)
    pretty_xml = '\n'.join([line for line in parsed.toprettyxml(indent=" ").split('\n') if line.strip()])

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(pretty_xml)
    return output_file


@app.route("/")
def index():
    return render_template("index.html")

# --- Önizleme (XML’e kaydetmeden) ---
@app.route("/preview", methods=["POST"])
def preview():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "Dosya seçilmedi!"}), 400

    results = []
    for file in files:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        text = read_invoice(file_path)
        data = extract_invoice_data(text)
        results.append(data)

    return jsonify({"invoices": results})

# --- XML kaydetme (kullanıcı onayından sonra) ---
@app.route("/save", methods=["POST"])
def save():
    invoices = request.json.get("invoices", [])
    if not invoices:
        return jsonify({"error": "Kaydedilecek veri yok"}), 400

    for inv in invoices:
        save_to_xml(inv)

    return jsonify({"message": f"{len(invoices)} fatura XML’e kaydedildi!"})


if __name__ == "__main__":
    app.run(debug=True)

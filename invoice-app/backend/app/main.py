import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from .invoice import (
    ALLOWED_EXTS,
    read_invoice,
    extract_invoice_data,
    save_single_xml,
    append_to_master,
    generate_unique_name,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
UPLOAD_DIR = os.path.join(ROOT_DIR, "uploads")
OUTPUT_DIR = os.path.join(ROOT_DIR, "outputs")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

MASTER_XML = os.path.join(OUTPUT_DIR, "efaturalar.xml")

app = FastAPI(title="E-Fatura OCR API")

# CORS: React/Frontend için
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite
        "http://localhost:3000",  # CRA
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*",  # geliştirme sürecinde serbest bırakmak istersen
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/api/invoices/extract")
async def extract_invoice(file: UploadFile = File(...)):
    # 1) Dosyayı diske al
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail=f"Desteklenmeyen dosya türü: {ext}")

    upload_name = generate_unique_name("upload", ext)
    upload_path = os.path.join(UPLOAD_DIR, upload_name)

    content = await file.read()
    with open(upload_path, "wb") as f:
        f.write(content)

    # 2) OCR + regex
    try:
        text = read_invoice(upload_path)
        data = extract_invoice_data(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"İşleme hatası: {e}")

    # 3) XML çıktıları
    # 3a) Tekil XML dosyası
    single_xml_name = generate_unique_name("invoice", ".xml")
    single_xml_path = os.path.join(OUTPUT_DIR, single_xml_name)
    save_single_xml(data, single_xml_path)

    # 3b) Master XML’e ekle
    append_to_master(data, MASTER_XML)

    # 4) JSON döndür + indirilebilir tekil XML linki
    return JSONResponse(
        {
            "fields": data,
            "single_xml": f"/api/invoices/xml/{single_xml_name}",
            "master_xml": "/api/invoices/xml/master",
        }
    )

@app.get("/api/invoices/xml/{filename}")
def download_single_xml(filename: str):
    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Dosya bulunamadı")
    return FileResponse(path, media_type="application/xml", filename=filename)

@app.get("/api/invoices/xml/master")
def download_master_xml():
    if not os.path.exists(MASTER_XML):
        raise HTTPException(status_code=404, detail="Henüz master XML yok")
    return FileResponse(MASTER_XML, media_type="application/xml", filename="efaturalar.xml")

[https://huggingface.co/spaces/tdnathmlenthusiast/Legal\_OCR](https://huggingface.co/spaces/tdnathmlenthusiast/Legal_OCR)

# Legal\_OCR: PDF Ingestion, OCR & Metadata Extraction

A robust pipeline for extracting text, tables, images, and rich metadata from legal PDFs. Exposed as both a Gradio web application on Hugging Face Spaces and a RESTful POST API deployed on Render.

---

## Table of Contents

1. [Live Demo & Space](#live-demo--space)
2. [API Endpoint](#api-endpoint)
3. [Project Overview](#project-overview)
4. [Key Features](#key-features)
5. [Architecture](#architecture)
6. [Installation & Deployment](#installation--deployment)

   * [Hugging Face Space (Docker)](#hugging-face-space-docker)
   * [Render Web Service](#render-web-service)
7. [Usage](#usage)

   * [Gradio UI](#gradio-ui)
   * [POST `/ingest` API](#post-ingest-api)
   * [Download JSON Results](#download-json-results)
8. [Output Structure](#output-structure)
9. [Requirements](#requirements)
10. [Repository Layout](#repository-layout)
11. [License & Acknowledgements](#license--acknowledgements)

---

## Live Demo & Space

🔗 **Hugging Face Space (Gradio UI):**
[https://huggingface.co/spaces/tdnathmlenthusiast/Legal\_OCR](https://huggingface.co/spaces/tdnathmlenthusiast/Legal_OCR)

---

## API Endpoint

📡 **Render Deployment (REST API):**
`POST https://legal-ocr-1.onrender.com/ingest`
Accepts multipart/form-data with field `file` (PDF), returns JSON with extracted content and metadata.

---

## Project Overview

The **Legal\_OCR** project provides:

* **Native & OCR text extraction** (PyMuPDF + PaddleOCR)
* **Table recognition** (Camelot lattice/stream or PPStructure)
* **Image capture** (embedded images)
* **Metadata enrichment** (regex, spaCy NER & rules, Legal‑BERT NER & classification)
* **Structured JSON output** consumable by downstream systems or bots

Interfaces:

1. **Gradio Web App** on Hugging Face Spaces for interactive uploads and downloads.
2. **Flask REST API** on Render for programmatic access.

---

## Key Features

* 🎯 **Hybrid Text Extraction**: native PDF text + OCR fallback
* 📊 **Table Parsing**: lattice & stream modes + HTML→JSON conversion
* 🗃️ **Metadata Layer**:

  * Regex for dates and party references
  * SpaCy-based NER & rule matchers
  * Fine-tuned Legal‑BERT pipelines for entities & clause types
* ⚙️ **Progress Indicators** in Gradio UI
* 💾 **Persistent Storage**: saves uploaded PDFs (`/uploads`) and JSON outputs (`/results`)
* 🔗 **Download Links** for JSON via `/results/<filename>` endpoint

---

## Architecture

```text
Client  --> Gradio UI or HTTP POST --> Flask Server  --> HF Space via gradio_client
                                              |
                                              +--> Local Save (/uploads, /results)
```

Components:

* **Gradio Client**: calls `/predict` on HF Space
* **Flask App**: `/ingest` endpoint, file handling, result serving
* **HF Space**: runs OCR & metadata pipeline on the Space

---

## Installation & Deployment

### Hugging Face Space (Docker Blank Container)

1. Create a new Space with **Docker** SDK.
2. Include in repo:

   * `Dockerfile`
   * `requirements.txt`
   * `app.py` (Flask + Gradio)
3. Push to HF Space; it builds and launches automatically.

```dockerfile
# sample Dockerfile
FROM python:3.10-slim
RUN apt-get update && apt-get install -y poppler-utils build-essential libglib2.0-0 libsm6 libxrender1 libfontconfig1
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . /app
WORKDIR /app
EXPOSE 7860
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:7860", "--workers", "2"]
```

### Render Web Service

1. Push `app.py`, `requirements.txt`, `packages.txt` to GitHub.
2. In Render dashboard, **New → Web Service**.
3. Connect repo, set:

   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `gunicorn app:app --timeout 180 --workers 1 --bind 0.0.0.0:$PORT`
4. Commit `packages.txt` with `poppler-utils` for system deps.
5. Deploy to obtain `https://legal-ocr-1.onrender.com`.

---

## Usage

### Gradio UI

1. Open Space URL.
2. Upload PDF.
3. View progress bar.
4. Click to download `output.json`.

### POST `/ingest` API

```bash
curl -F file=@path/to/doc.pdf \
     https://legal-ocr-1.onrender.com/ingest
```

Response:

```json
{
  "message": "Success",
  "saved_json_path": "results/<uuid>_output.json",
  "download_url": "https://.../results/<uuid>_output.json",
  "result": { /* full extraction */ }
}
```

### Download JSON Results

```bash
curl -O https://legal-ocr-1.onrender.com/results/<uuid>_output.json
```

---

## Output Structure

```json
{
  "text_pages": [ {"page":1, "text":"..."}, ... ],
  "image_content": [ {"page":1, "ocr_text":"...", "tables_html":["<table>...</table>"]}, ... ],
  "metadata": [ {"page":1, "metadata": {"dates":[], "parties":[], "clauses":[...] }}, ... ]
}
```

---

## Requirements

* **requirements.txt** lists Python libs: `Flask`, `gradio-client`, `PyMuPDF`, `pdf2image`, `paddleocr`, `paddlepaddle`, `camelot-py[base]`, `numpy`, `pandas`, `spacy`, `transformers`, `torch`, `tqdm`, `gradio`, `opencv-python`, `beautifulsoup4`, and `en_core_web_sm` wheel.
* **packages.txt** for OS-level: `poppler-utils`

---

## Repository Layout

```
legal-ocr/
├── LICENSE                                # Project license (MIT)
├── README.md                              # Project documentation and instructions
├── app-py                                 # Flask app for POST API (should be renamed to app.py)
├── api_run.py                             # Example script to call the API with any PDF
├── main_ocr.py                            # Core OCR and extraction pipeline
├── requirements.txt                       # Python dependencies
├── RFD.pdf                                # Sample testing PDF file
├── D SLT Correspondance .pdf              # Sample testing PDF file
├── output_RLTjson/                        # Folder with JSON output for RLT.pdf
│   └── ...                               
├── output_SLl_correspondence.json         # JSON output of SLT Correspondence PDF
└── .gitignore                             # Git ignore rules

Generated at runtime (not committed):

- `uploads/`  — saved uploaded PDFs
- `results/`  — saved JSON outputs from the API
```

---

## License & Acknowledgements

* **License**: MIT
* **Thanks to**:

  * [PyMuPDF](https://pymupdf.readthedocs.io/)
  * [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
  * [Camelot](https://camelot-py.readthedocs.io/)
  * [spaCy](https://spacy.io/) & [Legal‑BERT](https://huggingface.co/nlpaueb/legal-bert-base-uncased)
  * [pdf2image](https://github.com/Belval/pdf2image)
  * [Gradio](https://gradio.app/) & [Flask](https://flask.palletsprojects.com/)

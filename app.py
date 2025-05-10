import os
import uuid
import json
import traceback
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from gradio_client import Client, handle_file

# === Configuration ===
UPLOAD_DIR = "uploads"
RESULTS_DIR = "results"
ALLOWED_EXT = {"pdf"}
SPACE_ID = "tdnathmlenthusiast/Legal_OCR"
PREDICT_API = "/predict"

# === Prepare directories ===
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# === Initialize Flask & Hugging Face Client ===
app = Flask(__name__)
hf_client = Client(SPACE_ID)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

# === /ingest Endpoint ===
@app.route("/ingest", methods=["POST"])
def ingest():
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF files are allowed"}), 400

    try:
        # 1. Save PDF locally
        filename = secure_filename(file.filename)
        uid = uuid.uuid4().hex
        saved_pdf = os.path.join(UPLOAD_DIR, f"{uid}_{filename}")
        file.save(saved_pdf)

        # 2. Call Hugging Face Space via Gradio Client
        print(f"[INFO] Calling HF Space with: {saved_pdf}")
        result = hf_client.predict(
            file_obj=handle_file(saved_pdf),
            api_name=PREDICT_API
        )

        # 3. Save output JSON locally
        json_path = os.path.join(RESULTS_DIR, f"{uid}_output.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        # 4. Return response with full payload & download URL
        filename_json = os.path.basename(json_path)
        download_url = f"{request.url_root}results/{filename_json}"
        return jsonify({
            "message": "Success",
            "saved_json_path": json_path,
            "download_url": download_url,
            "result": result
        }), 200

    except Exception as e:
        print("[ERROR] Internal failure:")
        traceback.print_exc()
        return jsonify({
            "error": f"Internal server error: {str(e)}"
        }), 500

# === Download Endpoint ===
@app.route("/results/<path:filename>", methods=["GET"])
def download_result(filename):
    return send_from_directory(RESULTS_DIR, filename, as_attachment=True)

# === Server entrypoint ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

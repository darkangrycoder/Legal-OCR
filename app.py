# app.py
import os
import uuid
import json
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from gradio_client import Client, handle_file

# Configuration
UPLOAD_DIR = "uploads"
RESULTS_DIR = "results"
ALLOWED_EXT = {"pdf"}
SPACE_ID = "tdnathmlenthusiast/Legal_OCR"
PREDICT_API = "/predict"  # Named endpoint in your Space

# Ensure directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# Initialize Gradio client once
hf_client = Client(SPACE_ID)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


app = Flask(__name__)


@app.route("/ingest", methods=["POST"])
def ingest():
    # 1) Validate upload
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF files are allowed"}), 400

    # 2) Save with a unique name
    original = secure_filename(file.filename)  # prevents path traversal
    uid = uuid.uuid4().hex               # avoid collisions
    saved_p = os.path.join(UPLOAD_DIR, f"{uid}_{original}")
    file.save(saved_p)

    # 3) Call the Hugging Face Space via gradio_client
    try:
        # wrap local path so client knows to upload it
        prediction = hf_client.predict(
            file_obj=handle_file(saved_p),
            api_name=PREDICT_API
        )
    except Exception as e:
        return jsonify({"error": f"Failed calling Gradio client: {str(e)}"}), 502

    # 4) Persist JSON (optional)
    out_path = os.path.join(RESULTS_DIR, f"{uid}_output.json")
    with open(out_path, "w", encoding="utf-8") as fp:
        json.dump(prediction, fp, ensure_ascii=False, indent=2)

    # 5) Return JSON body and local path
    return jsonify({
        "result": prediction,
        "saved_json": out_path
    }), 200


if __name__ == "__main__":
    # Bind to 0.0.0.0 for containerized environments
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

import requests, json

API_URL = "https://legal-ocr-1.onrender.com/ingest"
PDF_PATH = "/content/RFD.pdf" # add your any pdf file 

# 1) POST the PDF
with open(PDF_PATH, "rb") as f:
    resp = requests.post(API_URL, files={"file": f})

# 2) Inspect response
if resp.status_code == 200:
    data = resp.json()
    print("✅ API Response:")
    print(json.dumps(data, indent=2))

    # 3) Extract full payload
    extracted = data["result"]
    print("\n📜 Extracted JSON:")
    print(json.dumps(extracted, indent=2))

    # 4) Save to Colab
    with open("ocr_full_result.json", "w") as out:
        json.dump(extracted, out, indent=2)
    print("\n💾 Saved as ocr_full_result.json")
else:
    print(f"❌ Error {resp.status_code}: {resp.text}")

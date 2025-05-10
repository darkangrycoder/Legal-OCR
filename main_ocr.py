import fitz  # PyMuPDF
from paddleocr import PPStructure
from pdf2image import convert_from_path
import numpy as np
import json
import pandas as pd
import re
import spacy
from spacy.matcher import Matcher
from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification
import torch
from tqdm import tqdm

# Initialize PPStructure for layout analysis and table recognition
structure_engine = PPStructure(table=True, ocr=True, layout=True)

# Path to your PDF file
pdf_path = '/content/SLT Correspondance .pdf'

# Step 1: Initialize NLP tools
# Load SpaCy model for NER, dependency parsing, and rule-based matching
nlp = spacy.load("en_core_web_sm")
matcher = Matcher(nlp.vocab)

# Define regex patterns for dates and parties
date_pattern = r'\d{2}-[A-Za-z]{3}-\d{2}|\d{2}\.\d{2}\.\d{2}'
party_pattern = r'M/s [A-Za-z\s&-]+(?:Consortium)?'

# Define SpaCy rule-based matcher for claimants
pattern = [{"LOWER": "claimant"}, {"IS_PUNCT": True, "OP": "?"}, {"ENT_TYPE": "ORG"}]
matcher.add("CLAIMANT", [pattern])

# Load Legal-BERT for advanced NER and clause classification
ner_model = "nlpaueb/legal-bert-base-uncased"
tokenizer = AutoTokenizer.from_pretrained(ner_model)
model = AutoModelForTokenClassification.from_pretrained(ner_model)
ner_pipeline = pipeline("ner", model=model, tokenizer=tokenizer, aggregation_strategy="simple")
classifier = pipeline("text-classification", model="nlpaueb/legal-bert-base-uncased")

# Step 2: Extract text directly from PDF (for completeness) with progress
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text_output = []
    for page_num in tqdm(range(len(doc)), desc="Extracting text from PDF pages"):
        page = doc[page_num]
        text = page.get_text("text")
        text_output.append({
            "page": page_num + 1,
            "text": text
        })
    doc.close()
    return text_output

# Step 3: Extract OCR text and tables from images using PPStructure with progress
def extract_content_from_images(pdf_path):
    expected_headers = [
        "Sr. No.",
        "Activity",
        "Baseline Date (BL)",
        "Dates as per Update on 30.06.15",
        "Delay wrt. BL & Update on 30.06.15",
        "Remarks"
    ]
    images = convert_from_path(pdf_path)
    content_output = []

    for i, image in tqdm(enumerate(images), total=len(images), desc="Extracting content from images"):
        image_np = np.array(image)
        result = structure_engine(image_np)
        page_text = []
        page_tables = []
        for res in result:
            if res['type'] == 'text':
                for line in res['res']:
                    if 'text' in line:
                        page_text.append(line['text'])
                    else:
                        print(f"Warning: 'text' key not found in line: {line}")
            elif res['type'] == 'table':
                if 'html' in res['res']:
                    html = res['res']['html']
                    try:
                        tables = pd.read_html(html)
                        for df in tables:
                            if isinstance(df.columns, pd.MultiIndex):
                                df.columns = ['_'.join(map(str, col)).strip() for col in df.columns]
                            else:
                                df.columns = [str(col) for col in df.columns]
                            if len(df.columns) == len(expected_headers):
                                df.columns = expected_headers
                            table_data = df.to_dict(orient='records')
                            if table_data:
                                page_tables.append(table_data)
                    except Exception as e:
                        print(f"Error parsing table on page {i+1}: {e}")
                else:
                    print(f"Warning: 'html' key not found in table result: {res['res']}")
        content_output.append({
            "page": i + 1,
            "text": " ".join(page_text),
            "tables": page_tables
        })
    return content_output

# Step 4: Extract metadata using regex, SpaCy, and Legal-BERT with progress
def extract_metadata(text):
    metadata = {
        "dates": [],
        "parties": [],
        "claimants": [],
        "tribunals": [],
        "relationships": [],
        "clauses": []
    }

    # Regex-based extraction
    dates = re.findall(date_pattern, text)
    metadata["dates"] = dates
    parties = re.findall(party_pattern, text)
    metadata["parties"].extend(parties)

    # SpaCy NER, dependency parsing, and rule-based matching
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ == "ORG" and ent.text not in metadata["parties"]:
            metadata["parties"].append(ent.text)
        if ent.label_ == "GPE":
            metadata["tribunals"].append(ent.text)
    matches = matcher(doc)
    for match_id, start, end in matches:
        claimant = doc[start:end].text
        metadata["claimants"].append(claimant)
    for sent in doc.sents:
        for token in sent:
            if token.lower_ == "claimant" and token.dep_ == "nsubj":
                claim_action = token.head.text
                if claim_action in ["submitted", "filed"]:
                    obj = None
                    for child in token.head.children:
                        if child.dep_ in ["dobj", "obj"]:
                            obj = child.text
                    if obj:
                        metadata["relationships"].append({
                            "claimant": token.text,
                            "action": claim_action,
                            "object": obj
                        })

    # Legal-BERT NER
    ner_results = ner_pipeline(text)
    for entity in ner_results:
        if entity['entity_group'] in ['ORG', 'PARTY'] and entity['word'] not in metadata["parties"]:
            metadata["parties"].append(entity['word'])
        if entity['entity_group'] == 'GPE' and entity['word'] not in metadata["tribunals"]:
            metadata["tribunals"].append(entity['word'])

    # Legal-BERT clause classification
    sentences = text.split('. ')
    for sentence in sentences:
        if len(sentence) > 10:
            try:
                classification = classifier(sentence)
                if classification[0]['label'] == 'arbitration_clause' and classification[0]['score'] > 0.7:
                    metadata["clauses"].append({"type": "arbitration_clause", "text": sentence})
                elif classification[0]['label'] == 'indemnity_clause' and classification[0]['score'] > 0.7:
                    metadata["clauses"].append({"type": "indemnity_clause", "text": sentence})
            except Exception as e:
                print(f"Error classifying clause: {e}")

    return metadata

# Main function to process PDF and generate JSON output with metadata
def process_pdf(pdf_path):
    print("Extracting text from PDF...")
    extracted_text = extract_text_from_pdf(pdf_path)

    print("Extracting content from images (OCR and tables)...")
    ocr_content = extract_content_from_images(pdf_path)

    print("Extracting metadata...")
    metadata_output = []
    for page in tqdm(extracted_text, desc="Extracting metadata from pages"):
        text = page["text"]
        page_metadata = extract_metadata(text)
        metadata_output.append({
            "page": page["page"],
            "metadata": page_metadata
        })

    # Combine outputs into a dictionary
    output = {
        "extracted_text": extracted_text,
        "ocr_content": ocr_content,
        "metadata": metadata_output
    }

    # Save to JSON file
    with open('output.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=4)

    print("Extraction complete. Results saved to 'output.json'.")
    return output

# Run the process
if __name__ == "__main__":
    output = process_pdf(pdf_path)
    # For verification, print the metadata from page 1
    if output["metadata"]:
        print("\nExtracted Metadata from Page 1:")
        print(json.dumps(output["metadata"][0], indent=4))


from fastapi import FastAPI, UploadFile, File
from ldi.ingestion.pdf_loader import load_pdf
from ldi.ingestion.docx_loader import load_docx
from ldi.ingestion.cleaner import clean_text
from ldi.chunking.clause_splitter import split_clauses
import shutil
import os

app = FastAPI()

@app.post("/ingest/")
async def ingest_document(file: UploadFile = File(...)):
	temp_path = f"temp_{file.filename}"
	with open(temp_path, "wb") as buffer:
		shutil.copyfileobj(file.file, buffer)
	try:
		if file.filename.lower().endswith(".pdf"):
			text = load_pdf(temp_path)
		elif file.filename.lower().endswith(".docx"):
			text = load_docx(temp_path)
		else:
			os.remove(temp_path)
			return {"error": "Unsupported file type"}
		cleaned = clean_text(text)
	finally:
		os.remove(temp_path)
	return {"text": cleaned}


@app.post("/chunk/")
async def chunk_document(file: UploadFile = File(...), semantic_validation: bool = False):
	temp_path = f"temp_{file.filename}"
	with open(temp_path, "wb") as buffer:
		shutil.copyfileobj(file.file, buffer)
	try:
		if file.filename.lower().endswith(".pdf"):
			text = load_pdf(temp_path)
		elif file.filename.lower().endswith(".docx"):
			text = load_docx(temp_path)
		else:
			os.remove(temp_path)
			return {"error": "Unsupported file type"}
		cleaned = clean_text(text)
		clauses = split_clauses(cleaned, semantic_validation=semantic_validation)
	finally:
		os.remove(temp_path)
	return {"clauses": clauses, "count": len(clauses)}

if __name__ == "__main__":
	# Manual test: load and clean a sample PDF and DOCX
	pdf_path = "sample_contract.pdf"  # Place a sample file in project root
	docx_path = "sample_contract.docx"
	try:
		pdf_text = load_pdf(pdf_path)
		print("PDF Loaded. Preview:")
		print(clean_text(pdf_text)[:300])
	except Exception as e:
		print(f"PDF load failed: {e}")
	try:
		docx_text = load_docx(docx_path)
		print("DOCX Loaded. Preview:")
		print(clean_text(docx_text)[:300])
	except Exception as e:
		print(f"DOCX load failed: {e}")

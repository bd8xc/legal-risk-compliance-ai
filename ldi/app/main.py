
# FastAPI and file utilities for API and temp file handling
from fastapi import FastAPI, UploadFile, File
import shutil
import os

# PDF loader: extracts both text and tables from PDF
from ldi.ingestion.pdf_table_loader import extract_pdf_text_and_tables
# DOCX loader: extracts both text and tables from DOCX
from ldi.ingestion.docx_loader import load_docx
# Clause chunker: splits text into legal clause objects
from ldi.chunking.clause_splitter import split_clauses

# Initialize FastAPI app
app = FastAPI()



# ==============================
# INGEST ENDPOINT: Extracts text and tables from uploaded PDF or DOCX
# ==============================
@app.post("/ingest/")
async def ingest_document(file: UploadFile = File(...)):
    # Save uploaded file to a temporary path
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # PDF: extract text and tables
        if file.filename.lower().endswith(".pdf"):
            result = extract_pdf_text_and_tables(temp_path)
        # DOCX: extract text and tables
        elif file.filename.lower().endswith(".docx"):
            result = load_docx(temp_path)
        # Unsupported file type
        else:
            return {"error": "Unsupported file type"}
    finally:
        # Always remove temp file
        os.remove(temp_path)

    # Return dict: {"text": ..., "tables": ...}
    return result



# ==============================
# CHUNK ENDPOINT: Splits text into legal clauses and returns tables
# ==============================
@app.post("/chunk/")
async def chunk_document(file: UploadFile = File(...)):
    # Save uploaded file to a temporary path
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # PDF: extract text and tables
        if file.filename.lower().endswith(".pdf"):
            result = extract_pdf_text_and_tables(temp_path)
        # DOCX: extract text and tables
        elif file.filename.lower().endswith(".docx"):
            result = load_docx(temp_path)
        # Unsupported file type
        else:
            return {"error": "Unsupported file type"}

        # Get extracted text and tables
        text = result["text"]
        tables = result["tables"]

        # Split text into legal clause objects
        clauses = split_clauses(text)
    finally:
        # Always remove temp file
        os.remove(temp_path)

    # Return both clauses and tables, with counts
    return {
        "clauses": clauses,
        "tables": tables,
        "clause_count": len(clauses),
        "table_count": len(tables)
    }


from fastapi import FastAPI, UploadFile, File
from fastapi import APIRouter
from typing import List
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
# INGEST ENDPOINT: Extracts text and tables from uploaded PDF or DOCX (single file)
# ==============================
@app.post("/ingest/")
async def ingest_document(file: UploadFile = File(...)):
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    try:
        if file.filename.lower().endswith(".pdf"):
            result = extract_pdf_text_and_tables(temp_path)
        elif file.filename.lower().endswith(".docx"):
            result = load_docx(temp_path)
        else:
            return {"error": "Unsupported file type"}
    finally:
        os.remove(temp_path)
    return result


# ==============================
# CHUNK ENDPOINT: Splits text into legal clauses and returns tables (single file)
# ==============================
@app.post("/chunk/")
async def chunk_document(file: UploadFile = File(...)):
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    try:
        if file.filename.lower().endswith(".pdf"):
            result = extract_pdf_text_and_tables(temp_path)
        elif file.filename.lower().endswith(".docx"):
            result = load_docx(temp_path)
        else:
            return {"error": "Unsupported file type"}
        text = result["text"]
        tables = result["tables"]
        clauses = split_clauses(text)
    finally:
        os.remove(temp_path)
    return {
        "clauses": clauses,
        "tables": tables,
        "clause_count": len(clauses),
        "table_count": len(tables)
    }


# ==============================
# INGEST MULTI ENDPOINT: Extracts text and tables from multiple uploaded PDFs or DOCXs
# ==============================
@app.post("/ingest-multi/")
async def ingest_documents(files: List[UploadFile] = File(...)):
    results = []
    for file in files:
        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        try:
            if file.filename.lower().endswith(".pdf"):
                result = extract_pdf_text_and_tables(temp_path)
            elif file.filename.lower().endswith(".docx"):
                result = load_docx(temp_path)
            else:
                result = {"error": f"Unsupported file type: {file.filename}"}
        finally:
            os.remove(temp_path)
        results.append({"filename": file.filename, **result})
    return results



# ==============================
# CHUNK MULTI ENDPOINT: Splits text into legal clauses and returns tables (multiple files)
# ==============================
@app.post("/chunk-multi/")
async def chunk_documents(files: List[UploadFile] = File(...)):
    results = []
    for file in files:
        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        try:
            if file.filename.lower().endswith(".pdf"):
                result = extract_pdf_text_and_tables(temp_path)
            elif file.filename.lower().endswith(".docx"):
                result = load_docx(temp_path)
            else:
                results.append({"filename": file.filename, "error": "Unsupported file type"})
                continue
            text = result["text"]
            tables = result["tables"]
            clauses = split_clauses(text)
            results.append({
                "filename": file.filename,
                "clauses": clauses,
                "tables": tables,
                "clause_count": len(clauses),
                "table_count": len(tables)
            })
        finally:
            os.remove(temp_path)
    return results

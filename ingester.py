import os
import re
import time

# --- DEPENDENCY CHECK ---
try:
    from pypdf import PdfReader
except ImportError:
    print("Error: 'pypdf' is not installed. Run: pip install pypdf")
    exit(1)

from extractor import extract_from_text, generate_alias_map

# ==========================================
# MODULE: DOCUMENT INGESTION & SEGMENTATION
# ==========================================

def clean_text(text):
    """Vaporizes PDF artifacts, URLs, and page numbers that confuse NLP models."""
    if not text:
        return ""
    text = re.sub(r'https?://\S+', '', text)          # Remove URLs
    text = re.sub(r'Page \d+ of \d+', '', text)       # Remove "Page X of Y"
    text = re.sub(r'\d+/\d+$', '', text)              # Remove isolated fractions/dates at line ends
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE) # Remove isolated page numbers
    return text.strip()

def chunk_text_sliding_window(text, words_per_chunk=300, overlap=50):
    """
    Fallback Segmentation: Creates overlapping chunks to preserve context 
    if the document lacks standard legal headings.
    """
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + words_per_chunk])
        chunks.append(chunk)
        i += (words_per_chunk - overlap) 
    return chunks

def chunk_by_clause(text):
    """
    Primary Segmentation: Splits text based on standard legal clause patterns.
    """
    # Regex pattern to detect numbered headings, e.g., "ARTICLE 1", "Section 4.1", "1. "
    pattern = re.compile(r'\n(?=\s*(?:ARTICLE|SECTION|CLAUSE|Article|Section|Clause)\s+[0-9IVX]+|\s*\d{1,2}\.(?:\d{1,2})?\s+[A-Z])')
    
    raw_chunks = pattern.split(text)
    
    # Filter out empty strings or tiny fragments (less than 20 characters)
    clauses = [chunk.strip() for chunk in raw_chunks if len(chunk.strip()) > 20]
    
    # SAFEGUARD: If the document lacks standard formatting, use the sliding window fallback
    if len(clauses) < 3:
        print("Warning: Standard legal headings not detected. Falling back to sliding window chunking.")
        return chunk_text_sliding_window(text)
        
    return clauses

def process_pdf(file_path, doc_id, doc_type):
    """
    The main orchestrator. Reads the PDF, segments the clauses, runs the Scout Pass, 
    and feeds the data into the Neuro-Symbolic Extraction Engine.
    """
    start_time = time.time() 
    filename = os.path.basename(file_path)
    print("="*60)
    print(f"STARTING INGESTION: {filename}")
    print("="*60)
    
    try:
        reader = PdfReader(file_path)
        if reader.is_encrypted:
            print(f"Error: The document '{filename}' is encrypted and cannot be processed.")
            return

        full_text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                full_text += clean_text(extracted) + "\n"
                
        # 1. SEGMENTATION
        chunks = chunk_by_clause(full_text)
        print(f"Segmented document into {len(chunks)} formal Clause blocks.")
        
        if not chunks:
            print("Error: Document text extraction yielded no usable content.")
            return

        doc_meta = {
            "id": doc_id,
            "type": doc_type,
            "filename": filename
        }
        
        # 2. THE SCOUT PASS (Dynamic Alias Resolution)
        dynamic_alias_map = generate_alias_map(chunks[0])
        
        # 3. DEEP EXTRACTION LOOP
        for i, chunk in enumerate(chunks):
            clause_id = f"{doc_id}_CLAUSE_{i+1}"
            chunk_meta = {
                "clause_id": clause_id,
                "text": chunk
            }
            
            print(f"\n--- Processing Clause {i+1}/{len(chunks)} ({clause_id}) ---")
            extract_from_text(chunk_meta, doc_meta, dynamic_alias_map)
            
        # 4. PERFORMANCE LOGGING
        execution_time = round(time.time() - start_time, 2)
        print("\n" + "="*60)
        print(f"SUCCESS: Pipeline completed in {execution_time} seconds.")
        print("="*60 + "\n")
        
    except FileNotFoundError:
        print(f"Error: Could not find the file at {file_path}. Please check the path.")
    except Exception as e:
        print(f"Critical Error during PDF processing: {e}")

# ==========================================
# TEST EXECUTION BLOCK
# ==========================================
if __name__ == "__main__":
    # Ensure you have your test PDF in the same directory, or update this path.
    sample_pdf_path = "mock_contract_long.pdf" 
    
    # You can set reset=True in graph_manager.py to clear the DB before running this
    process_pdf(
        file_path=sample_pdf_path, 
        doc_id="LEASE_002", 
        doc_type="Lease Agreement"
    )
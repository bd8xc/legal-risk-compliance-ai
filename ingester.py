import os
from pypdf import PdfReader
from extractor import extract_from_text, generate_alias_map

def chunk_text(text, words_per_chunk=300, overlap=50):
    """Creates overlapping chunks so sentences are never cut in half."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + words_per_chunk])
        chunks.append(chunk)
        i += (words_per_chunk - overlap) # Step forward, but leave an overlap
    return chunks

def process_pdf(file_path, doc_id, doc_type):
    filename = os.path.basename(file_path)
    print(f"📄 Opening {filename}...")
    
    try:
        reader = PdfReader(file_path)
        full_text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                # Scrub out URLs and "Page X of Y" footers
                import re
                extracted = re.sub(r'https?://\S+', '', extracted)
                extracted = re.sub(r'Page \d+ of \d+', '', extracted)
                extracted = re.sub(r'\d+/\d+$', '', extracted) # Catch isolated dates/page fractions
                
                full_text += extracted + "\n"
                
        chunks = chunk_text(full_text, words_per_chunk=300)
        print(f"✂️ Split document into {len(chunks)} manageable chunks.")
        
        if not chunks:
            print("❌ Error: Document is empty.")
            return

        doc_meta = {
            "id": doc_id,
            "type": doc_type,
            "filename": filename
        }
        
        # ==========================================
        # 1. THE DETERMINISTIC SCOUT PASS
        # Uses Regex to find aliases and creates a dictionary
        # ==========================================
        dynamic_alias_map = generate_alias_map(chunks[0])
        
        # ==========================================
        # 2. THE DEEP READ
        # ==========================================
        for i, chunk in enumerate(chunks):
            print(f"\n--- Processing Chunk {i+1} of {len(chunks)} ---")
            extract_from_text(chunk, doc_meta, dynamic_alias_map)
            
        print(f"\n✅ Finished processing {filename}!")
        
    except FileNotFoundError:
        print(f"❌ Error: Could not find the file at {file_path}.")
    except Exception as e:
        print(f"❌ Error reading PDF: {e}")

# # ==========================================
# # TEST BLOCK
# # ==========================================
# if __name__ == "__main__":
#     sample_pdf_path = "1525784382619_AGREEMENT.pdf"
    
#     # Zero hardcoding! The script does all the work now.
#     process_pdf(
#         sample_pdf_path, 
#         doc_id="LEASE_001", 
#         doc_type="Lease Agreement"
    # )
# ==========================================
# TEST BLOCK
# ==========================================
if __name__ == "__main__":
    sample_pdf_path = "EX-10.pdf" # Pointing to the new file
    
    process_pdf(
        sample_pdf_path, 
        doc_id="LEASE_002", # Changed the ID
        doc_type="Lease Agreement"
    )
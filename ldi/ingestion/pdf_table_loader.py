"""
PDF Table Extraction Utility using pdfplumber
Extracts tables from PDF and returns them as text blocks for downstream clause splitting.
"""
import pdfplumber

def extract_pdf_text_and_tables(pdf_path: str) -> str:
    """
    Extracts all text and tables from a PDF file.
    Tables are appended as text blocks (rows joined by newlines, columns by tabs).
    Returns a single string with text and tables in reading order.
    """
    output_blocks = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # Extract main text
            page_text = page.extract_text() or ""
            if page_text.strip():
                output_blocks.append(page_text.strip())
            # Extract tables
            tables = page.extract_tables()
            for table in tables:
                # Join table rows as tab-separated, then join rows by newlines
                table_str = '\n'.join(['\t'.join(cell if cell is not None else '' for cell in row) for row in table])
                if table_str.strip():
                    output_blocks.append(table_str.strip())
    return '\n\n'.join(output_blocks)
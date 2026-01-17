# DOCX Loader for extracting text from DOCX files
import docx

def load_docx(file_path):
	doc = docx.Document(file_path)
	text = "\n".join([para.text for para in doc.paragraphs])
	return text

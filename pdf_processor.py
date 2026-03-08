import pypdf

def load_and_chunk_pdf(uploaded_file):
    """
    Extracts text from a PDF file object.
    """
    text_chunks = []
    try:
        pdf_reader = pypdf.PdfReader(uploaded_file)
        for page in pdf_reader.pages:
            text = page.extract_text()
            if text:
                text_chunks.append(text)
    except Exception as e:
        return [f"Error reading PDF: {str(e)}"]
    
    return text_chunks
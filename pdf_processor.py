import pypdf

def load_and_chunk_pdf(uploaded_file):
    """
    Reads a PDF file object and returns a list of text chunks.
    """
    try:
        reader = pypdf.PdfReader(uploaded_file)
        chunks = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                # Basic chunking by page, can be improved later
                chunks.append(text)
        return chunks
    except Exception as e:
        return [f"Error reading PDF: {str(e)}"]

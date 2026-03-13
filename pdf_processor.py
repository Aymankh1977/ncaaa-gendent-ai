import pypdf

def load_and_chunk_pdf(uploaded_file) -> list[str]:
    """
    Extracts text from a PDF, returning one string per page.
    Each page is a separate chunk so the AI can cite page-level sources.
    Empty pages are skipped.
    """
    chunks = []
    try:
        pdf_reader = pypdf.PdfReader(uploaded_file)
        for page_num, page in enumerate(pdf_reader.pages, start=1):
            text = page.extract_text()
            if text and text.strip():
                # Prepend a page marker so the AI can cite it
                chunks.append(f"[PAGE {page_num}]\n{text.strip()}")
    except Exception as e:
        return [f"Error reading PDF: {str(e)}"]

    return chunks
import pypdf

def load_and_chunk_pdf(file_obj, chunk_size=4000, overlap=400):
    """
    Reads a PDF file object and chunks the text.
    Increased chunk size to capture full tables in Course Specs.
    """
    try:
        reader = pypdf.PdfReader(file_obj)
        full_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
        
        chunks = []
        if len(full_text) < chunk_size:
            return [full_text]
            
        for i in range(0, len(full_text), chunk_size - overlap):
            chunks.append(full_text[i:i+chunk_size])
        
        return chunks
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return []

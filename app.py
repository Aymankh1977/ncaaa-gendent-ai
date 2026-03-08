import streamlit as st
import pandas as pd
from io import BytesIO
from docx import Document
from config import NCAAA_STANDARDS, NQF_DOMAINS, REQUIRED_DOCUMENTS
from ai_engine import get_client, analyze_evidence_for_standard, check_nqf_alignment, chat_with_ssr_expert
from pdf_processor import load_and_chunk_pdf

# Page Config
st.set_page_config(page_title="NCAAA Dentistry Accreditation AI", layout="wide", page_icon="🦷")

# CSS for NCAAA Styling
st.markdown("""
<style>
    .reportview-container { background: #f0f2f6 }
    .sidebar .sidebar-content { background: #262730 }
    h1 { color: #0e1117; }
    .stMetric { background-color: #ffffff; padding: 10px; border-radius: 5px; border: 1px solid #e0e0e0; }
</style>
""", unsafe_allow_html=True)

# Helper Function for Word Report
def generate_word_report(analysis_data, standard_name):
    doc = Document()
    doc.add_heading('NCAAA Compliance Report', 0)
    doc.add_heading(f'Standard: {standard_name}', level=1)
    
    # Compliance Rating
    doc.add_heading('Compliance Rating', level=2)
    doc.add_paragraph(analysis_data.get("compliance_rating", "N/A"))
    
    # Reviewer Comment
    doc.add_heading('Reviewer Commentary', level=2)
    doc.add_paragraph(analysis_data.get("reviewer_comment", "No comment provided."))
    
    # Strengths
    doc.add_heading('Strengths', level=2)
    for s in analysis_data.get("strengths", []):
        doc.add_paragraph(s, style='List Bullet')
        
    # Areas for Improvement
    doc.add_heading('Areas for Improvement', level=2)
    for gap in analysis_data.get("areas_for_improvement", []):
        doc.add_paragraph(gap, style='List Bullet')
        
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# Sidebar
with st.sidebar:
    st.image("https://etec.gov.sa/assets/images/logo.svg", width=200) # Placeholder for ETEC logo
    st.title("🦷 Dentistry Accreditation")
    st.markdown("---")
    st.header("📂 Evidence Locker")
    
    uploaded_files = st.file_uploader("Upload School Documents (Specs, Reports, Manuals)", type=['pdf'], accept_multiple_files=True)
    
    if "processed_data" not in st.session_state:
        st.session_state.processed_data = {}
        st.session_state.full_text = ""
    
    # Store the last analysis result for downloading
    if "last_analysis" not in st.session_state:
        st.session_state.last_analysis = None
    if "last_standard" not in st.session_state:
        st.session_state.last_standard = ""

    if uploaded_files and st.button("Analyze Documents"):
        with st.spinner("Processing documents against ETEC Standards..."):
            all_text = ""
            for file in uploaded_files:
                chunks = load_and_chunk_pdf(file)
                file_text = " ".join(chunks)
                all_text += f"\n--- DOC: {file.name} ---\n{file_text}"
                st.session_state.processed_data[file.name] = file_text
            st.session_state.full_text = all_text
            st.success("Analysis Complete!")
            
    # --- DOWNLOAD SECTION ---
    if st.session_state.last_analysis:
        st.markdown("---")
        st.header("📥 Download Results")
        docx_file = generate_word_report(st.session_state.last_analysis, st.session_state.last_standard)
        st.download_button(
            label="Download Word Report",
            data=docx_file,
            file_name=f"NCAAA_Report_{st.session_state.last_standard.replace(' ', '_')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

# Main Area
st.title("NCAAA Accreditation Intelligence Platform")
st.markdown("**Target:** General Dentistry Program | **Framework:** ETEC 2022/2024")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Accreditation Status", 
    "🧐 Standard Reviewer", 
    "🔗 NQF Alignment", 
    "📝 SSR Writer"
])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.subheader("Readiness Dashboard")
    
    if not st.session_state.processed_data:
        st.info("Upload documents to see readiness status.")
        
        # Display Required Docs Checklist visually
        st.write("### Required Evidence Checklist")
        cols = st.columns(3)
        for i, doc in enumerate(REQUIRED_DOCUMENTS):
            cols[i % 3].checkbox(doc, disabled=True)
    else:
        # Mock Logic to check file presence (Simple keyword match in filenames)
        uploaded_names = list(st.session_state.processed_data.keys())
        found_docs = [doc for doc in REQUIRED_DOCUMENTS if any(doc.lower().split()[0] in f.lower() for f in uploaded_names)]
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Documents Uploaded", len(uploaded_names))
        col2.metric("Required Docs Found", f"{len(found_docs)}/{len(REQUIRED_DOCUMENTS)}")
        col3.metric("Estimated Readiness", f"{int((len(found_docs)/len(REQUIRED_DOCUMENTS))*100)}%")
        
        st.progress(len(found_docs)/len(REQUIRED_DOCUMENTS))
        
        st.write("### Document Inventory")
        st.dataframe(pd.DataFrame({"Uploaded Files": uploaded_names, "Size (Est)": "PDF"}))

# --- TAB 2: STANDARD REVIEWER ---
with tab2:
    st.subheader("AI Compliance Review")
    
    selected_standard = st.selectbox("Select Standard to Audit", list(NCAAA_STANDARDS.keys()))
    
    if st.button("Run Compliance Audit"):
        if not st.session_state.full_text:
            st.error("Please upload documents first.")
        else:
            client = get_client()
            if client:
                with st.spinner(f"Auditing Standard: {selected_standard}..."):
                    # We pass the full text, but in production, you'd use RAG to fetch relevant chunks
                    analysis = analyze_evidence_for_standard(
                        client, 
                        selected_standard, 
                        NCAAA_STANDARDS[selected_standard], 
                        st.session_state.full_text
                    )
                    
                    if "error" in analysis:
                        st.error("AI Error: " + analysis['error'])
                    else:
                        # Save result to session state for downloading
                        st.session_state.last_analysis = analysis
                        st.session_state.last_standard = selected_standard
                        
                        # Display Results
                        r_col1, r_col2 = st.columns([1, 3])
                        with r_col1:
                            st.metric("Compliance Rating", analysis.get("compliance_rating", "N/A"))
                            st.caption("Based on Self-Evaluation Scales")
                        
                        with r_col2:
                            st.markdown(f"**Reviewer Comment:** {analysis.get('reviewer_comment')}")
                        
                        st.markdown("---")
                        c1, c2 = st.columns(2)
                        with c1:
                            st.success("✅ Strengths")
                            for s in analysis.get("strengths", []):
                                st.write(f"- {s}")
                        with c2:
                            st.error("⚠️ Areas for Improvement")
                            for gap in analysis.get("areas_for_improvement", []):
                                st.write(f"- {gap}")
            else:
                st.error("API Key not found. Please set ANTHROPIC_API_KEY environment variable.")

# --- TAB 3: NQF ALIGNMENT ---
with tab3:
    st.subheader("NQF & Learning Outcomes")
    st.markdown("Verifies if Program Learning Outcomes (PLOs) meet **NQF Level 6 (Dentistry)** requirements.")
    
    plo_input = st.text_area("Paste Program Learning Outcomes (PLOs) here if not in documents:")
    
    if st.button("Check NQF Alignment"):
        text_to_check = plo_input if plo_input else st.session_state.full_text
        if not text_to_check:
            st.warning("No text to analyze.")
        else:
            client = get_client()
            if client:
                with st.spinner("Analyzing against NQF Matrix..."):
                    result = check_nqf_alignment(client, text_to_check, NQF_DOMAINS)
                    st.markdown(result)
            else:
                st.error("API Key missing.")

# --- TAB 4: SSR WRITER ---
with tab4:
    st.subheader("Self-Study Report (SSR) Assistant")
    st.markdown("Ask the AI to draft sections of the SSR based on the uploaded evidence.")
    
    # Pre-canned prompts for Dentistry
    st.markdown("Try asking:")
    st.code("Draft the narrative for Standard 2.2 (Clinical Training) referencing the Field Experience Manual.")
    st.code("Analyze the faculty-to-student ratio in the clinics based on the uploaded data.")
    
    user_query = st.chat_input("Enter your request for the SSR...")
    
    if user_query:
        if not st.session_state.full_text:
            st.error("Upload documents first.")
        else:
            client = get_client()
            if client:
                with st.chat_message("user"):
                    st.write(user_query)
                
                with st.chat_message("assistant"):
                    with st.spinner("Drafting response..."):
                        response = chat_with_ssr_expert(client, st.session_state.full_text, user_query)
                        st.markdown(response)
            else:
                st.error("API Key missing.")

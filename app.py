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

# Helper Function for Word Report (Fixed to prevent crashes)
def generate_word_report(analysis_data, standard_name):
    doc = Document()
    doc.add_heading('NCAAA Compliance Report', 0)
    doc.add_heading(f'Standard: {str(standard_name)}', level=1)
    
    # Compliance Rating - Force string conversion to prevent TypeError
    doc.add_heading('Compliance Rating', level=2)
    rating = analysis_data.get("compliance_rating", "N/A")
    doc.add_paragraph(str(rating))
    
    # Reviewer Comment
    doc.add_heading('Reviewer Commentary', level=2)
    comment = analysis_data.get("reviewer_comment", "No comment provided.")
    doc.add_paragraph(str(comment))
    
    # Strengths
    doc.add_heading('Strengths', level=2)
    strengths = analysis_data.get("strengths", [])
    if isinstance(strengths, list):
        for s in strengths:
            doc.add_paragraph(str(s), style='List Bullet')
    else:
        doc.add_paragraph(str(strengths))
        
    # Areas for Improvement
    doc.add_heading('Areas for Improvement', level=2)
    gaps = analysis_data.get("areas_for_improvement", [])
    if isinstance(gaps, list):
        for gap in gaps:
            doc.add_paragraph(str(gap), style='List Bullet')
    else:
        doc.add_paragraph(str(gaps))
        
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# Sidebar
with st.sidebar:
    st.image("https://etec.gov.sa/assets/images/logo.svg", width=200) 
    st.title("🦷 Dentistry Accreditation")
    st.markdown("---")
    st.header("📂 Evidence Locker")
    
    uploaded_files = st.file_uploader("Upload School Documents", type=['pdf'], accept_multiple_files=True)
    
    if "processed_data" not in st.session_state:
        st.session_state.processed_data = {}
        st.session_state.full_text = ""
    
    # Session state for report downloading
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
            file_name=f"NCAAA_Report.docx",
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
        st.write("### Required Evidence Checklist")
        cols = st.columns(3)
        for i, doc in enumerate(REQUIRED_DOCUMENTS):
            cols[i % 3].checkbox(doc, disabled=True)
    else:
        uploaded_names = list(st.session_state.processed_data.keys())
        found_docs = [doc for doc in REQUIRED_DOCUMENTS if any(doc.lower().split()[0] in f.lower() for f in uploaded_names)]
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Documents Uploaded", len(uploaded_names))
        col2.metric("Required Docs Found", f"{len(found_docs)}/{len(REQUIRED_DOCUMENTS)}")
        col3.metric("Estimated Readiness", f"{int((len(found_docs)/len(REQUIRED_DOCUMENTS))*100)}%")
        st.progress(len(found_docs)/len(REQUIRED_DOCUMENTS))

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
                    analysis = analyze_evidence_for_standard(
                        client, 
                        selected_standard, 
                        NCAAA_STANDARDS[selected_standard], 
                        st.session_state.full_text
                    )
                    
                    if "error" in analysis:
                        st.error("AI Error: " + analysis['error'])
                    else:
                        st.session_state.last_analysis = analysis
                        st.session_state.last_standard = selected_standard
                        
                        r_col1, r_col2 = st.columns([1, 3])
                        with r_col1:
                            st.metric("Compliance Rating", analysis.get("compliance_rating", "N/A"))
                        with r_col2:
                            st.markdown(f"**Reviewer Comment:** {analysis.get('reviewer_comment')}")
                        
                        c1, c2 = st.columns(2)
                        with c1:
                            st.success("✅ Strengths")
                            for s in analysis.get("strengths", []): st.write(f"- {s}")
                        with c2:
                            st.error("⚠️ Areas for Improvement")
                            for gap in analysis.get("areas_for_improvement", []): st.write(f"- {gap}")
            else:
                st.error("API Key not found.")

# --- TAB 3: NQF ALIGNMENT ---
with tab3:
    st.subheader("NQF & Learning Outcomes")
    plo_input = st.text_area("Paste Program Learning Outcomes (PLOs) here if not in documents:")
    
    if st.button("Check NQF Alignment"):
        text_to_check = plo_input if plo_input else st.session_state.full_text
        if not text_to_check:
            st.warning("No text/docs found.")
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
    user_query = st.chat_input("Enter your request for the SSR...")
    
    if user_query:
        if not st.session_state.full_text:
            st.error("Upload documents first.")
        else:
            client = get_client()
            if client:
                with st.chat_message("user"): st.write(user_query)
                with st.chat_message("assistant"):
                    with st.spinner("Drafting response..."):
                        response = chat_with_ssr_expert(client, st.session_state.full_text, user_query)
                        st.markdown(response)
            else:
                st.error("API Key missing.")

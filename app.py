import streamlit as st
import pandas as pd
import json
from config import NCAAA_STANDARDS, NQF_DOMAINS, REQUIRED_DOCUMENTS
from ai_engine import get_client, analyze_evidence_for_standard, check_nqf_alignment, chat_with_ssr_expert
from pdf_processor import load_and_chunk_pdf 

st.set_page_config(page_title="NCAAA Dentistry Accreditation AI", layout="wide", page_icon="🦷")

st.markdown("""
<style>
    .reportview-container { background: #f0f2f6 }
    .sidebar .sidebar-content { background: #262730 }
    h1 { color: #0e1117; }
    .stMetric { background-color: #ffffff; padding: 10px; border-radius: 5px; border: 1px solid #e0e0e0; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.image("https://etec.gov.sa/assets/images/logo.svg", width=200) 
    st.title("🦷 Dentistry Accreditation")
    st.markdown("---")
    st.header("📂 Evidence Locker")
    
    uploaded_files = st.file_uploader("Upload School Documents", type=['pdf'], accept_multiple_files=True)
    
    if "processed_data" not in st.session_state:
        st.session_state.processed_data = {}
        st.session_state.full_text = ""

    if uploaded_files and st.button("Analyze Documents"):
        with st.spinner("Processing documents..."):
            all_text = ""
            for file in uploaded_files:
                chunks = load_and_chunk_pdf(file)
                file_text = " ".join(chunks)
                all_text += f"\n--- DOC: {file.name} ---\n{file_text}"
                st.session_state.processed_data[file.name] = file_text
            st.session_state.full_text = all_text
            st.success("Analysis Complete!")

st.title("NCAAA Accreditation Intelligence Platform")
st.markdown("**Target:** General Dentistry Program | **Framework:** ETEC 2022/2024")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Status", "🧐 Reviewer", "🔗 NQF", "📝 SSR Writer"])

# --- TAB 1 ---
with tab1:
    st.subheader("Readiness Dashboard")
    if not st.session_state.processed_data:
        st.info("Upload documents to see readiness status.")
    else:
        uploaded_names = list(st.session_state.processed_data.keys())
        found_docs = [doc for doc in REQUIRED_DOCUMENTS if any(doc.lower().split()[0] in f.lower() for f in uploaded_names)]
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Uploaded", len(uploaded_names))
        col2.metric("Matches", f"{len(found_docs)}/{len(REQUIRED_DOCUMENTS)}")
        col3.metric("Readiness", f"{int((len(found_docs)/len(REQUIRED_DOCUMENTS))*100)}%")
        st.progress(len(found_docs)/len(REQUIRED_DOCUMENTS))

# --- TAB 2: AUDIT ---
with tab2:
    st.subheader("AI Compliance Review")
    selected_standard = st.selectbox("Select Standard", list(NCAAA_STANDARDS.keys()))
    
    if "audit_result" not in st.session_state:
        st.session_state.audit_result = None

    if st.button("Run Compliance Audit"):
        if not st.session_state.full_text:
            st.error("Upload documents first.")
        else:
            client = get_client()
            if client:
                with st.spinner(f"Auditing Standard: {selected_standard}..."):
                    analysis = analyze_evidence_for_standard(
                        client, selected_standard, NCAAA_STANDARDS[selected_standard], st.session_state.full_text
                    )
                    st.session_state.audit_result = analysis
    
    if st.session_state.audit_result:
        analysis = st.session_state.audit_result
        if "error" in analysis:
            st.error(f"AI Error: {analysis['error']}")
        else:
            c1, c2 = st.columns([1, 3])
            c1.metric("Rating", analysis.get("compliance_rating", "N/A"))
            c2.info(analysis.get("reviewer_comment", "No comment generated."))
            
            s1, s2 = st.columns(2)
            with s1: 
                st.success("Strengths")
                for s in analysis.get("strengths", []): st.write(f"- {s}")
            with s2: 
                st.error("Improvements")
                for gap in analysis.get("areas_for_improvement", []): st.write(f"- {gap}")
            
            st.download_button("📥 Download Report", json.dumps(analysis, indent=4), "audit.json", "application/json")

# --- TAB 3: NQF ---
with tab3:
    st.subheader("NQF Alignment")
    plo_input = st.text_area("Paste PLOs here:")
    if st.button("Check NQF"):
        txt = plo_input if plo_input else st.session_state.full_text
        if not txt: st.warning("No text.")
        else:
            client = get_client()
            with st.spinner("Checking..."):
                res = check_nqf_alignment(client, txt, NQF_DOMAINS)
                st.markdown(res)
                st.download_button("📥 Download", res, "nqf.md")

# --- TAB 4: SSR ---
with tab4:
    st.subheader("SSR Assistant")
    q = st.chat_input("Ask about SSR...")
    if q and st.session_state.full_text:
        client = get_client()
        with st.chat_message("user"): st.write(q)
        with st.chat_message("assistant"):
            with st.spinner("Writing..."):
                res = chat_with_ssr_expert(client, st.session_state.full_text, q)
                st.markdown(res)
                st.download_button("📥 Download", res, "ssr.txt")
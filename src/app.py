import streamlit as st
from ai_engine import get_client, analyze_chunk, generate_compliance_report, query_documents
from pdf_processor import load_and_chunk_pdf
from pdf_generator import generate_pdf_report
from config import ETEC_STANDARDS_2025

st.set_page_config(page_title="NCAAA General Dentistry AI", layout="wide")

st.title("🦷 NCAAA/ETEC General Dentistry AI Platform")
st.markdown("Automated analysis against **Academic Standards for General Dentistry Programs 2025 (Version 2.0)**.")

if 'full_text_context' not in st.session_state:
    st.session_state['full_text_context'] = ""
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

tab1, tab2 = st.tabs(["📊 Accreditation Analyzer", "💬 Research Chat"])

# --- TAB 1: ANALYZER ---
with tab1:
    with st.sidebar:
        st.header("1. Select Standard")
        selected_key = st.selectbox(
            "Select ETEC 2025 Standard",
            options=list(ETEC_STANDARDS_2025.keys()),
            format_func=lambda x: ETEC_STANDARDS_2025[x]['title']
        )
        st.info(ETEC_STANDARDS_2025[selected_key]['definition'])
        
        st.header("2. Upload Evidence")
        uploaded_files = st.file_uploader(
            "Upload Course Specs, Annual Reports, QMS Manuals", 
            type=["pdf"], 
            accept_multiple_files=True
        )

    if st.button("Analyze Compliance", type="primary"):
        if not uploaded_files:
            st.error("Please upload PDF documents first.")
        else:
            try:
                client = get_client()
                st.write(f"### 🔍 Analyzing {len(uploaded_files)} documents...")
                
                all_evidence = []
                full_text_accumulator = ""
                
                prog = st.progress(0)
                
                for i, file in enumerate(uploaded_files):
                    chunks = load_and_chunk_pdf(file)
                    full_text_accumulator += f"\n--- FILE: {file.name} ---\n"
                    
                    for chunk in chunks:
                        full_text_accumulator += chunk + "\n"
                        # Analyze this chunk against the specific 2025 standard
                        ev = analyze_chunk(
                            client, 
                            chunk, 
                            ETEC_STANDARDS_2025[selected_key]['title'], 
                            ETEC_STANDARDS_2025[selected_key]['definition']
                        )
                        if ev and "NO_DATA" not in ev:
                            all_evidence.append(ev)
                    
                    prog.progress((i+1)/len(uploaded_files))
                
                # Store text for Chat
                st.session_state['full_text_context'] = full_text_accumulator
                
                if not all_evidence:
                    st.warning("No specific evidence found for this standard in the uploaded files.")
                else:
                    st.success(f"Found {len(all_evidence)} relevant data points. Generating Report...")
                    
                    report_data = generate_compliance_report(
                        client, 
                        all_evidence, 
                        ETEC_STANDARDS_2025[selected_key]['title'], 
                        ETEC_STANDARDS_2025[selected_key]['definition']
                    )
                    
                    # Display Report
                    st.markdown("---")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("✅ Evidence of Compliance")
                        for item in report_data.get('indicators', []):
                            st.write(f"- {item}")
                    with col2:
                        st.subheader("⚠️ Gaps / Pitfalls")
                        for item in report_data.get('pitfalls', []):
                            st.write(f"- {item}")
                    
                    st.subheader("🏆 Best Practice / Strength")
                    st.info(report_data.get('best_practice', 'N/A'))
                    
                    # PDF Download
                    pdf_bytes = generate_pdf_report(report_data, ETEC_STANDARDS_2025[selected_key]['title'])
                    st.download_button(
                        "Download Official Compliance Report (PDF)", 
                        pdf_bytes, 
                        f"NCAAA_Report_{selected_key}.pdf", 
                        "application/pdf"
                    )

            except Exception as e:
                st.error(f"Error: {e}")

# --- TAB 2: CHAT ---
with tab2:
    st.markdown("### 💬 Ask the AI Researcher")
    st.markdown("You can ask questions like: *'How does KKUCOD's graduate satisfaction compare to the national average?'* or *'Does the QMS manual mention the 2025 ETEC standards?'*")
    
    if not st.session_state['full_text_context']:
        st.warning("⚠️ Please upload documents in the Analyzer tab first.")
    else:
        for msg in st.session_state['chat_history']:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
        
        if prompt := st.chat_input("Type your question here..."):
            st.session_state['chat_history'].append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    resp = query_documents(get_client(), st.session_state['full_text_context'], prompt)
                    st.write(resp)
                    st.session_state['chat_history'].append({"role": "assistant", "content": resp})

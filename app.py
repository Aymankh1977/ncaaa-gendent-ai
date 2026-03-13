import streamlit as st
import json
from config import NCAAA_STANDARDS, NQF_DOMAINS, REQUIRED_DOCUMENTS
from ai_engine import get_client, analyze_evidence_for_standard, check_nqf_alignment, chat_with_ssr_expert
from pdf_processor import load_and_chunk_pdf
from report_generator import build_audit_pdf, build_nqf_pdf, build_ssr_pdf

st.set_page_config(page_title="Accreditation AI Platform", layout="wide", page_icon="🦷")

st.markdown("""
<style>
    h1 { color: #0e1117; }
    .stMetric {
        background-color: #ffffff;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #e0e0e0;
    }
    .grounding-notice {
        background: #e8f4e8;
        border-left: 4px solid #2e7d32;
        padding: 10px 14px;
        border-radius: 4px;
        font-size: 0.9em;
        margin-bottom: 10px;
    }
    .warning-notice {
        background: #fff3e0;
        border-left: 4px solid #e65100;
        padding: 10px 14px;
        border-radius: 4px;
        font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🦷 Dentistry Accreditation")
    st.markdown("---")
    st.header("📂 Evidence Locker")

    uploaded_files = st.file_uploader(
        "Upload School Documents", type=["pdf"], accept_multiple_files=True
    )

    if "processed_chunks" not in st.session_state:
        st.session_state.processed_chunks = {}
        st.session_state.all_chunks      = []
        st.session_state.full_text       = ""

    if uploaded_files and st.button("📖 Process Documents"):
        with st.spinner("Reading and indexing documents…"):
            all_chunks, processed = [], {}
            for file in uploaded_files:
                chunks = load_and_chunk_pdf(file)
                processed[file.name] = chunks
                all_chunks.extend(chunks)
            st.session_state.processed_chunks = processed
            st.session_state.all_chunks       = all_chunks
            st.session_state.full_text        = " ".join(all_chunks)
            total_pages = sum(len(v) for v in processed.values())
            st.success(f"✅ Indexed {len(processed)} doc(s) — {total_pages} pages total.")

    if st.session_state.processed_chunks:
        st.markdown("**Loaded documents:**")
        for fname, chunks in st.session_state.processed_chunks.items():
            st.markdown(f"- `{fname}` ({len(chunks)} pages)")

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("Accreditation Intelligence Platform")

st.markdown(
    '<div class="grounding-notice">🔒 <strong>Grounded Mode Active</strong> — '
    'All AI responses are restricted to content found in your uploaded documents. '
    'Anything not evidenced will be explicitly flagged as '
    '<em>NOT EVIDENCED IN DOCUMENTS</em>.</div>',
    unsafe_allow_html=True
)

tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Dashboard", "🧐 Standard Reviewer", "🔗 NQF Alignment", "📝 SSR Writer"]
)

# ── TAB 1 — DASHBOARD ──────────────────────────────────────────────────────────
with tab1:
    st.subheader("Document Readiness Dashboard")

    if not st.session_state.processed_chunks:
        st.info("📁 Upload and process documents using the sidebar to see your readiness status.")
    else:
        uploaded_names = list(st.session_state.processed_chunks.keys())
        found_docs   = [d for d in REQUIRED_DOCUMENTS
                        if any(d.lower().split()[0] in f.lower() for f in uploaded_names)]
        missing_docs = [d for d in REQUIRED_DOCUMENTS if d not in found_docs]

        col1, col2, col3 = st.columns(3)
        col1.metric("📄 Documents Uploaded",    len(uploaded_names))
        col2.metric("✅ Required Docs Matched",  f"{len(found_docs)}/{len(REQUIRED_DOCUMENTS)}")
        col3.metric("📈 Readiness Score",        f"{int(len(found_docs)/len(REQUIRED_DOCUMENTS)*100)}%")
        st.progress(len(found_docs) / len(REQUIRED_DOCUMENTS))

        if missing_docs:
            st.markdown("**⚠️ Missing Required Documents:**")
            for d in missing_docs:
                st.markdown(f"- {d}")

        st.markdown("---")
        st.markdown("**Pages indexed per document:**")
        for fname, chunks in st.session_state.processed_chunks.items():
            st.markdown(f"- `{fname}`: {len(chunks)} pages")

# ── TAB 2 — STANDARD REVIEWER ──────────────────────────────────────────────────
with tab2:
    st.subheader("AI Compliance Reviewer")
    st.markdown(
        "The reviewer scans **every page** of your documents for evidence relevant to the "
        "selected standard before generating its assessment."
    )

    selected_standard = st.selectbox("Select Standard", list(NCAAA_STANDARDS.keys()))

    if "audit_result" not in st.session_state:
        st.session_state.audit_result = None

    if st.button("▶️ Run Compliance Audit"):
        if not st.session_state.all_chunks:
            st.error("⚠️ No documents processed. Upload and process documents first.")
        else:
            client = get_client("audit")
            if not client:
                st.error("No API key found. Please set ANTHROPIC_API_KEY in your environment.")
            else:
                with st.spinner(f"Extracting evidence for '{selected_standard}'…"):
                    analysis = analyze_evidence_for_standard(
                        client,
                        selected_standard,
                        NCAAA_STANDARDS[selected_standard],
                        st.session_state.all_chunks
                    )
                    st.session_state.audit_result = analysis

    if st.session_state.audit_result:
        analysis = st.session_state.audit_result

        if "error" in analysis:
            st.error(f"❌ API Error: {analysis['error']}")
        else:
            c1, c2 = st.columns([1, 3])
            c1.metric("Compliance Rating", analysis.get("compliance_rating", "N/A"))
            c1.metric("Relevance",         analysis.get("relevance", "N/A"))
            c2.info(analysis.get("reviewer_comment", "No comment generated."))

            s1, s2 = st.columns(2)
            with s1:
                st.success("✅ Strengths")
                strengths = analysis.get("strengths", [])
                if strengths:
                    for s in strengths:
                        st.write(f"- {s}")
                else:
                    st.write("No strengths evidenced in uploaded documents.")
            with s2:
                st.error("⚠️ Gaps & Improvements")
                for gap in analysis.get("areas_for_improvement", []):
                    st.write(f"- {gap}")

            citations = analysis.get("citations", [])
            if citations:
                with st.expander("📎 Source Citations from Documents"):
                    for cite in citations:
                        st.markdown(f"> {cite}")

            # ── PDF download ──
            pdf_bytes = build_audit_pdf(selected_standard, analysis)
            st.download_button(
                label="📥 Download Audit Report (PDF)",
                data=pdf_bytes,
                file_name=f"audit_{selected_standard.replace(' ', '_')}.pdf",
                mime="application/pdf"
            )

# ── TAB 3 — NQF ALIGNMENT ──────────────────────────────────────────────────────
with tab3:
    st.subheader("NQF Level 6 Alignment Checker")
    st.markdown(
        "Paste your PLOs directly, or leave blank to use PLO content extracted "
        "from your uploaded documents."
    )

    plo_input = st.text_area(
        "Program Learning Outcomes (PLOs)",
        height=200,
        placeholder="Paste your PLOs here, one per line…\nLeave blank to use uploaded documents."
    )

    if "nqf_result" not in st.session_state:
        st.session_state.nqf_result = None

    if st.button("🔍 Check NQF Alignment"):
        plo_source = plo_input.strip() if plo_input.strip() else st.session_state.full_text

        if not plo_source:
            st.warning("⚠️ No PLO text and no documents uploaded. Please provide input.")
        else:
            client = get_client("nqf")
            if not client:
                st.error("No API key found. Please set ANTHROPIC_API_KEY in your environment.")
            else:
                source_label = "manually pasted PLOs" if plo_input.strip() else "uploaded documents"
                with st.spinner(f"Analysing alignment from {source_label}…"):
                    result = check_nqf_alignment(client, plo_source, NQF_DOMAINS)
                    st.session_state.nqf_result = result

    if st.session_state.nqf_result:
        st.markdown(st.session_state.nqf_result)

        # ── PDF download ──
        pdf_bytes = build_nqf_pdf(st.session_state.nqf_result)
        st.download_button(
            label="📥 Download NQF Report (PDF)",
            data=pdf_bytes,
            file_name="nqf_alignment_report.pdf",
            mime="application/pdf"
        )

# ── TAB 4 — SSR WRITER ─────────────────────────────────────────────────────────
with tab4:
    st.subheader("SSR Writing Assistant")
    st.markdown(
        "Ask the assistant to draft a section of your Self-Study Report. "
        "It will only write from evidence found in your uploaded documents."
    )

    if not st.session_state.all_chunks:
        st.markdown(
            '<div class="warning-notice">⚠️ No documents loaded. '
            "Upload and process documents in the sidebar before using the SSR Writer.</div>",
            unsafe_allow_html=True
        )

    if "ssr_chat_history" not in st.session_state:
        st.session_state.ssr_chat_history = []

    for msg in st.session_state.ssr_chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_query = st.chat_input(
        "Ask the SSR Assistant (e.g. 'Write the narrative for Standard 4 — Students')…"
    )

    if user_query:
        st.session_state.ssr_chat_history.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        if not st.session_state.all_chunks:
            reply = (
                "⚠️ No documents have been processed yet. "
                "Please upload and process your documents using the sidebar first."
            )
            with st.chat_message("assistant"):
                st.markdown(reply)
        else:
            client = get_client("ssr")
            if not client:
                reply = "❌ No API key configured. Please set ANTHROPIC_API_KEY in your environment."
                with st.chat_message("assistant"):
                    st.markdown(reply)
            else:
                with st.chat_message("assistant"):
                    with st.spinner("Searching documents and drafting response…"):
                        reply = chat_with_ssr_expert(
                            client,
                            st.session_state.all_chunks,
                            user_query
                        )
                        st.markdown(reply)

                        # ── PDF download ──
                        pdf_bytes = build_ssr_pdf(user_query, reply)
                        st.download_button(
                            label="📥 Download SSR Section (PDF)",
                            data=pdf_bytes,
                            file_name="ssr_section.pdf",
                            mime="application/pdf",
                            key=f"ssr_dl_{len(st.session_state.ssr_chat_history)}"
                        )

        st.session_state.ssr_chat_history.append({"role": "assistant", "content": reply})
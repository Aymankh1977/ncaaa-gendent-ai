import streamlit as st
import json
from datetime import datetime
from config import (RUBRIC_CRITERIA, NCAAA_STANDARDS_GROUPS, NQF_DOMAINS,
                    REQUIRED_DOCUMENTS, ALL_CRITERIA_KEYS,
                    PROGRAM_KPIS, KPI_REPORT_REQUIREMENTS,
                    DENTISTRY_SPECIALIZED_STANDARDS)
from ai_engine import get_client, analyze_evidence_for_standard, check_nqf_alignment, chat_with_ssr_expert
from document_processor import load_document
from report_generator import build_audit_pdf, build_nqf_pdf, build_ssr_pdf

st.set_page_config(page_title="DentEdTech — Accreditation AI", layout="wide", page_icon="🦷")

st.markdown("""
<style>
    h1 { color: #0e1117; }
    .stMetric { background-color:#fff; padding:10px; border-radius:5px; border:1px solid #e0e0e0; }
    .grounding-notice  { background:#e8f4e8; border-left:4px solid #2e7d32; padding:10px 14px; border-radius:4px; font-size:0.9em; margin-bottom:10px; }
    .warning-notice    { background:#fff3e0; border-left:4px solid #e65100; padding:10px 14px; border-radius:4px; font-size:0.9em; }
    .doc-select-notice { background:#e3f2fd; border-left:4px solid #1565c0; padding:10px 14px; border-radius:4px; font-size:0.9em; margin-bottom:12px; }
    .ssr-summary-box   { background:#f3e5f5; border-left:4px solid #6a1b9a; padding:10px 14px; border-radius:4px; font-size:0.9em; margin-bottom:10px; }
</style>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────
for key, default in [
    ("processed_chunks", {}), ("audit_result", None),
    ("nqf_result", None), ("ssr_chat_history", []),
    ("ssr_last_reply", None), ("ssr_last_query", ""),
    ("ssr_all_replies", []),   # NEW: stores all (query, reply) tuples for summary
]:
    if key not in st.session_state:
        st.session_state[key] = default


def chunks_for(selected_filenames):
    result = []
    for fname in selected_filenames:
        result.extend(st.session_state.processed_chunks.get(fname, []))
    return result


def doc_selector(key, label="📄 Select documents to analyse"):
    all_docs = list(st.session_state.processed_chunks.keys())
    if not all_docs:
        return []
    return st.multiselect(
        label, options=all_docs, default=all_docs, key=key,
        help="Deselect official reference/framework PDFs to keep them out of the evidence pool."
    )


def build_ssr_full_session_pdf(all_replies: list) -> bytes:
    """Builds a single PDF containing all SSR responses from this session."""
    combined_question = f"SSR Session Summary — {len(all_replies)} section(s) drafted"
    combined_text = ""
    for i, (q, r) in enumerate(all_replies, 1):
        combined_text += f"# Section {i}: {q}\n\n{r}\n\n---\n\n"
    return build_ssr_pdf(combined_question, combined_text)


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🦷 DentEdTech")
    st.markdown("**Accreditation Intelligence Platform**")
    st.markdown("---")
    st.header("📂 Evidence Locker")

    uploaded_files = st.file_uploader(
        "Upload School Documents",
        type=["pdf", "docx", "xlsx", "xls", "csv", "txt"],
        accept_multiple_files=True,
        help="Supported: PDF · Word · Excel · CSV · TXT"
    )
    st.caption("📎 Accepted: PDF · Word · Excel · CSV · TXT")

    if uploaded_files and st.button("📖 Process Documents"):
        with st.spinner("Reading and indexing documents…"):
            processed = {}
            for file in uploaded_files:
                chunks = load_document(file)
                processed[file.name] = chunks
            st.session_state.processed_chunks  = processed
            st.session_state.audit_result      = None
            st.session_state.nqf_result        = None
            st.session_state.ssr_chat_history  = []
            st.session_state.ssr_last_reply    = None
            st.session_state.ssr_all_replies   = []
            total_pages = sum(len(v) for v in processed.values())
            st.success(f"✅ Indexed {len(processed)} doc(s) — {total_pages} chunks total.")

    if st.session_state.processed_chunks:
        st.markdown("**Loaded documents:**")
        for fname, chunks in st.session_state.processed_chunks.items():
            st.markdown(f"- `{fname}` ({len(chunks)} chunks)")

    # SSR session summary in sidebar
    if st.session_state.get("ssr_all_replies"):
        st.markdown("---")
        st.markdown(f"**📝 SSR Sections Drafted: {len(st.session_state.ssr_all_replies)}**")
        for i, (q, _) in enumerate(st.session_state.ssr_all_replies, 1):
            st.markdown(f"  {i}. _{q[:50]}{'...' if len(q)>50 else ''}_")


# ── Header ─────────────────────────────────────────────────────────────────────
st.title("DentEdTech — Accreditation Intelligence Platform")
st.markdown(
    '<div class="grounding-notice">🔒 <strong>Grounded Mode Active</strong> — '
    'All AI responses are restricted to content found in your <strong>selected</strong> documents. '
    'Anything not evidenced will be flagged as <em>NOT EVIDENCED IN DOCUMENTS</em>.</div>',
    unsafe_allow_html=True
)

tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🧐 Standard Reviewer", "🔗 NQF Alignment", "📝 SSR Writer"])

# ── TAB 1 — DASHBOARD ──────────────────────────────────────────────────────────
with tab1:
    st.subheader("Document Readiness Dashboard")
    if not st.session_state.processed_chunks:
        st.info("📁 Upload and process documents using the sidebar.")
    else:
        uploaded_names = list(st.session_state.processed_chunks.keys())
        found_docs   = [d for d in REQUIRED_DOCUMENTS if any(d.lower().split()[0] in f.lower() for f in uploaded_names)]
        missing_docs = [d for d in REQUIRED_DOCUMENTS if d not in found_docs]

        col1, col2, col3 = st.columns(3)
        col1.metric("📄 Documents Uploaded",   len(uploaded_names))
        col2.metric("✅ Required Docs Matched", f"{len(found_docs)}/{len(REQUIRED_DOCUMENTS)}")
        col3.metric("📈 Readiness Score",       f"{int(len(found_docs)/len(REQUIRED_DOCUMENTS)*100)}%")
        st.progress(len(found_docs) / len(REQUIRED_DOCUMENTS))

        if missing_docs:
            st.markdown("**⚠️ Missing Required Documents:**")
            for d in missing_docs: st.markdown(f"- {d}")

        st.markdown("---")
        for fname, chunks in st.session_state.processed_chunks.items():
            st.markdown(f"- `{fname}`: {len(chunks)} chunks")

        # KPI reference
        with st.expander("📊 NCAAA Required KPIs (DP-101, 2024)"):
            st.markdown("The following 11 KPIs are the **minimum** required by NCAAA for all bachelor programs:")
            for code, kpi in PROGRAM_KPIS.items():
                st.markdown(f"**{code}** — {kpi['name']}")
                st.caption(kpi['measurement'])


# ── TAB 2 — STANDARD REVIEWER ──────────────────────────────────────────────────
with tab2:
    st.subheader("AI Compliance Reviewer")
    st.markdown(
        "Select documents, choose a criterion, then run the audit. "
        "Every component in the rubric will be scored 1–4 against your evidence."
    )

    if not st.session_state.processed_chunks:
        st.info("📁 Upload and process documents first.")
    else:
        st.markdown(
            '<div class="doc-select-notice">💡 Deselect official NCAAA/NQF reference files — '
            "analyse only your school's evidence documents.</div>",
            unsafe_allow_html=True
        )
        audit_docs = doc_selector("audit_doc_select")

        if not audit_docs:
            st.warning("⚠️ No documents selected.")
        else:
            with st.expander(f"📋 {len(audit_docs)} document(s) active"):
                for fname in audit_docs:
                    st.markdown(f"- `{fname}` ({len(st.session_state.processed_chunks.get(fname,[]))} chunks)")

            st.markdown("---")

            col_a, col_b = st.columns([1, 2])
            with col_a:
                selected_group = st.selectbox(
                    "Filter by Standard",
                    ["— All Criteria —"] + list(NCAAA_STANDARDS_GROUPS.keys())
                )
            with col_b:
                if selected_group == "— All Criteria —":
                    available_criteria = ALL_CRITERIA_KEYS
                else:
                    group_keys = NCAAA_STANDARDS_GROUPS[selected_group]
                    available_criteria = [k for k in ALL_CRITERIA_KEYS if k in group_keys]
                selected_criterion = st.selectbox("Select Criterion", available_criteria)

            if selected_criterion and selected_criterion in RUBRIC_CRITERIA:
                crit_info = RUBRIC_CRITERIA[selected_criterion]
                st.info(f"**{selected_criterion}** — {crit_info['description']}\n\n"
                        f"*{len(crit_info['components'])} components to be scored*")

            if st.button("▶️ Run Compliance Audit"):
                client = get_client("audit")
                if not client:
                    st.error("No API key found.")
                elif selected_criterion not in RUBRIC_CRITERIA:
                    st.error("Criterion not found in rubric.")
                else:
                    selected_chunks = chunks_for(audit_docs)
                    with st.spinner(f"Scoring all components of {selected_criterion}…"):
                        result = analyze_evidence_for_standard(
                            client, selected_criterion,
                            RUBRIC_CRITERIA[selected_criterion],
                            selected_chunks
                        )
                        st.session_state.audit_result = result

    if st.session_state.audit_result:
        analysis = st.session_state.audit_result
        if "error" in analysis:
            st.error(f"❌ {analysis['error']}")
        else:
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            c1.metric("Overall Score",    analysis.get("overall_score", "N/A"))
            c2.metric("Compliance Level", analysis.get("overall_level", "N/A"))
            c3.metric("Components Scored", len(analysis.get("components", [])))
            st.markdown(f"**Summary:** {analysis.get('summary', '')}")

            components = analysis.get("components", [])
            if components:
                st.markdown("### Component Scores")
                for comp in components:
                    score = comp.get("score", 1)
                    level = comp.get("level", "")
                    colour = {"4": "🟢", "3": "🟡", "2": "🟠", "1": "🔴"}.get(str(score), "⚪")
                    with st.expander(f"{colour} **{comp.get('component','')[:80]}** — {score}/4 {level}"):
                        st.markdown(f"**Finding:** {comp.get('finding','')}")
                        if comp.get('citation') and comp['citation'] != 'N/A':
                            st.markdown(f"**Evidence:** `{comp.get('citation','')}`")

            s1, s2 = st.columns(2)
            with s1:
                st.success("✅ Strengths")
                for s in analysis.get("strengths", []) or ["None evidenced."]:
                    st.write(f"- {s}")
            with s2:
                st.error("⚠️ Gaps")
                for g in analysis.get("gaps", []):
                    st.write(f"- {g}")

            if analysis.get("citations"):
                with st.expander("📎 Document Citations"):
                    for c in analysis["citations"]:
                        st.markdown(f"> {c}")

            pdf_bytes = build_audit_pdf(analysis.get("criterion", ""), analysis)
            st.download_button(
                "📥 Download Audit Report (PDF)", data=pdf_bytes,
                file_name=f"audit_{analysis.get('criterion','').replace(' ','_').replace(':','')}.pdf",
                mime="application/pdf"
            )


# ── TAB 3 — NQF ALIGNMENT ──────────────────────────────────────────────────────
with tab3:
    st.subheader("NQF Level 6 / Level 7 Alignment Checker")
    st.markdown(
        "Evaluates PLOs against **both NQF Level 6 and Level 7** descriptors from the official "
        "NQF-KSA 2023 document, then determines the correct level for your BDS program."
    )

    if not st.session_state.processed_chunks:
        st.info("📁 Upload and process documents, or paste PLOs directly.")
    else:
        st.markdown(
            '<div class="doc-select-notice">💡 Select only the Program Specification or '
            'Course Specification — not the official NQF reference document itself.</div>',
            unsafe_allow_html=True
        )
        nqf_docs = doc_selector("nqf_doc_select")
        if nqf_docs:
            with st.expander(f"📋 {len(nqf_docs)} document(s) selected"):
                for fname in nqf_docs:
                    st.markdown(f"- `{fname}` ({len(st.session_state.processed_chunks.get(fname,[]))} chunks)")

    plo_input = st.text_area(
        "Program Learning Outcomes (PLOs) — optional manual paste",
        height=180, placeholder="Paste PLOs here to override document selection…"
    )

    if st.button("🔍 Check NQF Alignment"):
        if plo_input.strip():
            plo_source, source_label = plo_input.strip(), "manually pasted PLOs"
        elif st.session_state.processed_chunks:
            selected = st.session_state.get("nqf_doc_select", list(st.session_state.processed_chunks.keys()))
            if not selected:
                st.warning("⚠️ No documents selected.")
                st.stop()
            plo_source   = " ".join(chunks_for(selected))
            source_label = f"{len(selected)} selected document(s)"
        else:
            st.warning("⚠️ No input provided.")
            st.stop()

        client = get_client("nqf")
        if not client:
            st.error("No API key found.")
        else:
            with st.spinner(f"Analysing from {source_label}…"):
                result = check_nqf_alignment(client, plo_source, NQF_DOMAINS)
                st.session_state.nqf_result = result

    if st.session_state.nqf_result:
        st.markdown("---")
        st.markdown(st.session_state.nqf_result)
        pdf_bytes = build_nqf_pdf(st.session_state.nqf_result)
        st.download_button("📥 Download NQF Report (PDF)", data=pdf_bytes,
                           file_name="nqf_alignment_report.pdf", mime="application/pdf")


# ── TAB 4 — SSR WRITER ─────────────────────────────────────────────────────────
with tab4:
    st.subheader("SSR Writing Assistant")
    st.markdown(
        "Select the documents that contain your evidence, then ask the assistant to draft "
        "a section. Only the selected documents will be used as source material."
    )

    # ── Document selection ──
    if not st.session_state.processed_chunks:
        st.markdown('<div class="warning-notice">⚠️ Upload and process documents first.</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="doc-select-notice">💡 Select only your school\'s evidence documents — '
            'exclude NCAAA/NQF reference files.</div>', unsafe_allow_html=True
        )
        ssr_docs = doc_selector("ssr_doc_select")
        if ssr_docs:
            with st.expander(f"📋 {len(ssr_docs)} document(s) selected for SSR drafting"):
                for fname in ssr_docs:
                    st.markdown(f"- `{fname}` ({len(st.session_state.processed_chunks.get(fname,[]))} chunks)")
        else:
            st.warning("⚠️ No documents selected.")

    st.markdown("---")

    # ── Session summary table ──
    all_replies = st.session_state.get("ssr_all_replies", [])
    if all_replies:
        st.markdown(
            '<div class="ssr-summary-box">📋 <strong>Session Summary</strong> — '
            f'{len(all_replies)} SSR section(s) drafted in this session.</div>',
            unsafe_allow_html=True
        )
        # Summary table
        summary_data = []
        for i, (q, r) in enumerate(all_replies, 1):
            word_count = len(r.split())
            summary_data.append(f"| {i} | {q[:70]}{'...' if len(q)>70 else ''} | ~{word_count} words |")

        st.markdown("| # | Request | Length |")
        st.markdown("|---|---|---|")
        for row in summary_data:
            st.markdown(row)

        st.markdown("")
        col_dl1, col_dl2 = st.columns(2)

        with col_dl1:
            # Download LAST response
            if st.session_state.get("ssr_last_reply"):
                pdf_bytes = build_ssr_pdf(
                    st.session_state.get("ssr_last_query", "SSR Section"),
                    st.session_state["ssr_last_reply"]
                )
                st.download_button(
                    "📥 Download Last Response (PDF)",
                    data=pdf_bytes,
                    file_name="ssr_last_section.pdf",
                    mime="application/pdf",
                    key="ssr_dl_last"
                )

        with col_dl2:
            # Download ALL responses as one PDF
            if len(all_replies) > 1:
                full_pdf_bytes = build_ssr_full_session_pdf(all_replies)
                st.download_button(
                    f"📥 Download All {len(all_replies)} Sections (PDF)",
                    data=full_pdf_bytes,
                    file_name=f"ssr_full_session_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf",
                    key="ssr_dl_all"
                )

        if st.button("🗑️ Clear Session History"):
            st.session_state.ssr_chat_history = []
            st.session_state.ssr_all_replies  = []
            st.session_state.ssr_last_reply   = None
            st.session_state.ssr_last_query   = ""
            st.rerun()

        st.markdown("---")

    # ── Chat history ──
    for msg in st.session_state.ssr_chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ── Chat input ──
    user_query = st.chat_input(
        "Ask the SSR Assistant (e.g. 'Write Standard 2-3-3 narrative using my course specification')…"
    )

    if user_query:
        st.session_state.ssr_chat_history.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        ssr_docs_now = st.session_state.get("ssr_doc_select", [])

        if not st.session_state.processed_chunks:
            reply = "⚠️ No documents processed yet. Upload documents first."
            with st.chat_message("assistant"): st.markdown(reply)
        elif not ssr_docs_now:
            reply = "⚠️ No documents selected. Tick at least one document above."
            with st.chat_message("assistant"): st.markdown(reply)
        else:
            client = get_client("ssr")
            if not client:
                reply = "❌ No API key configured."
                with st.chat_message("assistant"): st.markdown(reply)
            else:
                selected_chunks = chunks_for(ssr_docs_now)
                with st.spinner(f"Searching {len(ssr_docs_now)} document(s) and drafting…"):
                    reply = chat_with_ssr_expert(client, selected_chunks, user_query)
                with st.chat_message("assistant"):
                    st.markdown(reply)

                # Store in session state
                st.session_state["ssr_last_reply"] = reply
                st.session_state["ssr_last_query"] = user_query
                # Add to all_replies for summary and full-session download
                st.session_state["ssr_all_replies"].append((user_query, reply))

                # ── Per-response download rendered BELOW the message ──
                # Uses a unique key based on total count to avoid duplicate widget keys
                pdf_bytes = build_ssr_pdf(user_query, reply)
                st.download_button(
                    f"📥 Download this section (PDF)",
                    data=pdf_bytes,
                    file_name=f"ssr_section_{len(st.session_state['ssr_all_replies'])}.pdf",
                    mime="application/pdf",
                    key=f"ssr_dl_response_{len(st.session_state['ssr_all_replies'])}"
                )

        st.session_state.ssr_chat_history.append({"role": "assistant", "content": reply})
import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from core.loader import DuckDBDataLoader
from core.llm import LLMClient
from core.profiler import DataProfiler
from core.engine import DataChatEngine

# Page Configuration & Modern Styling
st.set_page_config(
    page_title="DataChat - AI Data Q&A",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Design & Dark UI Aesthetics
st.markdown("""
<style>
    /* Global Styles */
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    
    /* Header Gradient */
    .hero-header {
        background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.2rem;
        margin-bottom: 0.2rem;
    }
    .hero-subtitle {
        color: #9CA3AF;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }

    /* Pill Buttons */
    .stButton>button {
        border-radius: 20px;
        border: 1px solid #4F46E5;
        background: rgba(79, 70, 229, 0.1);
        color: #E0E7FF;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        background: #4F46E5;
        color: white;
        border-color: #4F46E5;
        transform: translateY(-1px);
    }
</style>
""", unsafe_allow_html=True)

load_dotenv()

# Initialize Session States
if "loader" not in st.session_state:
    st.session_state.loader = DuckDBDataLoader()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "suggested_questions" not in st.session_state:
    st.session_state.suggested_questions = []

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

# Initialize LLM & Engine
llm_client = LLMClient()
engine = DataChatEngine(st.session_state.loader, llm_client)

# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.markdown("<h2 style='color:#6366F1;'>⚡ DataChat Studio</h2>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 0.85rem; color: #9CA3AF;'>Darwinbox FDE AI Data Q&A Engine</p>", unsafe_allow_html=True)
    st.divider()

    # Data Ingestion Controls
    st.subheader("📁 Data Ingestion")
    
    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        if st.button("⚡ Load HR Demo", help="Preload sample employees, departments, and compensation datasets"):
            sample_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_data")
            for fname in ["employees.csv", "departments.csv", "compensation.csv"]:
                fpath = os.path.join(sample_dir, fname)
                if os.path.exists(fpath):
                    st.session_state.loader.load_file(fpath)
            st.success("Loaded 3 HR Datasets!")
            st.session_state.suggested_questions = []
            st.rerun()

    with col_btn2:
        if st.button("🗑️ Reset All"):
            st.session_state.loader = DuckDBDataLoader()
            st.session_state.messages = []
            st.session_state.suggested_questions = []
            st.rerun()

    uploaded_files = st.file_uploader(
        "Upload CSV or Excel files",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=True
    )

    if uploaded_files:
        for file in uploaded_files:
            st.session_state.loader.load_file(file)
        st.success(f"Loaded {len(uploaded_files)} file(s)!")
        st.session_state.suggested_questions = []

    st.divider()

    # Active Tables & Schema Inspector
    loaded_summary = st.session_state.loader.get_schema_summary()
    if loaded_summary:
        st.subheader("📊 Active Datasets")
        for table_name, details in loaded_summary.items():
            with st.expander(f"📋 `{table_name}` ({details['row_count']} rows)"):
                st.caption(f"Source: {details['original_filename']}")
                st.write("**Columns:**")
                for c_name, c_type in details["columns"].items():
                    st.text(f"  • {c_name} ({c_type})")

        # Data Quality Warnings
        profiler = DataProfiler(st.session_state.loader, llm_client)
        warnings = profiler.generate_quality_warnings()
        if warnings:
            with st.expander("⚠️ Data Quality Alerts"):
                for w in warnings:
                    st.warning(w["message"])
    else:
        st.info("No datasets loaded yet. Click 'Load HR Demo' or upload CSV/Excel files to begin.")


# --- MAIN CHAT CANVAS ---
st.markdown("<div class='hero-header'>Build & Ask Anything Across Your Data</div>", unsafe_allow_html=True)
st.markdown("<div class='hero-subtitle'>Ask analytical questions in plain English. DuckDB executes exact SQL, and OpenRouter AI provides insights and charts.</div>", unsafe_allow_html=True)

# Generate Suggested Questions if datasets present
if loaded_summary and not st.session_state.suggested_questions:
    profiler = DataProfiler(st.session_state.loader, llm_client)
    with st.spinner("Analyzing schema to generate starter questions..."):
        st.session_state.suggested_questions = profiler.generate_suggested_questions()

# Display Clickable Suggested Question Pills
if st.session_state.suggested_questions:
    st.markdown("**💡 Suggested Questions (Click to Ask):**")
    pill_cols = st.columns(len(st.session_state.suggested_questions))
    for idx, q_text in enumerate(st.session_state.suggested_questions):
        with pill_cols[idx]:
            if st.button(f"🔍 {q_text}", key=f"pill_{idx}"):
                st.session_state.pending_prompt = q_text
                st.rerun()

st.divider()

# --- RENDER MESSAGES ---
for msg_idx, msg in enumerate(st.session_state.messages):
    avatar_icon = "👤" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=avatar_icon):
        st.write(msg["content"])
        
        # Display SQL
        if msg.get("sql"):
            with st.expander("🔍 View Executed SQL Query"):
                st.code(msg["sql"], language="sql")
        
        # Display Result Table
        if msg.get("dataframe") is not None and not msg["dataframe"].empty:
            st.dataframe(msg["dataframe"], width="stretch")
            csv_bytes = msg["dataframe"].to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download CSV Result",
                data=csv_bytes,
                file_name="query_result.csv",
                mime="text/csv",
                key=f"dl_msg_{msg_idx}"
            )
        
        # Display Chart
        if msg.get("chart") is not None:
            st.plotly_chart(msg["chart"])

        # Ambiguity Options
        if msg.get("ambiguity_options"):
            st.write("**Select clarifying logic to execute:**")
            for opt_idx, opt in enumerate(msg["ambiguity_options"]):
                if st.button(f"👉 {opt}", key=f"amb_opt_{msg_idx}_{opt_idx}"):
                    st.session_state.pending_prompt = f"{msg.get('original_question', '')} ({opt})"
                    st.rerun()


# --- INPUT HANDLER ---
chat_user_input = st.chat_input("Ask an analytical question across your uploaded files...")

prompt_to_execute = None
if st.session_state.pending_prompt:
    prompt_to_execute = st.session_state.pending_prompt
    st.session_state.pending_prompt = None
elif chat_user_input:
    prompt_to_execute = chat_user_input

if prompt_to_execute:
    # 1. Store User Question
    st.session_state.messages.append({"role": "user", "content": prompt_to_execute})

    # 2. Process via Engine
    with st.spinner("Analyzing..."):
        res = engine.process_query(
            question=prompt_to_execute,
            chat_history=st.session_state.messages
        )

    # 3. Store Engine Output
    if res.get("status") == "ambiguous":
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"🤔 **Question Ambiguity Detected:** {res.get('explanation')}",
            "original_question": prompt_to_execute,
            "ambiguity_options": res.get("options", [])
        })

    elif res.get("status") == "error":
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"❌ {res.get('message')}"
        })

    elif res.get("status") == "success":
        st.session_state.messages.append({
            "role": "assistant",
            "content": res.get("answer", "Query executed successfully."),
            "sql": res.get("sql", ""),
            "dataframe": res.get("dataframe"),
            "chart": res.get("chart")
        })

    st.rerun()

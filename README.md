# DataChat: AI-Powered Data Q&A Web App

> **Darwinbox Forward Deployed Engineer (FDE) Take-Home Assignment Solution**  
> A full-featured analytical web application enabling plain-English Q&A across multiple CSV/Excel files using in-memory DuckDB Text-to-SQL, OpenRouter open-source LLMs (`Llama 3.3 70B`), automated data quality profiling, ambiguity resolution, auto-visualization, and an evaluation benchmark.

---

## 🌟 Executive Summary & Acceptance Criteria Mapping

| Darwinbox Acceptance Criteria | How DataChat Fulfills It | Architectural Module |
| :--- | :--- | :--- |
| **1. Multi-file upload** | Drag-and-drop multiple `.csv` and `.xlsx` files simultaneously, registered instantly into an in-memory DuckDB instance. Includes a 1-click **Load HR Demo** button. | [`core/loader.py`](core/loader.py) |
| **2. Cross-file analysis** | Executes complex relational operations (`JOIN`, `GROUP BY`, aggregations, window functions, conditional filters) across multiple uploaded files. | [`core/engine.py`](core/engine.py) |
| **3. Visual insights** | Automatically recommends and renders interactive **Plotly** charts (Bar, Line, Pie, Scatter) based on result cardinality and data types. | [`core/charts.py`](core/charts.py) |
| **4. Delta solutioning** *(Value-Add)* | • **Ambiguity Detection**: Asks clarifying questions instead of guessing.<br>• **Suggested Questions**: Auto-generates clickable prompt pills upon upload.<br>• **Multi-turn Context**: Enables follow-up queries (*"now break that down by month"*).<br>• **SQL Guardrail**: Enforces read-only SELECT safety.<br>• **Eval Benchmark**: Automated test suite runner. | [`core/profiler.py`](core/profiler.py), [`core/sql_guard.py`](core/sql_guard.py), [`eval/`](eval/) |

---

## 🧠 Technical Architecture & Key Decisions

```text
datachat/
├── app.py              # Streamlit Web App (Chat UI, Sidebar, Pills, Interactive Tables & Plotly Charts)
├── core/
│   ├── loader.py       # Multi-file Ingestion & Schema Normalization -> DuckDB Tables
│   ├── profiler.py     # Data Quality Warnings & Auto-Suggested Starter Questions
│   ├── llm.py          # OpenRouter API Client (Llama 3.3 70B, DeepSeek R1 70B, Qwen 2.5 Coder)
│   ├── sql_guard.py    # SQL Security Validator (Read-only SELECT enforcement & sanitization)
│   ├── engine.py       # Core Orchestrator (Ambiguity Check + Multi-Turn Memory + SQL Exec + NL Summary)
│   └── charts.py       # Auto Chart Recommendation & Plotly Figure Builder
├── sample_data/        # Benchmark HR Datasets (employees.csv, departments.csv, compensation.csv)
├── eval/               # Evaluation Benchmark (10 Golden Questions + Accuracy Runner)
│   ├── golden_questions.json
│   └── run_eval.py
├── requirements.txt    # Python dependencies
└── README.md           # Setup, architecture decisions & FDE write-up
```

### Why Text-to-SQL (DuckDB) over Vector RAG?

1. **Exact Mathematical Aggregations**: Vector RAG embeds text chunks and retrieves top similarity snippets, which hallucinates or fails when calculating exact totals (`SUM`, `AVG`, `COUNT`) across thousands of rows. Text-to-SQL executes exact relational algebra across 100% of dataset records.
2. **Cross-Table JOINs**: Vector similarity cannot join `employees.csv` to `departments.csv` on `dept_id`. DuckDB natively handles complex relational JOINs in under 10ms.
3. **Enterprise Auditability**: Enterprise HR analytics require auditable results. The generated SQL query is fully transparent and inspectable.

---

## 🚀 Quick Start & Run Instructions

### 1. Prerequisites & Virtual Environment Setup

Ensure you have Python 3.8+ installed (Python 3.12 recommended):

```powershell
# Navigate to project directory
cd datachat

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows PowerShell:
.\venv\Scripts\activate

# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and add your **OpenRouter API Key**:

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
DEFAULT_MODEL=meta-llama/llama-3.3-70b-instruct
```

### 3. Run Benchmark Evaluation Suite

To execute the golden questions test suite against the sample HR datasets:

```powershell
python -m eval.run_eval
```

### 4. Launch the Web Application

Launch the Streamlit interactive dashboard:

```powershell
streamlit run app.py
```

The web app will open automatically in your browser at `http://localhost:8501`. Click **⚡ Load HR Demo** in the sidebar to test immediately with pre-packaged datasets!

---

## 📄 1-Page Approach & Write-Up (FDE Problem Solving & Next Steps)

### Approach & Scoping

To build a production-grade data assistant within time constraints, I scoped the app around three core principles:

1. **Determinism First**: Leveraging DuckDB as an in-memory analytical engine eliminates database infrastructure complexity while guaranteeing mathematical precision.
2. **Frictionless Onboarding**: Auto-generating schema-aware starter questions eliminates "blank canvas syndrome" for users upon dataset upload.
3. **Guardrails & Enterprise Safety**: Implementing AST/Regex SQL security validation ensures LLM hallucinations can never execute destructive state mutations (`DROP`, `DELETE`).

### Key Trade-Offs & Decisions

- **OpenRouter API vs. Local Ollama**: Used OpenRouter to access state-of-the-art open-source LLMs (`Llama 3.3 70B`) via a unified OpenAI-compatible SDK without requiring GPU hardware.
- **Plotly vs. Static Matplotlib**: Selected Plotly for interactive zoom, hover tooltips, and seamless Streamlit integration.

### Future Roadmap (What I'd Build Next for Enterprise Deployment)

1. **Dynamic Schema Relationship Inference**: Use fuzzy column matching and LLM reasoning to auto-detect foreign key join paths when dataset schemas lack explicit naming matches.
2. **Role-Based Data Access (RBAC) & Cell Masking**: In HR systems like Darwinbox, sensitive columns (e.g. `salary`, `performance_rating`) require row-level and column-level security filters before executing SQL.
3. **Cached Aggregation Views**: Materialize frequent SQL query patterns into DuckDB views for instant sub-millisecond dashboard rendering.

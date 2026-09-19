from typing import List, Dict, Any
from .loader import DuckDBDataLoader
from .llm import LLMClient

class DataProfiler:
    """
    Analyzes loaded datasets for data quality insights and generates schema-aware suggested questions.
    """
    def __init__(self, loader: DuckDBDataLoader, llm: LLMClient = None):
        self.loader = loader
        self.llm = llm

    def generate_quality_warnings(self) -> List[Dict[str, str]]:
        """
        Scans DuckDB tables for null counts, row counts, and data quality alerts.
        """
        warnings = []
        summary = self.loader.get_schema_summary()

        for table_name, details in summary.items():
            row_count = details["row_count"]
            if row_count == 0:
                warnings.append({
                    "severity": "high",
                    "table": table_name,
                    "message": f"Table `{table_name}` is empty (0 rows)."
                })
                continue

            # Check null counts per column
            for col_name, dtype in details["columns"].items():
                null_res = self.loader.con.execute(
                    f"SELECT COUNT(*) - COUNT({col_name}) AS null_count FROM {table_name}"
                ).fetchone()
                null_count = null_res[0] if null_res else 0

                if null_count > 0:
                    pct = round((null_count / row_count) * 100, 1)
                    warnings.append({
                        "severity": "medium" if pct > 10 else "low",
                        "table": table_name,
                        "message": f"Column `{col_name}` in `{table_name}` has {null_count} missing values ({pct}%)."
                    })

        return warnings

    def generate_suggested_questions(self) -> List[str]:
        """
        Calls LLM to inspect database schema and suggest 4 starter analytical questions.
        """
        if not self.llm or not self.llm.is_configured():
            # Fallback static questions if LLM key is not provided yet
            tables = list(self.loader.loaded_tables.keys())
            if "employees" in tables and "departments" in tables:
                return [
                    "What is the total and average salary per department?",
                    "Which department has the highest budget for 2025?",
                    "Show the top 3 highest-rated employees and their department names.",
                    "What is the distribution of employees across locations?"
                ]
            return [
                "Summarize the total row counts for all uploaded files.",
                "Show the top 5 records from each table.",
                "What are the column summary statistics for numeric fields?",
                "Are there any missing values across the tables?"
            ]

        schema_prompt = self.loader.get_schema_prompt_text()
        system_prompt = (
            "You are an expert Data Analyst & Business Intelligence Lead at an HR Tech company.\n"
            "Given the user's uploaded database schema, generate exactly 4 clear, high-value analytical questions\n"
            "that a business leader would ask. Include at least 1 cross-table query if multiple tables are present.\n"
            "Respond in JSON format with a key 'questions' containing a list of 4 string questions."
        )
        user_prompt = f"Dataset Schemas:\n{schema_prompt}"

        try:
            res = self.llm.generate_json(system_prompt, user_prompt)
            questions = res.get("questions", [])
            if isinstance(questions, list) and len(questions) > 0:
                return questions[:4]
        except Exception:
            pass

        # Fallback if LLM JSON parsing fails
        return [
            "What is the average salary by department?",
            "Which department has the highest performance rating?",
            "Compare employee compensation and bonus breakdown.",
            "Show headcount distribution across office locations."
        ]

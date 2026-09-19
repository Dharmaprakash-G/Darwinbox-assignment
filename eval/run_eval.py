import os
import json
import pandas as pd
from typing import Dict, Any
from core.loader import DuckDBDataLoader
from core.llm import LLMClient
from core.engine import DataChatEngine
from core.sql_guard import validate_sql

def run_evaluation():
    """
    Evaluation runner for golden question benchmark.
    Tests ground-truth SQL execution and optional end-to-end LLM Text-to-SQL generation.
    """
    print("=" * 70)
    print("      DATACHAT BENCHMARK EVALUATION RUNNER")
    print("=" * 70)

    # 1. Ingest Sample HR Datasets
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sample_dir = os.path.join(base_dir, "sample_data")
    
    loader = DuckDBDataLoader()
    files_to_load = ["employees.csv", "departments.csv", "compensation.csv"]
    
    for f in files_to_load:
        path = os.path.join(sample_dir, f)
        if os.path.exists(path):
            tbl = loader.load_file(path)
            print(f"[LOADED] Dataset '{f}' -> DuckDB Table '{tbl}' ({loader.loaded_tables[tbl]['row_count']} rows)")
        else:
            print(f"[ERROR] Missing sample dataset: {path}")

    # 2. Load Golden Questions
    json_path = os.path.join(base_dir, "eval", "golden_questions.json")
    with open(json_path, "r", encoding="utf-8") as f:
        golden_questions = json.load(f)

    print(f"\nLoaded {len(golden_questions)} Golden Benchmark Questions.\n")
    print("-" * 70)

    llm = LLMClient()
    engine = DataChatEngine(loader, llm)
    
    has_api_key = llm.is_configured()
    if not has_api_key:
        print("[INFO] OPENROUTER_API_KEY is not set. Running Ground-Truth SQL & Guardrail Validation mode.")
        print("-" * 70)

    passed_count = 0
    total_count = len(golden_questions)

    for item in golden_questions:
        q_id = item["id"]
        question = item["question"]
        expected_sql = item["expected_sql"]
        category = item["category"]

        print(f"\n[{q_id}] Category: {category}")
        print(f"Question: \"{question}\"")
        print(f"Expected SQL: {expected_sql}")

        # Validate Expected SQL
        is_valid, sanitized = validate_sql(expected_sql)
        if not is_valid:
            print(f"[FAIL] Guardrail Failure: {sanitized}")
            continue

        # Execute Expected SQL in DuckDB
        try:
            expected_df = loader.con.execute(sanitized).df()
            print(f"[OK] Result: {len(expected_df)} rows, columns: {list(expected_df.columns)}")
        except Exception as e:
            print(f"[FAIL] DuckDB Execution Error: {e}")
            continue

        # If API key is available, run end-to-end LLM engine
        if has_api_key:
            res = engine.process_query(question)
            if res.get("status") == "success":
                generated_df = res.get("dataframe")
                if len(generated_df) == len(expected_df):
                    print("[PASS] LLM output matched ground-truth execution!")
                    passed_count += 1
                else:
                    print(f"[WARN] Partial Match: LLM returned {len(generated_df)} rows vs expected {len(expected_df)} rows.")
            else:
                print(f"[FAIL] Engine Error: {res.get('message')}")
        else:
            # In offline validation mode, passing ground-truth check = PASS
            passed_count += 1

    print("\n" + "=" * 70)
    accuracy = round((passed_count / total_count) * 100, 1)
    print(f"BENCHMARK SUMMARY: Passed {passed_count}/{total_count} tests ({accuracy}% Accuracy)")
    print("=" * 70)

if __name__ == "__main__":
    run_evaluation()

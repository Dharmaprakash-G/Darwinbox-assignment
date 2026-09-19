import pandas as pd
from typing import Dict, Any, List, Optional
from .loader import DuckDBDataLoader
from .llm import LLMClient
from .sql_guard import validate_sql
from .charts import recommend_and_build_chart

class DataChatEngine:
    """
    Core orchestrator that combines Intent Classification, Ambiguity Detection, 
    Multi-turn Context, Text-to-SQL Generation, DuckDB Execution, and Natural Language Explanation.
    """
    def __init__(self, loader: DuckDBDataLoader, llm: LLMClient):
        self.loader = loader
        self.llm = llm

    def classify_intent(self, question: str) -> str:
        """
        Classifies user input as either 'DATA_QUERY' (requires SQL) or 'CONVERSATIONAL' (meta chat/history/greetings).
        """
        import re
        q_lower = question.lower().strip()
        
        # Exact word boundary matching for conversational/meta phrases
        conversational_patterns = [
            r"\bwhat did i ask\b", r"\bwhat question\b", r"\bquestions i asked\b", r"\bquestion s i asked\b", 
            r"\basked so far\b", r"\bprevious question\b", r"\bchat history\b", r"\bsummarize what we asked\b",
            r"\bsummarize user questions\b", r"\bwhat were the questions\b", r"\bwho are you\b", 
            r"\bwhat can you do\b", r"\bhello\b", r"\bhi\b", r"\bhey\b"
        ]
        if any(re.search(pat, q_lower) for pat in conversational_patterns):
            return "CONVERSATIONAL"

        # Word boundary matching for data analytical queries
        data_keywords = [
            r"\bselect\b", r"\bwhere\b", r"\bcount\b", r"\baverage\b", r"\bavg\b", r"\bsum\b", r"\btotal\b", r"\bdepartment\b", 
            r"\bsalary\b", r"\bemployee\b", r"\bbudget\b", r"\bbonus\b", r"\brating\b", r"\bhighest\b", r"\blowest\b", 
            r"\btop\b", r"\blist\b", r"\bshow\b", r"\bhow many\b", r"\bcompare\b", r"\bdistribution\b", r"\btenure\b"
        ]
        if any(re.search(pat, q_lower) for pat in data_keywords):
            return "DATA_QUERY"

        # Fallback LLM Classification for ambiguous inputs
        if self.llm.is_configured():
            system_prompt = (
                "You are an intent classifier.\n"
                "Classify user input into one of two categories:\n"
                "1. DATA_QUERY: Asking for database numbers, columns, employee metrics, statistics, tables, or filters.\n"
                "2. CONVERSATIONAL: Greetings, asking about previous chat questions, asking what questions were asked, or meta chat topics.\n"
                "Respond ONLY with one word: DATA_QUERY or CONVERSATIONAL."
            )
            try:
                res = self.llm.generate_completion(system_prompt, f"User Input: {question}", temperature=0.0)
                if "CONVERSATIONAL" in res.upper():
                    return "CONVERSATIONAL"
            except Exception:
                pass

        return "DATA_QUERY"

    def check_ambiguity(self, question: str, chat_history: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Evaluates whether a SQL data query is ambiguous given the schema.
        If ambiguous, returns clarification options. Otherwise returns None.
        """
        if not self.llm.is_configured():
            return None

        # Bypass ambiguity check if the question has already been clarified by option selection
        q_lower = question.lower()
        if any(marker in q_lower for marker in ["(clarification:", "(option ", "(selected:", "instruction:"]):
            print(f"[ENGINE AMBIGUITY BYPASS] Question contains clarification selection. Skipping ambiguity check.")
            return None

        schema_text = self.loader.get_schema_prompt_text()
        system_prompt = (
            "You are a Data Quality & Intent Disambiguation Lead.\n"
            "Analyze if the user's DATA question is too vague or could mean multiple distinct SQL metric calculations given the schema.\n"
            "For example: 'who is performing best' could mean highest performance rating OR highest sales target achievement.\n"
            "If the question IS ambiguous, respond with JSON:\n"
            "{\n"
            '  "is_ambiguous": true,\n'
            '  "explanation": "Brief explanation of why it is ambiguous",\n'
            '  "options": ["Option 1: Filter by X", "Option 2: Aggregate by Y"]\n'
            "}\n"
            "If the question IS CLEAR and unambiguous, respond with JSON:\n"
            '{"is_ambiguous": false}\n'
            "DO NOT flag general filters or top-N queries as ambiguous."
        )
        
        user_prompt = f"Schema:\n{schema_text}\n\nUser Question: {question}"

        try:
            res = self.llm.generate_json(system_prompt, user_prompt)
            if res.get("is_ambiguous", False) is True:
                options = res.get("options", [])
                if options and isinstance(options, list):
                    print(f"[ENGINE AMBIGUITY] Question '{question}' flagged ambiguous: {res.get('explanation')}")
                    return {
                        "status": "ambiguous",
                        "explanation": res.get("explanation", "This question can be answered in multiple ways."),
                        "options": options[:3]
                    }
        except Exception as e:
            print(f"[ENGINE AMBIGUITY WARNING] Ambiguity check failed or skipped: {e}")

        return None

    def process_query(self, question: str, chat_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes the main pipeline with Intent Classification, Ambiguity Resolution, and Text-to-SQL.
        """
        print("\n" + "="*60)
        print(f"[ENGINE INPUT] Question: '{question}'")
        print("="*60)

        chat_history = chat_history or []

        # 1. Classify Intent (DATA_QUERY vs CONVERSATIONAL)
        intent = self.classify_intent(question)
        print(f"[ENGINE INTENT] Classified as: {intent}")

        if intent == "CONVERSATIONAL":
            print(f"[ENGINE META CHAT] Handling conversational/meta question: '{question}'")
            user_questions = [msg.get("content") for msg in chat_history if msg.get("role") == "user"]
            prev_questions = user_questions[:-1] if len(user_questions) > 1 else []
            history_text = "\n".join([f"{idx+1}. {q}" for idx, q in enumerate(prev_questions)]) if prev_questions else "No previous questions asked in this session yet."
            
            system_prompt = (
                "You are DataChat, an AI-Powered Data Analytics & Business Intelligence Assistant.\n"
                "If the user asks about your capabilities or what you can do, explain your specialized tabular data analytics features:\n"
                "1. Multi-File Dataset Analysis: Ingesting and querying across multiple CSV & Excel datasets.\n"
                "2. Text-to-SQL Relational Queries: Calculating exact totals, averages, counts, cross-table JOINs, and conditional filters in DuckDB.\n"
                "3. Auto-Visualization: Automatically building interactive Plotly charts (Bar, Line, Pie, Scatter).\n"
                "4. Ambiguity Resolution: Asking clarifying questions when business metrics are vague.\n"
                "5. Data Profiling: Identifying missing values, data types, and quality alerts.\n"
                "Do NOT list generic LLM capabilities like language translation, poem writing, or general trivia."
            )
            user_prompt = f"Previous User Questions in Chat Session:\n{history_text}\n\nCurrent User Question: {question}"
            
            try:
                nl_ans = self.llm.generate_completion(system_prompt, user_prompt, temperature=0.2)
            except Exception:
                nl_ans = (
                    "I am **DataChat**, your AI Data Analytics Assistant!\n\n"
                    "Here is what I can help you with:\n"
                    "• **Multi-File Dataset Ingestion**: Ingest and query multiple CSV/Excel files.\n"
                    "• **Exact Text-to-SQL Analytics**: Compute exact averages, totals, counts, and cross-table `JOIN`s in DuckDB.\n"
                    "• **Interactive Visualizations**: Auto-render Plotly bar, line, pie, and scatter charts.\n"
                    "• **Ambiguity Resolution**: Clarify vague business questions before querying.\n"
                    "• **Data Profiling**: Detect missing values and dataset quality alerts."
                )

            return {
                "status": "success",
                "question": question,
                "sql": None,
                "dataframe": None,
                "answer": nl_ans,
                "chart": None
            }

        # Validate that tables exist for DATA_QUERY
        if not self.loader.loaded_tables:
            print("[ENGINE ERROR] No tables loaded in DuckDB.")
            return {
                "status": "error",
                "message": "No tables have been uploaded yet. Please click '⚡ Load HR Demo' or upload CSV/Excel files first."
            }

        if not self.llm.is_configured():
            print("[ENGINE ERROR] OpenRouter API Key missing.")
            return {
                "status": "error",
                "message": "OpenRouter API Key is missing. Please check your .env file."
            }

        # 2. Check for SQL question ambiguity
        ambiguity_res = self.check_ambiguity(question, chat_history)
        if ambiguity_res:
            return ambiguity_res

        # 3. Build multi-turn conversation context
        recent_context_lines = []
        for msg in chat_history[-4:]:
            if msg.get("role") == "user":
                recent_context_lines.append(f"User: {msg.get('content')}")
            elif msg.get("role") == "assistant" and msg.get("sql"):
                recent_context_lines.append(f"SQL Executed Previously: {msg.get('sql')}")

        context_str = "\n".join(recent_context_lines) if recent_context_lines else "None"

        # 4. Text-to-SQL Generation Prompt
        schema_text = self.loader.get_schema_prompt_text()
        system_prompt = (
            "You are a Senior Data Engineer & Text-to-SQL expert.\n"
            "Given the DuckDB database schema and conversation history, generate a single valid DuckDB SQL query.\n"
            "RULES:\n"
            "1. Output ONLY the SQL query. Do not wrap in markdown code blocks or add explanatory text.\n"
            "2. Use exact table and column names from the provided schema.\n"
            "3. Use standard DuckDB SQL dialect (supports JOINs, GROUP BY, aggregations, ILIKE for text matching).\n"
            "4. Make sure the query is strictly read-only SELECT or WITH statement."
        )

        user_prompt = (
            f"{schema_text}\n\n"
            f"Recent Conversation History:\n{context_str}\n\n"
            f"User Question: {question}\n\n"
            f"Generate DuckDB SQL Query:"
        )

        # Generate & Validate SQL with self-correction retry
        max_retries = 2
        last_error = ""
        sanitized_sql = ""

        for attempt in range(max_retries):
            retry_prompt = user_prompt
            if last_error:
                print(f"[ENGINE RETRY] Attempt {attempt+1} failed ({last_error}). Retrying...")
                retry_prompt += f"\n\nPrevious attempt failed with error: {last_error}. Please correct the SQL."

            print(f"[ENGINE LLM REQUEST] Sending prompt to OpenRouter ({self.llm.model})...")
            raw_sql = self.llm.generate_completion(system_prompt, retry_prompt, temperature=0.0)
            print(f"[ENGINE LLM RESPONSE] Raw SQL: {raw_sql}")
            
            is_valid, validation_res = validate_sql(raw_sql)

            if not is_valid:
                print(f"[ENGINE GUARDRAIL REJECTED] {validation_res}")
                last_error = validation_res
                continue

            sanitized_sql = validation_res
            
            # Execute query in DuckDB
            try:
                print(f"[ENGINE DUCKDB EXEC] Executing SQL: {sanitized_sql}")
                result_df = self.loader.con.execute(sanitized_sql).df()
                print(f"[ENGINE DUCKDB SUCCESS] Returned {len(result_df)} rows, {len(result_df.columns)} columns.")
                break
            except Exception as e:
                print(f"[ENGINE DUCKDB ERROR] {e}")
                last_error = str(e)
                sanitized_sql = ""

        if not sanitized_sql or 'result_df' not in locals():
            return {
                "status": "error",
                "message": f"Failed to generate executable SQL query. Error: {last_error}"
            }

        # 5. Generate Natural Language Answer Summary
        summary_system_prompt = (
            "You are a helpful Data Analytics Assistant.\n"
            "Given the user's question, the SQL executed, and the query results, provide a clear, concise (2-3 sentences)\n"
            "natural language answer summarizing the key analytical takeaway."
        )
        
        preview_data = result_df.head(10).to_dict(orient="records")
        summary_user_prompt = (
            f"Question: {question}\n"
            f"SQL Executed: {sanitized_sql}\n"
            f"Total Result Rows: {len(result_df)}\n"
            f"Sample Data: {preview_data}\n\n"
            f"Provide plain English takeaway summary:"
        )

        try:
            nl_answer = self.llm.generate_completion(summary_system_prompt, summary_user_prompt, temperature=0.2)
        except Exception as e:
            print(f"[ENGINE NL SUMMARY ERROR] {e}")
            nl_answer = f"Found {len(result_df)} matching records for your question."

        print(f"[ENGINE ANSWER] {nl_answer}\n")

        # 6. Build Auto Chart Visualization
        chart_fig = recommend_and_build_chart(result_df, question)

        return {
            "status": "success",
            "question": question,
            "sql": sanitized_sql,
            "dataframe": result_df,
            "answer": nl_answer,
            "chart": chart_fig
        }

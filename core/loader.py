import os
import re
import pandas as pd
import duckdb
from typing import List, Dict, Any, Tuple, Union

def clean_identifier(name: str) -> str:
    """
    Sanitizes column and table names into valid SQL identifiers (snake_case).
    Example: 'Employee ID (%)' -> 'employee_id'
    """
    # Remove file extension if present
    name = os.path.splitext(name)[0]
    # Replace non-alphanumeric chars with underscores
    name = re.sub(r'[^a-zA-Z0-9]', '_', name)
    # Collapse multiple underscores
    name = re.sub(r'_+', '_', name).strip('_')
    # Convert to lowercase
    name = name.lower()
    # Ensure doesn't start with digit
    if name and name[0].isdigit():
        name = f"t_{name}"
    return name or "table_data"

class DuckDBDataLoader:
    """
    In-memory DuckDB manager to load CSV/Excel files and extract metadata schemas.
    """
    def __init__(self, db_connection: duckdb.DuckDBPyConnection = None):
        self.con = db_connection or duckdb.connect(":memory:")
        self.loaded_tables: Dict[str, Dict[str, Any]] = {}

    def load_file(self, file_source: Union[str, Any], table_name_override: str = None) -> str:
        """
        Loads a CSV or XLSX file/stream into DuckDB.
        Returns the sanitized table name created in DuckDB.
        """
        # Determine filename/name
        if isinstance(file_source, str):
            filename = os.path.basename(file_source)
            raw_table_name = table_name_override or filename
            if file_source.endswith('.csv'):
                df = pd.read_csv(file_source)
            elif file_source.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_source)
            else:
                raise ValueError(f"Unsupported file format: {file_source}")
        else:
            # Streamlit UploadedFile object
            filename = getattr(file_source, 'name', 'uploaded_file.csv')
            raw_table_name = table_name_override or filename
            if filename.endswith('.csv'):
                df = pd.read_csv(file_source)
            elif filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_source)
            else:
                raise ValueError(f"Unsupported file format: {filename}")

        table_name = clean_identifier(raw_table_name)
        
        # Clean column names
        df.columns = [clean_identifier(str(col)) for col in df.columns]

        # Register DataFrame in DuckDB
        self.con.register(f"df_{table_name}", df)
        self.con.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df_{table_name}")
        
        # Store metadata
        self.loaded_tables[table_name] = {
            "original_filename": filename,
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()}
        }
        
        return table_name

    def get_schema_summary(self) -> Dict[str, Any]:
        """
        Extracts table schemas, column types, row counts, and sample rows for LLM context.
        """
        summary = {}
        for table_name, meta in self.loaded_tables.items():
            # Get DuckDB column types
            type_info = self.con.execute(f"DESCRIBE {table_name}").fetchall()
            col_types = {col[0]: col[1] for col in type_info}
            
            # Fetch 3 sample rows
            sample_df = self.con.execute(f"SELECT * FROM {table_name} LIMIT 3").df()
            sample_records = sample_df.to_dict(orient="records")
            
            summary[table_name] = {
                "original_filename": meta["original_filename"],
                "row_count": meta["row_count"],
                "columns": col_types,
                "sample_rows": sample_records
            }
        return summary

    def get_schema_prompt_text(self) -> str:
        """
        Formats schema summary into a clean markdown string for LLM Text-to-SQL prompts.
        """
        summary = self.get_schema_summary()
        if not summary:
            return "No tables currently loaded."

        lines = ["Database Tables & Schemas:"]
        for table_name, details in summary.items():
            lines.append(f"\nTable: `{table_name}` (from '{details['original_filename']}', {details['row_count']} rows)")
            lines.append("Columns:")
            for col, dtype in details["columns"].items():
                lines.append(f"  - `{col}` ({dtype})")
            
            if details["sample_rows"]:
                lines.append("Sample Data (First 3 rows):")
                for i, row in enumerate(details["sample_rows"], 1):
                    lines.append(f"  Row {i}: {row}")
        
        return "\n".join(lines)

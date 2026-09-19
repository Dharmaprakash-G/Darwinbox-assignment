import re
from typing import Tuple

PROHIBITED_KEYWORDS = [
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bUPDATE\b",
    r"\bINSERT\b",
    r"\bALTER\b",
    r"\bTRUNCATE\b",
    r"\bEXEC\b",
    r"\bEXECUTE\b",
    r"\bCREATE\b",
    r"\bGRANT\b",
    r"\bREVOKE\b"
]

def clean_sql_query(raw_sql: str) -> str:
    """
    Strips markdown blocks and trailing whitespace/semicolons from raw LLM output.
    """
    if not raw_sql:
        return ""
    
    # Strip markdown code fencing ```sql ... ```
    cleaned = re.sub(r"^```(?:sql)?\s*", "", raw_sql.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    
    # Remove trailing semicolons for single query execution
    cleaned = cleaned.rstrip(";").strip()
    return cleaned

def validate_sql(sql_query: str) -> Tuple[bool, str]:
    """
    Validates that a SQL query is strictly read-only and free of destructive statements.
    Returns (is_valid, sanitized_sql_or_error_message).
    """
    sanitized = clean_sql_query(sql_query)
    
    if not sanitized:
        return False, "Empty SQL query generated."

    # Enforce SELECT or WITH statement start
    uppercase_sql = sanitized.upper()
    if not (uppercase_sql.startswith("SELECT") or uppercase_sql.startswith("WITH")):
        return False, "Security Violation: Query must begin with SELECT or WITH."

    # Check for destructive keywords
    for pattern in PROHIBITED_KEYWORDS:
        if re.search(pattern, uppercase_sql):
            keyword = pattern.replace(r"\b", "")
            return False, f"Security Violation: Destructive command '{keyword}' is prohibited."

    return True, sanitized

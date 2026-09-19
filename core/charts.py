import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, Dict, Any

def recommend_and_build_chart(df: pd.DataFrame, question: str = "") -> Optional[go.Figure]:
    """
    Inspects a SQL result DataFrame and returns a customized Plotly Figure.
    Returns None if the dataset is not suitable for graphing (e.g. single scalar result or empty).
    """
    if df is None or df.empty or len(df) == 0:
        return None

    # Do not graph single-cell scalar results (e.g. SELECT COUNT(*))
    if df.shape == (1, 1):
        return None

    num_cols = df.select_dtypes(include=["number"]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category", "string"]).columns.tolist()
    date_cols = [c for c in df.columns if "date" in c.lower() or "year" in c.lower() or "month" in c.lower()]

    title = question.capitalize() if question else "Data Visualization"
    
    # Custom vibrant color template
    color_sequence = ["#6366F1", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#06B6D4"]

    # 1. Line Chart: Date column + numeric column
    if date_cols and num_cols:
        x_col = date_cols[0]
        y_col = num_cols[0]
        df_sorted = df.sort_values(by=x_col)
        fig = px.line(
            df_sorted, 
            x=x_col, 
            y=y_col, 
            title=title, 
            markers=True,
            color_discrete_sequence=color_sequence
        )
        fig.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20))
        return fig

    # 2. Bar Chart: Categorical column + Numeric column
    if cat_cols and num_cols:
        x_col = cat_cols[0]
        y_col = num_cols[0]
        
        # If low cardinality (<= 6 categories), consider Pie or Bar
        if len(df) <= 6 and ("percentage" in question.lower() or "distribution" in question.lower() or "share" in question.lower()):
            fig = px.pie(
                df, 
                names=x_col, 
                values=y_col, 
                title=title,
                color_discrete_sequence=color_sequence,
                hole=0.4
            )
        else:
            fig = px.bar(
                df, 
                x=x_col, 
                y=y_col, 
                title=title,
                text_auto=".2s" if df[y_col].dtype != "int64" else True,
                color=x_col,
                color_discrete_sequence=color_sequence
            )
        fig.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20))
        return fig

    # 3. Scatter Plot: 2 Numeric columns
    if len(num_cols) >= 2:
        x_col = num_cols[0]
        y_col = num_cols[1]
        fig = px.scatter(
            df, 
            x=x_col, 
            y=y_col, 
            title=title,
            color_discrete_sequence=color_sequence,
            hover_data=cat_cols[:2] if cat_cols else None
        )
        fig.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20))
        return fig

    # 4. Fallback Bar Chart for numeric index
    if num_cols:
        y_col = num_cols[0]
        fig = px.bar(
            df, 
            y=y_col, 
            title=title,
            color_discrete_sequence=color_sequence
        )
        fig.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20))
        return fig

    return None

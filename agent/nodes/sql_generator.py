from typing import Any
import logging

from agent.helper import litellm_wrapper
from agent.schema_extractor import SchemaExtractor

logger = logging.getLogger(__name__)


class SQLGenerator:
    """
    Generate SQL queries from intent analysis
    """

    def __init__(self):
        self.schema_extractor = SchemaExtractor()
        self.schema_info = self.schema_extractor.get_schema_for_classification()

    def generate_sql(self, intent_analysis: dict[str, Any]) -> dict[str, Any]:
        """Generate SQL query from intent analysis"""

        operation_type = intent_analysis["operation_type"]
        logger.info(f"Generating SQL for {operation_type} operation")

        try:
            messages = [
                {"role": "system",
                 "content": f"""You are a SQL expert. Generate ONE complete executable SQL statement.

                DATABASE SCHEMA:
                {self.schema_info}
                
                INTENT ANALYSIS:
                - Intent: {intent_analysis.get('intent_description', '')}
                - Tables: {intent_analysis.get('tables_needed', [])}
                - Columns: {intent_analysis.get('columns_needed', [])}
                - Conditions: {intent_analysis.get('conditions', '')}
                - Operation: {intent_analysis.get('operation_type', '')}
                
                Generate a single SQL statement that accomplishes the user's request. Use subqueries, JOINs, or whatever SQL techniques needed to make it work in one statement.
                
                Return ONLY the SQL statement, nothing else."""},
                {"role": "user",
                 "content": f"Generate SQL for: {intent_analysis.get('original_query', '')}"
                 }
            ]

            response = litellm_wrapper(messages)
            sql_query = response.strip()

            if sql_query.startswith('```sql'):
                sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
            elif sql_query.startswith('```'):
                sql_query = sql_query.replace('```', '').strip()

            return {
                "sql_query": sql_query,
                "operation_type": operation_type,
                "original_query": intent_analysis.get("original_query", "")
            }

        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            return {
                "sql_query": None,
                "error": f"SQL generation error: {str(e)}",
                "operation_type": operation_type
            }
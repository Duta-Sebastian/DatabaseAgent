from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
import logging
from typing import Dict, Any

from database.connection import engine
from agent.schema_extractor import SchemaExtractor

logger = logging.getLogger(__name__)


class SQLExecutor:
    """
    Execute SQL statements using the existing database engine
    """

    def __init__(self):
        self.schema_extractor = SchemaExtractor()
        self.engine = engine

    def execute_sql(self, sql_query: str, operation_type: str = "UNKNOWN") -> Dict[str, Any]:
        """Execute SQL query and return results"""

        if not sql_query or sql_query.strip() == "":
            return {
                "success": False,
                "error": "No SQL query provided",
                "results": []
            }

        try:
            with self.engine.connect() as connection:
                result = connection.execute(text(sql_query))

                if operation_type in ["SELECT", "COUNT", "AGGREGATE"]:
                    # Read operations - fetch results
                    rows = result.fetchall()
                    column_names = list(result.keys()) if result.keys() else []

                    # Convert to list of dictionaries
                    results = []
                    for row in rows:
                        row_dict = dict(zip(column_names, row))
                        results.append(row_dict)

                    return {
                        "success": True,
                        "results": results,
                        "column_names": column_names,
                        "row_count": len(results),
                        "operation_type": operation_type
                    }

                else:
                    # Write operations - commit and return affected rows
                    connection.commit()
                    affected_rows = result.rowcount

                    return {
                        "success": True,
                        "results": [],
                        "affected_rows": affected_rows,
                        "operation_type": operation_type,
                        "message": f"{operation_type} executed successfully. {affected_rows} rows affected."
                    }

        except SQLAlchemyError as e:
            logger.error(f"Database error: {e}")
            return {
                "success": False,
                "error": f"Database error: {str(e)}",
                "sql_query": sql_query
            }
        except Exception as e:
            logger.error(f"Execution error: {e}")
            return {
                "success": False,
                "error": f"Execution error: {str(e)}",
                "sql_query": sql_query
            }

    def format_results(self, execution_result: Dict[str, Any]) -> str:
        """Format execution results for display"""

        if not execution_result.get("success", False):
            return f"Error: {execution_result.get('error', 'Unknown error')}"

        if execution_result.get("operation_type") in ["SELECT", "COUNT", "AGGREGATE"]:
            results = execution_result.get("results", [])
            if not results:
                return "No results found."

            # Format as table
            output = []
            if results:
                headers = list(results[0].keys())
                output.append(" | ".join(headers))
                output.append("-" * len(" | ".join(headers)))

                for row in results:
                    output.append(" | ".join(str(row[col]) for col in headers))

            return "\n".join(output)
        else:
            return execution_result.get("message", "Operation completed successfully.")

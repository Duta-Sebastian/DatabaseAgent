from typing import Any, Literal
import logging

from agent.helper import litellm_wrapper
from agent.schema_extractor import SchemaExtractor

logger = logging.getLogger(__name__)

OperationType = Literal["SELECT", "COUNT", "AGGREGATE", "INSERT", "UPDATE", "DELETE", "UNKNOWN"]


class OperationClassifier:
    """
    Classify database operations from natural language using LLM with schema context
    """

    def __init__(self):
        self.schema_extractor = SchemaExtractor()
        self.schema_info = self.schema_extractor.get_schema_for_classification()

    def classify_operation(self, user_query: str, conversation_history: str) -> dict[str, Any]:
        """Classify the database operation type from user query"""
        logger.info(f"Classifying operation for: {user_query}")

        result = self._classify_with_llm(user_query, conversation_history)

        op_info = self.get_operation_info(result["operation_type"])
        result["safety_level"] = op_info["safety_level"]
        result["description"] = op_info["description"]

        if result["operation_type"] == "UNKNOWN":
            result["needs_clarification"] = True
            logger.info("Classification uncertain - needs clarification")
        else:
            result["needs_clarification"] = False

        return result

    def _classify_with_llm(self, user_query: str, conversation_history: str) -> dict[str, Any]:
        """Use LLM for operation classification with schema context"""

        messages = [
            {
                "role": "system",
                "content": f"""You are a database operation classifier with knowledge of the database schema.

        DATABASE SCHEMA:
        {self.schema_info}

        CONVERSATION CONTEXT:
        {conversation_history}

        OPERATION TYPES:

        **SELECT** - Reading/retrieving data
        Examples: "show users", "list products", "find orders"

        **COUNT** - Counting records  
        Examples: "how many users", "count orders", "number of products"

        **AGGREGATE** - Mathematical calculations
        Examples: "sum of sales", "average price", "total revenue", "maximum order"

        **INSERT** - Adding new data
        Examples: "add user", "create product", "insert order"

        **UPDATE** - Modifying existing data
        Examples: "update email", "change price", "modify status"

        **DELETE** - Removing data
        Examples: "delete user", "remove product", "clear orders"

        **UNKNOWN** - Cannot determine operation (use sparingly)

        CLASSIFICATION RULES:
        1. Look for table/column names from schema in the query
        2. Match mathematical terms with numeric columns
        3. Focus on the primary intent of the query
        4. Use UNKNOWN only when truly unclear

        Return format:
        OPERATION: [operation_type]
        CONFIDENCE: [0.0-1.0]
        REASONING: [brief explanation]"""
            },
            {
                "role": "user",
                "content": f"Classify: '{user_query}'"
            }
        ]

        try:
            response = litellm_wrapper(messages)
            return self._parse_response(response, user_query)

        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            return {
                "operation_type": "UNKNOWN",
                "confidence": 0.0,
                "reasoning": f"Classification error: {str(e)}",
                "needs_clarification": True
            }

    @staticmethod
    def _parse_response(response: str, original_query: str) -> dict[str, Any]:
        """Parse the LLM response"""
        try:
            lines = response.strip().split('\n')

            operation_type: OperationType = "UNKNOWN"
            confidence = 0.0
            reasoning = "Failed to parse response"

            for line in lines:
                line = line.strip()
                if line.startswith("OPERATION:"):
                    parsed_op = line.split(":", 1)[1].strip().upper()
                    # Validate operation type using our Literal
                    if parsed_op in ["SELECT", "COUNT", "AGGREGATE", "INSERT", "UPDATE", "DELETE", "UNKNOWN"]:
                        operation_type = parsed_op  # type: ignore
                elif line.startswith("CONFIDENCE:"):
                    confidence = float(line.split(":", 1)[1].strip())
                elif line.startswith("REASONING:"):
                    reasoning = line.split(":", 1)[1].strip()

            # Clamp confidence
            confidence = max(0.0, min(1.0, confidence))

            return {
                "operation_type": operation_type,
                "confidence": confidence,
                "reasoning": reasoning,
                "original_query": original_query
            }

        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            return {
                "operation_type": "UNKNOWN",
                "confidence": 0.0,
                "reasoning": f"Parse error: {str(e)}",
                "original_query": original_query
            }

    @staticmethod
    def get_operation_info(operation_type: OperationType) -> dict[str, Any]:
        """Get operation information"""

        operation_info = {
            "SELECT": {
                "description": "Retrieve data from the database",
                "safety_level": "SAFE"
            },
            "COUNT": {
                "description": "Count records in the database",
                "safety_level": "SAFE"
            },
            "AGGREGATE": {
                "description": "Perform calculations on data",
                "safety_level": "SAFE"
            },
            "INSERT": {
                "description": "Add new data to the database",
                "safety_level": "CAUTION"
            },
            "UPDATE": {
                "description": "Modify existing data",
                "safety_level": "DANGEROUS"
            },
            "DELETE": {
                "description": "Remove data from the database",
                "safety_level": "DANGEROUS"
            }
        }

        return operation_info.get(operation_type, {
            "description": "Unknown operation type",
            "safety_level": "UNKNOWN"
        })
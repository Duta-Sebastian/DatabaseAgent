from typing import Any, Literal
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import logging

from agent.schema_extractor import SchemaExtractor

logger = logging.getLogger(__name__)

OperationType = Literal["SELECT", "COUNT", "AGGREGATE", "INSERT", "UPDATE", "DELETE", "UNKNOWN"]


class IntentAnalyzer:
    """
    Stage 2: Analyze user intent to determine specific tables, columns, and conditions
    """

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.schema_extractor = SchemaExtractor()
        self.schema_info = self.schema_extractor.get_schema_for_classification()

    def analyze_intent(self, user_query: str, operation_type: OperationType, reasoning: str) -> dict[str, Any]:
        """Analyze user intent based on query, operation type, and classification reasoning"""
        logger.info(f"Analyzing intent for {operation_type}: {user_query}")

        intent_result = self._analyze_with_llm(user_query, operation_type, reasoning)

        intent_result["operation_type"] = operation_type
        intent_result["original_query"] = user_query
        intent_result["classification_reasoning"] = reasoning

        return intent_result

    def _analyze_with_llm(self, user_query: str, operation_type: OperationType, reasoning: str) -> dict[str, Any]:
        """Analyze intent using LLM"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are analyzing user intent for a {operation_type} database operation.

DATABASE SCHEMA:
{self.schema_info}

CLASSIFICATION CONTEXT:
Operation Type: {operation_type}
Operation Guidance: {self._get_operation_guidance(operation_type)}
Classification Reasoning: {reasoning}

Analyze the user's request and determine exactly what they want to accomplish.

Respond in this exact format:

INTENT: [clear description of what user wants]
TABLES: [table names needed, comma-separated]
COLUMNS: [specific columns needed, comma-separated]
CONDITIONS: [filtering conditions if any]"""),
            ("human", f"Analyze: '{user_query}'")
        ])

        response = self.llm.invoke(prompt.format_messages())
        return self._parse_intent_response(response.content)

    @staticmethod
    def _parse_intent_response(response: str) -> dict[str, Any]:
        """Parse the LLM response"""
        lines = response.strip().split('\n')

        intent = ""
        tables = []
        columns = []
        conditions = ""

        for line in lines:
            line = line.strip()
            if line.startswith("INTENT:"):
                intent = line.split(":", 1)[1].strip()
            elif line.startswith("TABLES:"):
                tables_str = line.split(":", 1)[1].strip()
                tables = [t.strip() for t in tables_str.split(',') if t.strip()]
            elif line.startswith("COLUMNS:"):
                columns_str = line.split(":", 1)[1].strip()
                columns = [c.strip() for c in columns_str.split(',') if c.strip()]
            elif line.startswith("CONDITIONS:"):
                conditions = line.split(":", 1)[1].strip()

        return {
            "intent_description": intent,
            "tables_needed": tables,
            "columns_needed": columns,
            "conditions": conditions
        }

    @staticmethod
    def _get_operation_guidance(operation_type: OperationType) -> str:
        """Get operation-specific guidance"""

        guidance = {
            "SELECT": "- Which columns to display\n- Which tables contain the data\n- Any filtering conditions\n- How tables relate",
            "COUNT": "- What to count\n- Which table to count from\n- Any filtering conditions",
            "AGGREGATE": "- Which numeric columns to calculate (SUM, AVG, etc.)\n- Which tables contain the data\n- Any grouping needed",
            "INSERT": "- Which table to insert into\n- What data to insert",
            "UPDATE": "- Which table to update\n- Which columns to modify\n- Which records to update",
            "DELETE": "- Which table to delete from\n- Which records to delete"
        }

        return guidance.get(operation_type, "- What the user wants to accomplish")
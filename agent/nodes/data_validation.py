from typing import Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import logging

from agent.schema_extractor import SchemaExtractor

logger = logging.getLogger(__name__)


class DataValidator:
    """
    Stage 3: Validate if we have sufficient data to proceed with SQL generation
    """

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.schema_extractor = SchemaExtractor()
        self.schema_info = self.schema_extractor.get_schema_for_classification()

    def validate_data_completeness(self, intent_analysis: dict[str, Any], classification_result: dict[str, Any]) -> \
    dict[str, Any]:
        """Check if we have all necessary data to proceed with SQL generation"""

        operation_type = classification_result.get("operation_type", "UNKNOWN")
        logger.info(f"Validating data completeness for {operation_type} operation")

        try:
            if operation_type in ["SELECT", "COUNT", "AGGREGATE"]:
                return self._validate_read_operation(intent_analysis)
            elif operation_type == "INSERT":
                return self._validate_insert_operation(intent_analysis)
            elif operation_type == "UPDATE":
                return self._validate_update_operation(intent_analysis)
            elif operation_type == "DELETE":
                return self._validate_delete_operation(intent_analysis)
            else:
                return {
                    "is_complete": False,
                    "needs_clarification": True,
                    "missing_data": ["Operation type unclear"],
                    "clarification_questions": ["What type of database operation do you want to perform?"],
                    "can_proceed_to_sql": False
                }

        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            return {
                "is_complete": False,
                "needs_clarification": True,
                "missing_data": [f"Validation error: {str(e)}"],
                "clarification_questions": ["Could you rephrase your request?"],
                "can_proceed_to_sql": False
            }

    def _validate_read_operation(self, intent_analysis: dict[str, Any]) -> dict[str, Any]:
        """Validate SELECT/COUNT/AGGREGATE operations using LLM"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are validating if a READ operation (SELECT/COUNT/AGGREGATE) has sufficient data.

DATABASE SCHEMA:
{self.schema_info}

INTENT ANALYSIS:
- Intent: {intent_analysis.get('intent_description', '')}
- Tables: {intent_analysis.get('tables_needed', [])}
- Columns: {intent_analysis.get('columns_needed', [])}
- Conditions: {intent_analysis.get('conditions', '')}
- Original Query: {intent_analysis.get('original_query', '')}

For READ operations, check:
1. Is the target table clearly identified?
2. Are the columns/data requested clear enough?
3. Are any conditions or filters clear enough?

Most READ operations can proceed even with minimal info, but some might need clarification.

Respond in this format:
IS_COMPLETE: [true/false]
MISSING_DATA: [comma-separated list of missing data, or "none"]
QUESTIONS: [specific questions to ask user, separated by |, or "none"]
NOTES: [brief explanation]"""),
            ("human", f"Validate READ operation for: {intent_analysis.get('original_query', '')}")
        ])

        response = self.llm.invoke(prompt.format_messages())
        return self._parse_validation_response(response.content)

    def _validate_insert_operation(self, intent_analysis: dict[str, Any]) -> dict[str, Any]:
        """Validate INSERT operations using LLM"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are validating if an INSERT operation has sufficient data.

DATABASE SCHEMA:
{self.schema_info}

INTENT ANALYSIS:
- Intent: {intent_analysis.get('intent_description', '')}
- Tables: {intent_analysis.get('tables_needed', [])}
- Columns: {intent_analysis.get('columns_needed', [])}
- Conditions: {intent_analysis.get('conditions', '')}
- Original Query: {intent_analysis.get('original_query', '')}

For INSERT operations, check:
1. Do we know WHICH table to insert into?
2. Do we have VALUES for required fields?
3. Are there missing required fields that need user input?

Respond in this format:
IS_COMPLETE: [true/false]
MISSING_DATA: [comma-separated list of missing required data, or "none"]
QUESTIONS: [specific questions to ask user, separated by |, or "none"]
NOTES: [brief explanation of what's missing]"""),
            ("human", f"Validate INSERT data for: {intent_analysis.get('original_query', '')}")
        ])

        response = self.llm.invoke(prompt.format_messages())
        return self._parse_validation_response(response.content)

    def _validate_update_operation(self, intent_analysis: dict[str, Any]) -> dict[str, Any]:
        """Validate UPDATE operations using LLM"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are validating if an UPDATE operation has sufficient data.

DATABASE SCHEMA:
{self.schema_info}

INTENT ANALYSIS:
- Intent: {intent_analysis.get('intent_description', '')}
- Tables: {intent_analysis.get('tables_needed', [])}
- Columns: {intent_analysis.get('columns_needed', [])}
- Conditions: {intent_analysis.get('conditions', '')}
- Original Query: {intent_analysis.get('original_query', '')}

For UPDATE operations, check:
1. Do we know WHICH records to update (WHERE conditions)?
2. Do we know WHAT to update TO (new values)?
3. Are the conditions specific enough to avoid updating too many records?

UPDATE without proper WHERE conditions is dangerous and should require clarification.

Respond in this format:
IS_COMPLETE: [true/false]
MISSING_DATA: [comma-separated list of missing data, or "none"]
QUESTIONS: [specific questions to ask user, separated by |, or "none"]
NOTES: [brief explanation of what's missing or why it's unsafe]"""),
            ("human", f"Validate UPDATE operation for: {intent_analysis.get('original_query', '')}")
        ])

        response = self.llm.invoke(prompt.format_messages())
        return self._parse_validation_response(response.content)

    def _validate_delete_operation(self, intent_analysis: dict[str, Any]) -> dict[str, Any]:
        """Validate DELETE operations using LLM"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are validating if a DELETE operation has sufficient data.

DATABASE SCHEMA:
{self.schema_info}

INTENT ANALYSIS:
- Intent: {intent_analysis.get('intent_description', '')}
- Tables: {intent_analysis.get('tables_needed', [])}
- Columns: {intent_analysis.get('columns_needed', [])}
- Conditions: {intent_analysis.get('conditions', '')}
- Original Query: {intent_analysis.get('original_query', '')}

For DELETE operations, check:
1. Do we have SPECIFIC WHERE conditions to identify which records to delete?
2. Are the conditions precise enough to avoid deleting too much data?
3. Is this a safe deletion or could it affect many records?

DELETE operations are dangerous and must have precise conditions. Broad deletions like "delete all" or "delete everything" require explicit confirmation.

Respond in this format:
IS_COMPLETE: [true/false]
MISSING_DATA: [comma-separated list of missing data, or "none"]
QUESTIONS: [specific questions to ask user, separated by |, or "none"]
NOTES: [brief explanation of safety concerns or missing conditions]"""),
            ("human", f"Validate DELETE operation for: {intent_analysis.get('original_query', '')}")
        ])

        response = self.llm.invoke(prompt.format_messages())
        return self._parse_validation_response(response.content)

    @staticmethod
    def _parse_validation_response(response: str) -> dict[str, Any]:
        """Parse LLM validation response"""
        lines = response.strip().split('\n')

        result = {
            "is_complete": False,
            "missing_data": [],
            "clarification_questions": [],
            "validation_notes": ""
        }

        for line in lines:
            line = line.strip()
            if line.startswith("IS_COMPLETE:"):
                complete_str = line.split(":", 1)[1].strip().lower()
                result["is_complete"] = complete_str in ["true", "yes", "1"]
            elif line.startswith("MISSING_DATA:"):
                missing_str = line.split(":", 1)[1].strip()
                if missing_str and missing_str.lower() not in ["none", "null", ""]:
                    result["missing_data"] = [item.strip() for item in missing_str.split(',') if item.strip()]
            elif line.startswith("QUESTIONS:"):
                questions_str = line.split(":", 1)[1].strip()
                if questions_str and questions_str.lower() not in ["none", "null", ""]:
                    result["clarification_questions"] = [q.strip() for q in questions_str.split('|') if q.strip()]
            elif line.startswith("NOTES:"):
                result["validation_notes"] = line.split(":", 1)[1].strip()

        result["needs_clarification"] = not result["is_complete"]
        result["can_proceed_to_sql"] = result["is_complete"]

        return result

    @staticmethod
    def generate_clarification_message(validation_result: dict[str, Any]) -> str:
        """Generate a user-friendly clarification message"""

        missing_data = validation_result.get("missing_data", [])
        questions = validation_result.get("clarification_questions", [])

        if not questions and not missing_data:
            return "I need more information to proceed. Could you provide more details?"

        message_parts = ["I need some additional information to complete your request:"]

        if questions:
            for i, question in enumerate(questions, 1):
                message_parts.append(f"{i}. {question}")
        elif missing_data:
            message_parts.append(f"Missing data: {', '.join(missing_data)}")

        return "\n".join(message_parts)
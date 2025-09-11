from typing import TypedDict, Optional, List, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
import logging

from agent.nodes.data_validation import DataValidator
from agent.nodes.intent_analyzer import IntentAnalyzer
from agent.nodes.operation_classifier import OperationClassifier
from agent.nodes.sql_executor import SQLExecutor
from agent.nodes.sql_generator import SQLGenerator

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    messages: List[dict]
    user_query: str
    classification_result: Optional[dict]
    intent_analysis: Optional[dict]
    validation_result: Optional[dict]
    sql_result: Optional[dict]
    execution_result: Optional[dict]
    needs_clarification: bool


class DatabaseAgent:
    """LangGraph-based database agent with memory for conversations"""

    def __init__(self):
        self.classifier = OperationClassifier()
        self.intent_analyzer = IntentAnalyzer()
        self.data_validator = DataValidator()
        self.sql_generator = SQLGenerator()
        self.sql_executor = SQLExecutor()

        # Use MemorySaver for conversation context - avoids SQLite conflicts
        self.checkpointer = MemorySaver()
        self.graph = self._build_graph()
        self.app = self.graph.compile(checkpointer=self.checkpointer)

    def _build_graph(self) -> StateGraph:
        """Build the workflow with conditional paths"""
        workflow = StateGraph(AgentState)

        workflow.add_node("classify_operation", self._classify_operation_node)
        workflow.add_node("analyze_intent", self._analyze_intent_node)
        workflow.add_node("validate_data", self._validate_data_node)
        workflow.add_node("generate_sql", self._generate_sql_node)
        workflow.add_node("execute_sql", self._execute_sql_node)
        workflow.add_node("request_clarification", self._request_clarification_node)

        workflow.set_entry_point("classify_operation")

        workflow.add_edge("classify_operation", "analyze_intent")
        workflow.add_edge("analyze_intent", "validate_data")

        workflow.add_conditional_edges(
            "validate_data",
            self._should_clarify_or_proceed,
            {
                "clarify": "request_clarification",
                "generate_sql": "generate_sql"
            }
        )

        workflow.add_edge("request_clarification", END)
        workflow.add_edge("generate_sql", "execute_sql")
        workflow.add_edge("execute_sql", END)

        return workflow

    @staticmethod
    def _should_clarify_or_proceed(state: AgentState) -> Literal["clarify", "generate_sql"]:
        """Decide whether to ask for clarification or proceed to SQL generation"""
        validation_result = state.get("validation_result", {})
        if validation_result.get("needs_clarification", False):
            return "clarify"
        return "generate_sql"

    def _classify_operation_node(self, state: AgentState) -> AgentState:
        """Node: Classify the database operation"""
        try:
            logger.info(f"Classifying: {state['user_query']}")
            result = self.classifier.classify_operation(
                state["user_query"],
                self._get_conversation_context(state)
            )

            print(f"Classification Result:")
            print(f"   Operation: {result['operation_type']}")
            print(f"   Confidence: {result.get('confidence', 'N/A')}")
            print(f"   Reasoning: {result.get('reasoning', 'N/A')}")
            print(f"   Safety: {result.get('safety_level', 'N/A')}")

            return {**state, "classification_result": result}

        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return {
                **state,
                "classification_result": {
                    "operation_type": "UNKNOWN",
                    "error": str(e)
                }
            }

    def _analyze_intent_node(self, state: AgentState) -> AgentState:
        """Node: Analyze user intent with conversation context"""
        try:
            logger.info("Analyzing intent...")
            classification = state["classification_result"]

            if classification.get("error"):
                print(f"Skipping intent analysis due to classification error")
                return {
                    **state,
                    "intent_analysis": {"error": "Classification failed"}
                }

            intent_result = self.intent_analyzer.analyze_intent(
                state["user_query"],
                classification["operation_type"],
                classification.get("reasoning", ""),
                self._get_conversation_context(state)
            )

            print(f"Intent Analysis Result:")
            print(f"   Intent: {intent_result.get('intent_description', 'N/A')}")
            print(f"   Tables: {intent_result.get('tables_needed', [])}")
            print(f"   Columns: {intent_result.get('columns_needed', [])}")
            print(f"   Conditions: {intent_result.get('conditions', 'None')}")

            return {**state, "intent_analysis": intent_result}

        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
            return {**state, "intent_analysis": {"error": str(e)}}

    def _get_conversation_context(self, state: AgentState) -> str:
        """Extract relevant context from conversation history"""
        messages = state.get("messages", [])
        if len(messages) <= 1:  # Only current message
            return ""

        # Get previous messages (excluding current one)
        previous_messages = messages[:-1]
        context_parts = []

        for msg in previous_messages[-3:]:  # Last 3 messages for context
            if hasattr(msg, 'content'):
                if msg.__class__.__name__ == "HumanMessage":
                    context_parts.append(f"User previously asked: {msg.content}")
                elif msg.__class__.__name__ == "AIMessage":
                    context_parts.append(f"Agent previously responded: {msg.content}")

        return " | ".join(context_parts) if context_parts else ""

    def _validate_data_node(self, state: AgentState) -> AgentState:
        """Node: Validate data completeness"""
        try:
            logger.info("Validating data completeness...")

            if (state.get("classification_result", {}).get("error") or
                    state.get("intent_analysis", {}).get("error")):
                print(f"Skipping validation due to previous errors")
                return {
                    **state,
                    "validation_result": {
                        "is_complete": False,
                        "needs_clarification": True,
                        "error": "Previous stage failed"
                    }
                }

            validation_result = self.data_validator.validate_data_completeness(
                state["intent_analysis"],
                state["classification_result"],
                self._get_conversation_context(state)
            )

            print(f"Data Validation Result:")
            print(f"   Complete: {validation_result.get('is_complete', False)}")
            print(f"   Can Proceed: {validation_result.get('can_proceed_to_sql', False)}")

            if validation_result.get("missing_data"):
                print(f"   Missing Data: {validation_result['missing_data']}")

            if validation_result.get("clarification_questions"):
                print(f"   Questions Needed: {len(validation_result['clarification_questions'])}")

            return {
                **state,
                "validation_result": validation_result,
                "needs_clarification": validation_result.get("needs_clarification", False)
            }

        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            return {
                **state,
                "validation_result": {
                    "is_complete": False,
                    "needs_clarification": True,
                    "error": str(e)
                }
            }

    def _request_clarification_node(self, state: AgentState) -> AgentState:
        """Node: Request clarification for missing data"""
        validation_result = state.get("validation_result", {})
        clarification_msg = self.data_validator.generate_clarification_message(validation_result)

        print(f"Requesting Clarification:")
        print(f"   {clarification_msg}")

        updated_messages = state["messages"] + [
            AIMessage(content=clarification_msg)
        ]

        return {**state, "messages": updated_messages}

    def _generate_sql_node(self, state: AgentState) -> AgentState:
        """Node: Generate SQL from validated intent analysis"""
        try:
            logger.info("Generating SQL...")

            if not state.get("validation_result", {}).get("can_proceed_to_sql", False):
                print(f"Skipping SQL generation - validation failed")
                return {**state, "sql_result": {"error": "Data validation failed"}}

            sql_result = self.sql_generator.generate_sql(
                state["intent_analysis"]
            )

            print(f"SQL Generation Result:")
            if sql_result.get('error'):
                print(f"   Error: {sql_result['error']}")
            else:
                print(f"   SQL: {sql_result.get('sql_query', 'None')}")

            return {**state, "sql_result": sql_result}

        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            return {**state, "sql_result": {"error": str(e)}}

    def _execute_sql_node(self, state: AgentState) -> AgentState:
        """Node: Execute the generated SQL query"""
        try:
            logger.info("Executing SQL...")
            sql_result = state.get("sql_result", {})

            if not sql_result or sql_result.get("error"):
                print(f"Skipping SQL execution - no valid SQL")
                return {
                    **state,
                    "execution_result": {
                        "success": False,
                        "error": "No valid SQL to execute"
                    }
                }

            sql_query = sql_result.get("sql_query")
            operation_type = sql_result.get("operation_type", "UNKNOWN")

            execution_result = self.sql_executor.execute_sql(sql_query, operation_type)

            print(f"SQL Execution Result:")
            if execution_result.get("success"):
                print(f"   Success: {execution_result.get('message', 'Query executed')}")
                if execution_result.get("results"):
                    formatted = self.sql_executor.format_results(execution_result)
                    print(f"   Results:\n{formatted}")
            else:
                print(f"   Error: {execution_result.get('error')}")

            return {**state, "execution_result": execution_result}

        except Exception as e:
            logger.error(f"SQL execution failed: {e}")
            return {
                **state,
                "execution_result": {
                    "success": False,
                    "error": str(e)
                }
            }

    def _get_conversation_context(self, state, limit: int = 5) -> str:
        """Return last N messages as plain text conversation history."""
        messages = state.get("messages", [])
        if not messages:
            return "No prior conversation."

        recent = messages[-limit:]  # only the last N messages
        context_lines = []
        for msg in recent:
            role = getattr(msg, "type", "user")
            role = "User" if role == "human" else "Agent"
            content = getattr(msg, "content", str(msg))
            context_lines.append(f"{role}: {content}")

        return "\n".join(context_lines)

    def run_query(self, user_query: str, thread_id: str = "default") -> dict:
        """Run a query through the pipeline with conversation context"""
        print(f"\nProcessing Query: '{user_query}'")
        print("=" * 60)

        # Use thread_id for conversation continuity
        config = {"configurable": {"thread_id": thread_id}}
        current_state = self.app.get_state(config)

        if current_state:
            # Continue from previous conversation
            messages = current_state.values.get("messages", []) + [HumanMessage(content=user_query)]
        else:
            # First query in this thread
            messages = [HumanMessage(content=user_query)]

        initial_state = {
            "messages": messages,
            "user_query": user_query,
            "classification_result": None,
            "intent_analysis": None,
            "validation_result": None,
            "sql_result": None,
            "execution_result": None,
            "needs_clarification": False,
            "waiting_for_user": False,
            "user_response": None
        }

        final_state = self.app.invoke(initial_state, config=config)

        print(f"\nFinal Pipeline Results:")
        print("=" * 60)
        print(f"Original Query: {final_state['user_query']}")

        # Show final results
        execution_result = final_state.get('execution_result', {})
        if execution_result and execution_result.get('success'):
            print(f"\nQUERY EXECUTED SUCCESSFULLY!")
            if execution_result.get('results'):
                print(f"Found {execution_result.get('row_count', 0)} results")

        return final_state

    def continue_with_user_response(self, user_response: str, thread_id: str = "default") -> dict:
        """Continue processing after receiving user clarification"""
        print(f"\nContinuing with user response: '{user_response}'")
        print("=" * 60)

        # Get the current state from the checkpointer
        config = {"configurable": {"thread_id": thread_id}}
        current_state = self.app.get_state(config)

        if not current_state:
            print("No conversation found to continue")
            return {}

        # Update the state with user response
        updated_state = {
            **current_state.values,
            "user_response": user_response,
            "user_query": f"{current_state.values.get('user_query', '')} [User clarification: {user_response}]",
            "messages": current_state.values.get("messages", []) + [HumanMessage(content=user_response)]
        }

        # Continue from where we left off
        final_state = self.app.invoke(updated_state, config=config)

        print(f"\nContinuation Results:")
        print("=" * 60)

        # Show final results
        execution_result = final_state.get('execution_result', {})
        if execution_result and execution_result.get('success'):
            print(f"\nQUERY EXECUTED SUCCESSFULLY!")
            if execution_result.get('results'):
                print(f"Found {execution_result.get('row_count', 0)} results")

        return final_state
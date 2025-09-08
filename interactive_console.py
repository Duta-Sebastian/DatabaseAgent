import logging
from typing import Dict, Optional
from datetime import datetime

from langchain_openai import ChatOpenAI
from agent.database_agent import DatabaseAgent

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Reduce noise in console
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class InteractiveConsole:
    """Interactive console for the Database Agent"""

    def __init__(self):
        self.agent: Optional[DatabaseAgent] = None
        self.current_thread_id = "main"
        self.session_stats = {
            "queries_processed": 0,
            "successful_queries": 0,
            "clarifications_requested": 0
        }

    def initialize_agent(self) -> bool:
        """Initialize the AI agent"""
        try:
            print("Initializing Database Agent...")
            llm = ChatOpenAI(model="gpt-4o", temperature=0)
            self.agent = DatabaseAgent(llm)
            print("Agent initialized successfully!\n")
            return True
        except Exception as e:
            print(f"Failed to initialize agent: {e}")
            return False

    @staticmethod
    def print_welcome():
        """Print welcome message and instructions"""
        print("=" * 70)
        print("      AI Database Agent - Interactive Console")
        print("=" * 70)
        print("Ask me anything about your database in natural language!")
        print("\nExamples:")
        print("  • 'Show me all users who have placed orders'")
        print("  • 'How many products do we have?'")
        print("  • 'Update user email where name is John'")
        print("  • 'Delete old orders from last year'")
        print("\nCommands:")
        print("  • 'help' - Show this help")
        print("  • 'stats' - Show session statistics")
        print("  • 'new' - Start a new conversation thread")
        print("  • 'quit' or 'exit' - Exit the console")
        print("\nNote: If I need clarification, I'll ask follow-up questions.")
        print("=" * 70)
        print()

    def handle_command(self, user_input: str) -> bool:
        """Handle special commands. Returns True if command was handled."""
        command = user_input.lower().strip()

        if command in ['quit', 'exit']:
            print("\nGoodbye! Thanks for using the Database Agent.")
            return True

        elif command == 'help':
            self.print_welcome()
            return True

        elif command == 'stats':
            self.print_stats()
            return True

        elif command == 'new':
            self.start_new_thread()
            return True

        return False

    def print_stats(self):
        """Print session statistics"""
        stats = self.session_stats
        print(f"\nSession Statistics:")
        print(f"  Queries processed: {stats['queries_processed']}")
        print(f"  Successful queries: {stats['successful_queries']}")
        print(f"  Clarifications requested: {stats['clarifications_requested']}")
        if stats['queries_processed'] > 0:
            success_rate = (stats['successful_queries'] / stats['queries_processed']) * 100
            print(f"  Success rate: {success_rate:.1f}%")
        print(f"  Current thread: {self.current_thread_id}")
        print()

    def start_new_thread(self):
        """Start a new conversation thread"""
        timestamp = datetime.now().strftime("%H%M%S")
        self.current_thread_id = f"thread_{timestamp}"
        print(f"\nStarted new conversation thread: {self.current_thread_id}")
        print("Previous conversation context has been cleared.\n")

    def process_query(self, user_query: str) -> bool:
        """
        Process a user query.
        Returns True if query completed, False if waiting for clarification
        """
        try:
            self.session_stats["queries_processed"] += 1

            # Try to run the query
            result = self.agent.run_query(user_query, self.current_thread_id)

            # Check if we need clarification
            if self._needs_clarification(result):
                self.session_stats["clarifications_requested"] += 1
                print("\n" + ">" * 50)
                print("I need more information to proceed.")

                # Get the clarification message from the agent's response
                clarification_msg = self._extract_clarification_message(result)
                if clarification_msg:
                    print(f"Agent: {clarification_msg}")

                print(">" * 50)
                return False  # Waiting for user response

            # Query completed successfully or with error
            execution_result = result.get('execution_result', {})
            if execution_result.get('success'):
                self.session_stats["successful_queries"] += 1
                print(f"\nQuery completed successfully!")
            else:
                error_msg = execution_result.get('error', 'Unknown error')
                print(f"\nQuery failed: {error_msg}")

            return True  # Query completed

        except Exception as e:
            print(f"\nError processing query: {e}")
            logger.error(f"Query processing failed: {e}")
            return True  # Consider it completed (with error)

    def process_clarification(self, user_response: str) -> bool:
        """
        Process user clarification response.
        Returns True if query completed, False if more clarification needed
        """
        try:
            print(f"\nProcessing your clarification...")

            # Continue with user response
            result = self.agent.continue_with_user_response(
                user_response,
                self.current_thread_id
            )

            # Check if we still need more clarification
            if self._needs_clarification(result):
                print("\n" + ">" * 50)
                print("I need additional information:")

                clarification_msg = self._extract_clarification_message(result)
                if clarification_msg:
                    print(f"Agent: {clarification_msg}")

                print(">" * 50)
                return False  # Still waiting for more input

            # Query completed
            execution_result = result.get('execution_result', {})
            if execution_result.get('success'):
                self.session_stats["successful_queries"] += 1
                print(f"\n✅ Query completed successfully!")
            else:
                error_msg = execution_result.get('error', 'Unknown error')
                print(f"\nQuery failed: {error_msg}")

            return True  # Query completed

        except Exception as e:
            print(f"\nError processing clarification: {e}")
            logger.error(f"Clarification processing failed: {e}")
            return True  # Consider it completed (with error)

    @staticmethod
    def _needs_clarification(result: Dict) -> bool:
        """Check if the result indicates clarification is needed"""
        return (
                result.get('validation_result', {}).get('needs_clarification', False) or
                result.get('waiting_for_user', False) or
                not result.get('execution_result', {}).get('success', False) and
                not result.get('execution_result', {}).get('error')  # No error means it's waiting
        )

    @staticmethod
    def _extract_clarification_message(result: Dict) -> Optional[str]:
        """Extract clarification message from agent result"""
        messages = result.get('messages', [])
        if messages:
            # Get the last AI message
            for msg in reversed(messages):
                if hasattr(msg, 'content') and msg.content:
                    return msg.content
        return None

    def run(self) -> int:
        """Main console loop"""
        if not self.initialize_agent():
            return 1

        self.print_welcome()

        waiting_for_clarification = False

        try:
            while True:
                # Prompt based on current state
                if waiting_for_clarification:
                    prompt = "Your clarification: "
                else:
                    prompt = "You: "

                try:
                    user_input = input(prompt).strip()
                except (KeyboardInterrupt, EOFError):
                    print("\n\nGoodbye!")
                    break

                if not user_input:
                    continue

                # Handle commands (only when not waiting for clarification)
                if not waiting_for_clarification and self.handle_command(user_input):
                    if user_input.lower() in ['quit', 'exit']:
                        break
                    continue

                # Process user input
                if waiting_for_clarification:
                    # Handle clarification response
                    completed = self.process_clarification(user_input)
                    waiting_for_clarification = not completed
                else:
                    # Handle new query
                    completed = self.process_query(user_input)
                    waiting_for_clarification = not completed

                print()  # Add spacing

        except Exception as e:
            print(f"\nUnexpected error: {e}")
            logger.error(f"Console loop error: {e}")
            return 1

        return 0
import os

from langchain_openai import ChatOpenAI

from agent.nodes.operation_classifier import OperationClassifier
from agent.schema_extractor import SchemaExtractor


def main():
    api_key = os.getenv("OPENAI_API_KEY")
    llm = ChatOpenAI(api_key=api_key, model="gpt-4o-mini", temperature=0.1)
    test = OperationClassifier(llm)
    print(test.classify_operation("Get the number of users"))


if __name__ == "__main__":
    main()

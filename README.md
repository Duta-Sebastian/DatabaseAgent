# AI Database Agent

A sophisticated AI-powered database agent built with LangGraph and LangChain that converts natural language queries into executable SQL statements. The agent maintains conversation context, validates operations for safety, and provides intelligent clarification when needed.

## Architecture

The agent implements a multi-stage pipeline architecture using LangGraph workflows:

```
User Query → Operation Classification → Intent Analysis → Data Validation → SQL Generation → Execution
```

### Pipeline Stages

**Operation Classification**: Uses an LLM with database schema context to determine the type of operation (SELECT, INSERT, UPDATE, DELETE, COUNT, AGGREGATE) from natural language input.

**Intent Analysis**: Analyzes the classified operation to extract specific intent including required tables, columns, conditions, and relationships based on the database schema.

**Data Validation**: Validates whether sufficient information is available to proceed with SQL generation. Requests clarification from users when data is incomplete or potentially unsafe.

**SQL Generation**: Generates executable SQL queries from the validated intent analysis, leveraging schema knowledge to create syntactically correct statements.

**SQL Execution**: Safely executes generated SQL with proper error handling, transaction management, and result formatting.

## Core Features

**Conversation Context**: Maintains conversation history using LangGraph's MemorySaver, allowing for follow-up questions and context-aware responses.

**Schema Awareness**: Automatically extracts and utilizes database schema information to improve classification accuracy and SQL generation quality.

**Safety Validations**: Implements multi-layered safety checks, particularly for destructive operations like UPDATE and DELETE, ensuring proper WHERE clauses and preventing accidental data loss.

**Multi-Operation Support**: Handles the full spectrum of database operations from simple SELECT queries to complex aggregations and data modifications.

**Intelligent Clarification**: Requests additional information when user queries are ambiguous or lack required details, using conversational flow to gather missing data.

## Agent Components

### DatabaseAgent (LangGraph Orchestrator)

The main orchestrator class that defines the workflow graph and manages state transitions. It coordinates between different pipeline stages and handles conversation memory through configurable thread IDs.

### Operation Classifier

Analyzes natural language input against database schema to determine operation type. Uses carefully crafted prompts with schema context to achieve high classification accuracy even for ambiguous queries.

### Intent Analyzer

Processes classified operations to extract structured intent including:
- Target tables and their relationships
- Required columns for the operation
- Filtering conditions and constraints
- Aggregation requirements

### Data Validator

Implements operation-specific validation logic:
- **READ operations**: Ensures sufficient context for meaningful queries
- **INSERT operations**: Validates required field availability  
- **UPDATE operations**: Verifies proper record identification and new values
- **DELETE operations**: Enforces strict condition requirements for safety

### SQL Generator

Transforms validated intent into executable SQL using schema-aware generation. Handles complex queries including JOINs, subqueries, and aggregations as single statements.

### SQL Executor

Manages database interactions with proper error handling, transaction management, and result formatting. Differentiates between read and write operations for appropriate response handling.
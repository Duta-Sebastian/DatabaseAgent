from typing import Dict, List, Any
from sqlalchemy import inspect
from database.connection import engine


class SchemaExtractor:
    """
    Extract database schema information using SQLAlchemy
    """

    def __init__(self):
        self.inspector = inspect(engine)

    def get_schema_for_classification(self) -> str:
        """Get clean schema information for LLM classification"""

        schema_parts = ["DATABASE SCHEMA:"]

        # Get all table names
        table_names = self.inspector.get_table_names()
        table_names.remove("alembic_version")
        for table_name in table_names:
            schema_parts.append(f"\nTable: {table_name}")

            # Get columns
            columns = self.inspector.get_columns(table_name)
            for col in columns:
                col_info = f"  - {col['name']} ({col['type']})"
                if not col['nullable']:
                    col_info += " NOT NULL"
                schema_parts.append(col_info)

            # Get primary key
            pk = self.inspector.get_pk_constraint(table_name)
            if pk['constrained_columns']:
                schema_parts.append(f"  PRIMARY KEY: {', '.join(pk['constrained_columns'])}")

            # Get foreign keys
            fks = self.inspector.get_foreign_keys(table_name)
            for fk in fks:
                schema_parts.append(
                    f"  FOREIGN KEY: {', '.join(fk['constrained_columns'])} "
                    f"REFERENCES {fk['referred_table']}({', '.join(fk['referred_columns'])})"
                )

        return "\n".join(schema_parts)

    def get_tables(self) -> List[str]:
        """Get list of table names"""
        return self.inspector.get_table_names()

    def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """Get column information for a specific table"""
        columns = self.inspector.get_columns(table_name)
        return [
            {
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col["nullable"],
                "primary_key": False  # Will be set by get_table_info
            }
            for col in columns
        ]

    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get complete table information"""
        columns = self.get_table_columns(table_name)

        # Get primary keys
        pk = self.inspector.get_pk_constraint(table_name)
        pk_columns = pk.get('constrained_columns', [])

        # Mark primary key columns
        for col in columns:
            if col['name'] in pk_columns:
                col['primary_key'] = True

        # Get foreign keys
        fks = self.inspector.get_foreign_keys(table_name)
        foreign_keys = [
            {
                "columns": fk['constrained_columns'],
                "references_table": fk['referred_table'],
                "references_columns": fk['referred_columns']
            }
            for fk in fks
        ]

        return {
            "table_name": table_name,
            "columns": columns,
            "primary_keys": pk_columns,
            "foreign_keys": foreign_keys
        }

    def get_all_tables_info(self) -> Dict[str, Any]:
        """Get information for all tables"""
        tables_info = {}

        for table_name in self.get_tables():
            tables_info[table_name] = self.get_table_info(table_name)

        return tables_info
import kuzu
import os
import shutil

class LexGraph:
    """
    Manages the KùzuDB connection and enforces the strict graph schema.
    This acts as the Institutional Memory for the LEXGUARD system.
    """
    def __init__(self, db_path="lexguard_db", reset=False):
        self.db_path = db_path
        
        # Bulletproof DB reset logic
        if reset and os.path.exists(self.db_path):
            try:
                if os.path.isdir(self.db_path):
                    shutil.rmtree(self.db_path)
                else:
                    os.remove(self.db_path)
                print("🗑️ Old database wiped successfully.")
            except Exception as e:
                print(f"⚠️ Warning: Could not clear old database: {e}")
                
        # Initialize Database and Connection
        self.db = kuzu.Database(self.db_path)
        self.conn = kuzu.Connection(self.db)
        
        # Enforce Schema
        self._setup_schema()
        
    def _setup_schema(self):
        """
        Defines the strict structural boundaries of the knowledge graph.
        Executes each query independently to prevent 'table already exists' crashes.
        """
        schema_queries = [
            # --- NODES ---
            # 1. Entities: The 'Who' (Companies, Directors, Law Firms)
            """
            CREATE NODE TABLE Entity (
                name STRING, 
                label STRING, 
                normalized_name STRING, 
                PRIMARY KEY (name)
            )
            """,
            
            # 2. Sources: The Parent Contract (The 'Where')
            """
            CREATE NODE TABLE Source (
                doc_id STRING, 
                doc_type STRING, 
                filename STRING, 
                PRIMARY KEY (doc_id)
            )
            """,

            # 3. Clauses: The distinct text chunks
            """
            CREATE NODE TABLE Clause (
                clause_id STRING,
                text STRING,
                PRIMARY KEY (clause_id)
            )
            """,

            # --- EDGES (RELATIONSHIPS) ---
            # 4. Semantic Connections (Entity-to-Entity)
            "CREATE REL TABLE RELATES_TO (FROM Entity TO Entity, type STRING)",

            # 5. Structural Hierarchy (Document -> contains -> Clause)
            "CREATE REL TABLE CONTAINS_CLAUSE (FROM Source TO Clause)",

            # 6. Provenance (Entity -> extracted from -> Clause)
            "CREATE REL TABLE EXTRACTED_FROM (FROM Entity TO Clause)"
        ]

        for query in schema_queries:
            try:
                self.conn.execute(query)
            except Exception as e:
                # Ignore expected errors when tables already exist
                if "already exists" not in str(e).lower():
                    print(f"⚠️ Schema Error on query '{query.split('(')[0].strip()}': {e}")

    def execute(self, query, params=None):
        """
        Wrapper to safely execute Cypher queries.
        """
        return self.conn.execute(query, params if params else {})

# ==========================================
# GLOBAL INSTANCE EXPORT
# ==========================================
# Set reset=True ONLY when you want to wipe the database clean before a test run.
graph = LexGraph(reset=False)
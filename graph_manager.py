import kuzu
import os
import shutil

class LexGraph:
    def __init__(self, db_path="lexguard_db", reset=False):
        # Bulletproof reset logic for Windows
        if reset and os.path.exists(db_path):
            try:
                if os.path.isdir(db_path):
                    shutil.rmtree(db_path)
                else:
                    os.remove(db_path)
            except Exception as e:
                print(f"⚠️ Warning: Could not clear old database: {e}")
                
        self.db = kuzu.Database(db_path)
        self.conn = kuzu.Connection(self.db)
        self._setup_schema()
        
    # ... keep your _setup_schema and execute functions exactly the same ...

    def _setup_schema(self):
        """
        Defines the structure of our Institutional Memory.
        """
        try:
            # 1. Entities: The 'Who' (Companies, Directors, Law Firms)
            # normalized_name is key for merging 'Alpha Corp' and 'Alpha Corp Inc.'
            self.conn.execute("""
                CREATE NODE TABLE Entity (
                    name STRING, 
                    label STRING, 
                    normalized_name STRING, 
                    PRIMARY KEY (name)
                )
            """)

            # 2. Sources: The 'Where' (The specific Document)
            self.conn.execute("""
                CREATE NODE TABLE Source (
                    doc_id STRING, 
                    doc_type STRING, 
                    filename STRING, 
                    PRIMARY KEY (doc_id)
                )
            """)

            # 3. Relationships: Entity-to-Entity connections
            self.conn.execute("CREATE REL TABLE RELATES_TO (FROM Entity TO Entity, type STRING)")

            # 4. Provenance: Linking Entities back to their Source Document
            self.conn.execute("CREATE REL TABLE MENTIONED_IN (FROM Entity TO Source)")
            
            print("✅ Institutional Memory Schema Initialized.")
        except Exception as e:
            # Kuzu throws an error if tables already exist, which is fine
            if "already exists" not in str(e).lower():
                print(f"⚠️ Schema Error: {e}")

    def execute(self, query, params=None):
        return self.conn.execute(query, params if params else {})

# Initialize the global graph instance
# reset=True means it builds a fresh, clean DB every time we run this during testing
graph = LexGraph(reset=False)
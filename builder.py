from graph_manager import graph

def ingest_document_data(doc_meta, chunk_meta, entities, relationships):
    """
    Inserts extracted data into the KuzuDB graph using the strict Module Schema.
    Now properly links Entities directly to the specific Clause they were found in.
    """
    doc_id = doc_meta.get("id", "UNKNOWN_DOC")
    doc_type = doc_meta.get("type", "UNKNOWN_TYPE")
    filename = doc_meta.get("filename", "UNKNOWN_FILE")
    
    clause_id = chunk_meta.get("clause_id")
    clause_text = chunk_meta.get("text", "").replace('"', "'") # Escape quotes for Cypher

    try:
        # 1. UPSERT THE SOURCE DOCUMENT
        graph.execute(
            """
            MERGE (s:Source {doc_id: $doc_id})
            ON CREATE SET s.doc_type = $doc_type, s.filename = $filename
            """,
            {"doc_id": doc_id, "doc_type": doc_type, "filename": filename}
        )

        # 2. UPSERT THE CLAUSE NODE (Criticism 4 Resolution)
        graph.execute(
            """
            MERGE (c:Clause {clause_id: $clause_id})
            ON CREATE SET c.text = $text
            """,
            {"clause_id": clause_id, "text": clause_text}
        )

        # 3. LINK CLAUSE TO SOURCE (Document -> contains -> Clause)
        graph.execute(
            """
            MATCH (s:Source {doc_id: $doc_id})
            MATCH (c:Clause {clause_id: $clause_id})
            MERGE (s)-[:CONTAINS_CLAUSE]->(c)
            """,
            {"doc_id": doc_id, "clause_id": clause_id}
        )

        # 4. UPSERT ENTITIES & LINK TO SPECIFIC CLAUSE
        for ent in entities:
            ent_name = ent.get("name", "").strip()
            ent_label = ent.get("label", "Company").strip()
            
            if not ent_name:
                continue

            # Merge Entity
            graph.execute(
                """
                MERGE (e:Entity {name: $name})
                ON CREATE SET e.label = $label, e.normalized_name = $name
                """,
                {"name": ent_name, "label": ent_label}
            )

            # Link Entity directly to the Clause it was found in (EXTRACTED_FROM)
            graph.execute(
                """
                MATCH (e:Entity {name: $name})
                MATCH (c:Clause {clause_id: $clause_id})
                MERGE (e)-[:EXTRACTED_FROM]->(c)
                """,
                {"name": ent_name, "clause_id": clause_id}
            )

        # 5. UPSERT RELATIONSHIPS BETWEEN ENTITIES
        for rel in relationships:
            from_ent = rel.get("from", "").strip()
            to_ent = rel.get("to", "").strip()
            rel_type = rel.get("type", "RELATED_TO").strip()

            if not from_ent or not to_ent:
                continue

            graph.execute(
                """
                MATCH (a:Entity {name: $from_name})
                MATCH (b:Entity {name: $to_name})
                MERGE (a)-[r:RELATES_TO {type: $rel_type}]->(b)
                """,
                {"from_name": from_ent, "to_name": to_ent, "rel_type": rel_type}
            )

        print(f"Graph Insertion Complete for Clause {clause_id}.")

    except Exception as e:
        print(f"Error inserting data into graph: {e}")
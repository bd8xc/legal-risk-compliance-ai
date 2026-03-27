import re
from graph_manager import graph

def normalize(name):
    """
    Standardizes names so the graph can link 'Alpha Corp, Inc.' and 'Alpha Corp'.
    """
    n = name.lower().strip()
    # Remove punctuation
    n = re.sub(r'[^a-z0-9 ]', '', n)
    # Strip common corporate suffixes
    suffixes = [' inc', ' corp', ' ltd', ' llc', ' limited', ' corporation']
    for s in suffixes:
        if n.endswith(s):
            n = n[:-len(s)].strip()
    return n

def ingest_document_data(doc_meta, entities, relationships):
    """
    Links entities and relations from a document into the Knowledge Graph.
    """
    # 1. Register the Source Document
    graph.execute(
        "MERGE (s:Source {doc_id: $id}) SET s.doc_type = $type, s.filename = $fname",
        {"id": doc_meta['id'], "type": doc_meta['type'], "fname": doc_meta['filename']}
    )

    # 2. Add Entities and link to the Source (Provenance)
    for ent in entities:
        norm = normalize(ent['name'])
        
        # FIX: MERGE on the normalized name! This prevents duplicates.
        graph.execute(
            "MERGE (e:Entity {name: $norm}) SET e.label = $label, e.normalized_name = $norm",
            {"norm": norm, "label": ent['label']}
        )
        
        # Connect Entity -> Source using the normalized name
        graph.execute(
            "MATCH (e:Entity {name: $en}), (s:Source {doc_id: $sid}) MERGE (e)-[:MENTIONED_IN]->(s)",
            {"en": norm, "sid": doc_meta['id']}
        )

    # 3. Add Entity-to-Entity Relationships
    for rel in relationships:
        # FIX: We must also normalize the relationship source/target to match our nodes
        src_norm = normalize(rel['from'])
        tgt_norm = normalize(rel['to'])
        rel_type = rel['type'].upper().replace(" ", "_")
        
        graph.execute(
            f"MATCH (a:Entity {{name: $src}}), (b:Entity {{name: $tgt}}) "
            f"MERGE (a)-[r:RELATES_TO {{type: $rtype}}]->(b)",
            {"src": src_norm, "tgt": tgt_norm, "rtype": rel_type}
        )
    
    print(f"📈 Integrated {len(entities)} nodes from '{doc_meta['filename']}'")
from graph_manager import graph

print("="*60)
print("🔍 INSPECTING NEURO-SYMBOLIC KNOWLEDGE GRAPH")
print("="*60)

try:
    # 1. Document & Clause Hierarchy
    print("\n[1] 📄 DOCUMENTS & CLAUSES")
    doc_query = """
        MATCH (s:Source)-[:CONTAINS_CLAUSE]->(c:Clause) 
        RETURN s.filename, count(c) AS total_clauses
    """
    res = graph.execute(doc_query)
    while res.has_next():
        row = res.get_next()
        print(f"  -> File: {row[0]} | Segmented into {row[1]} distinct Clauses.")

    # 2. Total Entities Extracted
    print("\n[2] 🏢 EXTRACTED ENTITIES (By Type)")
    ent_query = """
        MATCH (e:Entity) 
        RETURN e.label, count(e) AS total
    """
    res = graph.execute(ent_query)
    while res.has_next():
        row = res.get_next()
        print(f"  -> {row[0]}: {row[1]} unique entities")

    # 3. The Relationships (The core of the graph)
    print("\n[3] 🔗 BUSINESS RELATIONSHIPS (Sample)")
    rel_query = """
        MATCH (a:Entity)-[r:RELATES_TO]->(b:Entity) 
        RETURN a.name, r.type, b.name 
        LIMIT 15
    """
    res = graph.execute(rel_query)
    if not res.has_next():
        print("  -> No relationships found yet.")
    while res.has_next():
        row = res.get_next()
        print(f"  [{row[0].title()}] --({row[1]})--> [{row[2].title()}]")

    # 4. Strict Provenance (Replacing the old MENTIONED_IN)
    print("\n[4] 📍 DATA PROVENANCE (Traceability Check)")
    prov_query = """
        MATCH (e:Entity)-[:EXTRACTED_FROM]->(c:Clause) 
        RETURN e.name, c.clause_id 
        LIMIT 10
    """
    res = graph.execute(prov_query)
    while res.has_next():
        row = res.get_next()
        print(f"  Entity '{row[0].title()}' was mathematically traced to -> {row[1]}")

    print("\n" + "="*60)

except Exception as e:
    print(f"\n❌ Error querying the graph: {e}")
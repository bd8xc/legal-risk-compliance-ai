from graph_manager import graph

print("🔍 Inspecting the Knowledge Graph...\n")

# Query to get all relationships and the documents they came from
query = """
    MATCH (a:Entity)-[r:RELATES_TO]->(b:Entity), (a)-[:MENTIONED_IN]->(s:Source)
    RETURN a.name, r.type, b.name, s.filename
"""

results = graph.execute(query)

if not results.has_next():
    print("Graph is empty!")
else:
    print(f"{'ENTITY 1':<25} | {'RELATIONSHIP':<18} | {'ENTITY 2':<25} | {'SOURCE DOCUMENT'}")
    print("-" * 90)
    while results.has_next():
        row = results.get_next()
        print(f"{row[0]:<25} | {row[1]:<18} | {row[2]:<25} | {row[3]}")
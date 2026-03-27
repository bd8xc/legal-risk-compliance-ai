from builder import ingest_document_data
from graph_manager import graph

print("--- INGESTING DOCUMENT 1: SEC FILING ---")
ingest_document_data(
    doc_meta={"id": "SEC_101", "type": "Governance", "filename": "alpha_corp_structure.pdf"},
    entities=[
        {"name": "Alpha Corp Inc.", "label": "Company"},
        {"name": "Beta Subsidiary LLC", "label": "Company"}
    ],
    relationships=[
        {"from": "Beta Subsidiary LLC", "to": "Alpha Corp Inc.", "type": "SUBSIDIARY_OF"}
    ]
)

print("\n--- INGESTING DOCUMENT 2: COURT DOCKET ---")
ingest_document_data(
    doc_meta={"id": "CRT_999", "type": "Litigation", "filename": "lawsuit_v_alpha.pdf"},
    entities=[
        {"name": "Alpha Corp", "label": "Company"}, # Notice the name is slightly different
        {"name": "Smith & Associates", "label": "LawFirm"}
    ],
    relationships=[
        {"from": "Smith & Associates", "to": "Alpha Corp", "type": "REPRESENTS"}
    ]
)

# --- THE TEST: Cross-Document Conflict Search ---
# We are asking the database: "Who represents the parent of Beta Subsidiary?"
print("\n🔍 Querying Institutional Memory for hidden connections...")
query = """
    MATCH (sub:Entity)-[:RELATES_TO {type: 'SUBSIDIARY_OF'}]->(parent:Entity)<-[:RELATES_TO {type: 'REPRESENTS'}]-(firm:Entity)
    RETURN sub.name, parent.name, firm.name
"""
results = graph.execute(query)

while results.has_next():
    row = results.get_next()
    print(f"\n🚨 CONFLICT FOUND:")
    print(f"Entity: {row[0]}")
    print(f"Is a subsidiary of: {row[1]}")
    print(f"Which is represented by: {row[2]}")
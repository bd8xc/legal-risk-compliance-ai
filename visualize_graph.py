import os
import webbrowser
import networkx as nx
from pyvis.network import Network
from graph_manager import graph

def generate_interactive_graph():
    print("Generating interactive Knowledge Graph visualization...")
    
    # Initialize PyVis network (Dark mode for a professional look)
    net = Network(height="800px", width="100%", bgcolor="#1E1E1E", font_color="white", directed=True)
    
    # 1. MAP THE HIERARCHY: Document -> Clause
    doc_query = """
        MATCH (s:Source)-[:CONTAINS_CLAUSE]->(c:Clause) 
        RETURN s.doc_id, c.clause_id
    """
    res = graph.execute(doc_query)
    while res.has_next():
        row = res.get_next()
        doc_id, clause_id = row[0], row[1]
        
        # Add Nodes
        net.add_node(doc_id, label=f"Document:\n{doc_id}", title="Source Document", color="#E03A3E", shape="box")
        net.add_node(clause_id, label=f"Clause:\n{clause_id.split('_')[-1]}", title=clause_id, color="#F58220")
        
        # Add Edge
        net.add_edge(doc_id, clause_id, title="CONTAINS_CLAUSE", color="#888888")

    # 2. MAP THE PROVENANCE: Entity -> Clause
    prov_query = """
        MATCH (e:Entity)-[:EXTRACTED_FROM]->(c:Clause) 
        RETURN e.name, e.label, c.clause_id
    """
    res = graph.execute(prov_query)
    while res.has_next():
        row = res.get_next()
        ent_name, ent_label, clause_id = row[0].title(), row[1], row[2]
        
        # Color code by entity type
        if ent_label == "Company": color = "#00B4D8"
        elif ent_label == "Person": color = "#9D4EDD"
        else: color = "#2DC653" # Location
            
        # Add Entity Node
        net.add_node(ent_name, label=ent_name, title=ent_label, color=color, shape="ellipse")
        
        # Add Edge
        net.add_edge(ent_name, clause_id, title="EXTRACTED_FROM", color="#555555", dashes=True)

    # 3. MAP THE BUSINESS LOGIC: Entity -> Entity
    rel_query = """
        MATCH (a:Entity)-[r:RELATES_TO]->(b:Entity) 
        RETURN a.name, r.type, b.name
    """
    res = graph.execute(rel_query)
    while res.has_next():
        row = res.get_next()
        ent_a, rel_type, ent_b = row[0].title(), row[1], row[2].title()
        
        # Make sure nodes exist (in case of detached edges)
        net.add_node(ent_a, label=ent_a, color="#00B4D8")
        net.add_node(ent_b, label=ent_b, color="#00B4D8")
        
        # Add thick, bright edge for business relationships
        net.add_edge(ent_a, ent_b, label=rel_type, title=rel_type, color="#FFD166", width=2)

    # Physics settings to make the graph spread out nicely
    net.barnes_hut(gravity=-8000, central_gravity=0.3, spring_length=150)
    
    # Save and open
    output_file = "lexguard_visual.html"
    net.save_graph(output_file)
    
    print(f"Success! Graph saved to {output_file}")
    
    # Automatically open in your default web browser
    filepath = "file://" + os.path.realpath(output_file)
    webbrowser.open(filepath)

if __name__ == "__main__":
    generate_interactive_graph()
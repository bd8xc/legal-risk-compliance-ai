# ldi/graph/engine.py
import re
import json
import os
import ollama
from typing import Dict, List
from pydantic import BaseModel, Field, field_validator
from neo4j import GraphDatabase

# ⚙️ Compile-time import directly from your configuration file
from ldi.config.ontology import ALLOWED_NODE_TYPES, ALLOWED_RELATIONSHIP_TYPES

# ─────────────────────────────────────────────────────────────────────
# ⚙️ SYSTEM MODE TOGGLE (THOUGHT-CONCEPT SWITCH)
# ─────────────────────────────────────────────────────────────────────
# True  = Unrestricted Thought-Concept Mode (Ingests EVERYTHING Ollama outputs)
# False = Strict Production Compliance Mode (Enforces strict ontology validation)
RELAXED_MODE = True 

# ─────────────────────────────────────────────────────────────────────
# 🔌 NEO4J DATABASE CONNECTION CONFIGURATION
# ─────────────────────────────────────────────────────────────────────
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# ─────────────────────────────────────────────────────────────────────
# 📋 RUNTIME PYDANTIC DATA INTERFACE SCHEMAS
# ─────────────────────────────────────────────────────────────────────

class Node(BaseModel):
    name: str
    type: str

    @field_validator("type")
    @classmethod
    def validate_node_type(cls, v: str) -> str:
        v_upper = v.strip().upper()
        # If relaxed mode is active, completely bypass the validation boundary check
        if not RELAXED_MODE and v_upper not in ALLOWED_NODE_TYPES:
            raise ValueError(f"Type '{v_upper}' rejected. Out of ontology boundaries.")
        return v_upper

class Relationship(BaseModel):
    source: str
    target: str
    type: str

    @field_validator("type")
    @classmethod
    def validate_edge_type(cls, v: str) -> str:
        v_upper = v.strip().upper().replace(" ", "_").replace("-", "_")
        # If relaxed mode is active, completely bypass the validation boundary check
        if not RELAXED_MODE and v_upper not in ALLOWED_RELATIONSHIP_TYPES:
            raise ValueError(f"Relationship '{v_upper}' rejected. Out of ontology boundaries.")
        return v_upper

class KnowledgeGraphExtraction(BaseModel):
    nodes: List[Node] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)

# ─────────────────────────────────────────────────────────────────────
# 🕵️ SCOUT & EXTRACTION ENGINE MODULES
# ─────────────────────────────────────────────────────────────────────

def run_scout_phase(full_text: str) -> Dict[str, str]:
    """Scouts preamble to isolate true corporate definitions natively."""
    aliases = {"LICENSOR": "UNKNOWN_LICENSOR", "LICENSEE": "UNKNOWN_LICENSEE"}
    preamble = full_text[:3000]
    
    licensor_match = re.search(r'([\w\s]{3,60?})(?:,\s+[^"\)]*)?[\("]hereinafter\s+referred\s+to\s+as\s+the\s+["\']Licensor["\']', preamble, re.IGNORECASE)
    licensee_match = re.search(r'([\w\s]{3,60?})(?:,\s+[^"\)]*)?[\("]hereinafter\s+referred\s+to\s+as\s+the\s+["\']Licensee["\']', preamble, re.IGNORECASE)
    
    if licensor_match:
        aliases["LICENSOR"] = licensor_match.group(1).strip().upper()
    if licensee_match:
        aliases["LICENSEE"] = licensee_match.group(1).strip().upper()
        
    print(f"[SCOUT PHASE] Target Map -> LICENSOR: {aliases['LICENSOR']} | LICENSEE: {aliases['LICENSEE']}")
    return aliases

def get_robust_system_prompt() -> str:
    """Generates prompt layout referencing the clean configuration arrays using categorized groups."""
    return (
        "You are a deterministic Legal Risk Ontology Parser. Your single task is to transform raw legal text into a structured JSON knowledge graph matching an explicit validation blueprint.\n\n"
        
        "=== CRITICAL SYSTEM RULES ===\n"
        "1. ABSOLUTE TRUTH: Only extract entities explicitly stated in the text. Never assume or extrapolate corporate hierarchies.\n"
        "2. NO PREAMBLE/POSTAMBLE: Output ONLY valid, raw JSON. Do not include markdown blocks or conversational text. Start with '{' and end with '}'.\n"
        "3. SKELETON INTEGRITY: Your output MUST contain both a 'nodes' key and a 'relationships' key.\n\n"
        
        "=== DYNAMIC ONTOLOGY SPECIFICATION ===\n"
        "You must select your fields EXCLUSIVELY from the categorized groups listed below:\n\n"
        
        "• ALLOWED NODE TYPES:\n"
        "  [Corporate Entities] 'COMPANY', 'PARTNERSHIP', 'FINANCIAL_INSTITUTION', 'INVESTMENT_FUND', 'NON_PROFIT_ENTITY'\n"
        "  [Human Actors]       'INDIVIDUAL', 'LAW_FIRM'\n"
        "  [Regulatory/Legal]   'GOVERNMENT_BODY', 'COURT', 'REGULATION', 'COMPLIANCE_FILING', 'SANCTION_RECORD', 'PENALTY_NOTICE', 'DISPUTE'\n"
        "  [Transactional Documents] 'CONTRACT', 'AMENDMENT', 'INSURANCE_POLICY', 'POWER_OF_ATTORNEY'\n"
        "  [Assets & Security]  'INTELLECTUAL_PROPERTY', 'ASSET', 'LIABILITY', 'SECURITY_INTEREST', 'DATA_REGISTRY', 'TRUST_ESTATE', 'OUTBOUND_SHIPMENT'\n\n"
        
        "• ALLOWED RELATIONSHIP TYPES:\n"
        "  [Corporate Ties]    'PARENT_COMPANY_OF', 'SUBSIDIARY_OF', 'JOINT_VENTURE_WITH', 'ACQUIRED_BY', 'SHAREHOLDER_OF', 'DIRECTOR_OF'\n"
        "  [Commercial Flows]  'CONTRACT_WITH', 'SUBCONTRACTOR_OF', 'SUPPLIES_TO', 'LICENSES_TO', 'PROCESSES_DATA_FOR'\n"
        "  [Financial Risk]    'INDEMNIFIED_BY', 'GUARANTEES_FINANCIALS_FOR', 'ASSIGNS_RIGHTS_TO', 'HOLDS_LIEN_ON', 'INSURES_AGAINST'\n"
        "  [Legal/Litigation]  'AMENDS_OFFICIALLY', 'GOVERNED_BY', 'VIOLATED_BY', 'INVESTIGATING', 'ENFORCED_BY', 'LITIGATING_AGAINST', 'REPRESENTS', 'ADJUDICATED_BY'\n"
        "  [Operational Control] 'TRACKS_MOVEMENT_OF'\n\n"
        
        "=== DATA NORMALIZATION RULES ===\n"
        "- Node 'name': Must be normalized to clean, strict UPPERCASE text strings without punctuation or business suffixes (e.g., convert 'Acme Corp, LLC' to 'ACME CORP').\n"
        "- Relationship Integrity: 'source' and 'target' values MUST match an extracted node 'name' string EXACTLY.\n"
        "- Edge Rejection: If a relationship type does not match the ALLOWED RELATIONSHIP TYPES exactly, or connects to generic actions, REJECT IT.\n\n"
        
        "=== ANCHOR EXAMPLE (FEW-SHOT VARIABLE TEMPLATE) ===\n"
        "Input text: 'COMPANY A signed an agreement with COMPANY B. Records show COMPANY A is a subsidiary of COMPANY C.'\n"
        "Output JSON:\n"
        "{\n"
        "  \"nodes\": [\n"
        "    {\"name\": \"COMPANY A\", \"type\": \"COMPANY\"},\n"
        "    {\"name\": \"COMPANY B\", \"type\": \"COMPANY\"},\n"
        "    {\"name\": \"COMPANY C\", \"type\": \"COMPANY\"}\n"
        "  ],\n"
        "  \"relationships\": [\n"
        "    {\"source\": \"COMPANY A\", \"target\": \"COMPANY B\", \"type\": \"CONTRACT_WITH\"},\n"
        "    {\"source\": \"COMPANY A\", \"target\": \"COMPANY C\", \"type\": \"SUBSIDIARY_OF\"}\n"
        "  ]\n"
        "}\n\n"
        "Execute parsing task natively for the following text chunk:"
    )

def extract_graph_from_chunk(chunk_text: str, aliases: Dict[str, str], chunk_idx: int = 1) -> KnowledgeGraphExtraction:
    """Executes the extraction pass and handles data execution context based on system mode flags."""
    system_prompt = get_robust_system_prompt()
    
    try:
        response = ollama.chat(
            model="llama3.2",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Extract data structure from this text block:\n\n{chunk_text}"}
            ],
            format=KnowledgeGraphExtraction.model_json_schema()
        )
        
        raw_json_content = response['message']['content']
        
        print(f"\n================ [ CHUNK {chunk_idx} ] ================")
        print(f"📡 [SYSTEM MODE: {'THOUGHT-CONCEPT (RELAXED)' if RELAXED_MODE else 'STRICT PRODUCTION'}]")
        print("=== RAW OLLAMA GRAPH OUTPUT ===")
        print(raw_json_content.strip())
        print("===============================================")
        
        data = json.loads(raw_json_content)
        
        GENERIC_BLACKLIST = {"AGREEMENT", "PLATFORM", "TERM", "CONTRACT", "CONFIDENTIAL INFORMATION", "THE AGREEMENT", "(PROPRIETOR)"}
        
        NODE_TYPE_FALLBACKS = {
            "SERVICE_PROVIDER": "COMPANY", "SERVICE PROVIDER": "COMPANY", "VENDOR": "COMPANY",
            "POSITION": "INDIVIDUAL", "RIGHTS": "CONTRACT", "PROVISIONS": "CONTRACT", "HALL_OF_RESIDENCE": "ASSET"
        }
        
        REL_TYPE_FALLBACKS = {
            "EMPLOYER_AS": "CONTRACT_WITH", "SERVICES_PROVIDED_BY": "CONTRACT_WITH", "COMPANY_NAME": "REPRESENTS",
            "TITLE": "REPRESENTS", "REPRESENTED_BY": "REPRESENTS", "RIGHTS_OF": "GOVERNED_BY",
            "PROVISIONS_RELATIONSHIP": "GOVERNED_BY", "HAS_LOCATION": "TRACKS_MOVEMENT_OF",
            "HAS_ASSET": "TRACKS_MOVEMENT_OF", "ISSUED_BY": "CONTRACT_WITH", "OWNED_BY": "PARENT_COMPANY_OF"
        }

        def clean_corporate_clutter(text_str: str) -> str:
            t = text_str.strip().upper()
            t = re.sub(r'^M/S\.?\s+', '', t)
            t = re.sub(r'\b(LLC|LTD|INC|CORP|PVT|PRIVATE|LIMITED|CO|COMPANY)\b', '', t)
            return re.sub(r'\s+', ' ', t).strip()

        # 🧼 Step 1: Process Nodes
        cleaned_nodes = []
        for node in data.get("nodes", []):
            raw_name = str(node.get("name", "")).strip().upper()
            type_str = str(node.get("type", "")).strip().upper()
            
            # Standard structural transformation layer (only executed in Production Mode)
            if not RELAXED_MODE:
                if any(x in type_str for x in ["INDIVID", "PERSON", "ACTOR", "ROLE", "TITLE", "HUMAN"]):
                    type_str = "INDIVIDUAL"
                elif any(x in type_str for x in ["COMP", "INSTITUT", "ORGANIZ", "VEND", "PROVID"]):
                    type_str = "COMPANY"
                elif any(x in type_str for x in ["BANK", "FINANC"]):
                    type_str = "FINANCIAL_INSTITUTION"
                elif any(x in type_str for x in ["LOCAT", "PROP", "FACIL", "RESID"]):
                    type_str = "ASSET"
                else:
                    type_str_norm = type_str.replace(" ", "_").replace("-", "_")
                    if type_str_norm in NODE_TYPE_FALLBACKS:
                        type_str = NODE_TYPE_FALLBACKS[type_str_norm]

            if raw_name in ["LICENSOR", "THE LICENSOR"]:
                raw_name = aliases["LICENSOR"]
            elif raw_name in ["LICENSEE", "THE LICENSEE"]:
                raw_name = aliases["LICENSEE"]
                
            name_str = clean_corporate_clutter(raw_name)
            
            if name_str in GENERIC_BLACKLIST or not name_str:
                continue

            cleaned_nodes.append({"name": name_str, "type": type_str})

        # Register valid nodes for integrity lookups
        valid_node_names = {n["name"] for n in cleaned_nodes}

        # 🧼 Step 2: Process Relationships
        cleaned_rels = []
        for rel in data.get("relationships", []):
            raw_src = str(rel.get("source", "")).strip().upper()
            raw_tgt = str(rel.get("target", "")).strip().upper()
            type_str = str(rel.get("type", "")).strip().upper()
            
            # Format spaces and syntax layouts cleanly
            type_str = type_str.replace(" ", "_").replace("-", "_")
            
            # Semantic keyword routing (only executed in Production Mode)
            if not RELAXED_MODE:
                if any(x in type_str for x in ["AGREE", "CONTR", "TERM", "PROVID", "SERV", "EMPLOY", "CLIENT"]):
                    type_str = "CONTRACT_WITH"
                elif any(x in type_str for x in ["SUPERV", "MANAG", "CHAIR", "DIRECT", "LEAD", "WARDEN", "PARTNER"]):
                    type_str = "DIRECTOR_OF"
                elif any(x in type_str for x in ["PAY", "RECEIV", "FINANC", "FUND", "COST"]):
                    type_str = "PROCESSES_DATA_FOR"
                elif any(x in type_str for x in ["OWN", "PARENT", "SUB", "HOST", "ACQUIR"]):
                    type_str = "PARENT_COMPANY_OF"
                else:
                    if type_str in REL_TYPE_FALLBACKS:
                        type_str = REL_TYPE_FALLBACKS[type_str]

            src_str = clean_corporate_clutter(raw_src)
            tget_str = clean_corporate_clutter(raw_tgt)

            if src_str in GENERIC_BLACKLIST or tget_str in GENERIC_BLACKLIST:
                continue
            
            # Structural Pointer Verification Gate
            if src_str not in valid_node_names or tget_str not in valid_node_names:
                continue

            cleaned_rels.append({"source": src_str, "target": tget_str, "type": type_str})

        data["nodes"] = cleaned_nodes
        data["relationships"] = cleaned_rels
        
        validated_data = KnowledgeGraphExtraction.model_validate(data)
        
        print("✅ EXTRACTION PROCESSING SELECTION:")
        print(f"  ├─ Nodes: {[(n.name, n.type) for n in validated_data.nodes]}")
        print(f"  └─ Edges: {[{'src': r.source, 'type': r.type, 'tgt': r.target} for r in validated_data.relationships]}")
        print("-" * 50)
        
        return validated_data
        
    except Exception as e:
        print(f"🚨 [GRAPH ENGINE ERROR] Chunk {chunk_idx} processing failed: {e}")
        print("-" * 50)
        return KnowledgeGraphExtraction(nodes=[], relationships=[])

# ─────────────────────────────────────────────────────────────────────
# 🌐 LIVE NEO4J DB WRITER CONNECTOR
# ─────────────────────────────────────────────────────────────────────
def write_graph_data_to_neo4j(graph_data: dict):
    """Writes the normalized knowledge graph dictionary structure into the active Neo4j instance."""
    nodes = graph_data.get("nodes", [])
    relationships = graph_data.get("relationships", [])
    
    if not nodes:
        return

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        with driver.session() as session:
            for node in nodes:
                name_str = node.get("name")
                type_str = node.get("type")
                safe_label = "".join([c for c in type_str if c.isalnum() or c == '_'])
                
                session.run(
                    "MERGE (n:Entity {name: $name}) SET n.type = $type",
                    name=name_str, type=type_str
                )
                if safe_label:
                    session.run(f"MATCH (n:Entity {{name: $name}}) SET n:{safe_label} RETURN n", name=name_str)
            
            for rel in relationships:
                src_str = rel.get("source")
                tgt_str = rel.get("target")
                rel_type = rel.get("type")
                safe_edge_label = "".join([c for c in rel_type if c.isalnum() or c == '_'])
                
                session.run(
                    f"MATCH (s:Entity {{name: $source}}), (t:Entity {{name: $target}}) "
                    f"MERGE (s)-[r:{safe_edge_label}]->(t)",
                    source=src_str, target=tgt_str
                )
        print(f"🧬 [NEO4J LIVE SYNC] Successfully committed {len(nodes)} nodes and {len(relationships)} edges.")
    finally:
        driver.close()
import json
import requests
import spacy
import difflib
import re
from builder import ingest_document_data

# ==========================================
# MODULE: NEURO-SYMBOLIC EXTRACTION ENGINE
# ==========================================
OLLAMA_MODEL = "qwen2.5:3b"
OLLAMA_API_URL = "http://localhost:11434/api/generate"
LLM_TIMEOUT = 30 

ENTITY_RELATIONSHIPS = {
    "ACQUIRES", "AFFILIATED_WITH", "AGENT_OF", "AGREES_WITH", "ASSIGNS_TO",
    "AUDITS", "BOARD_MEMBER_OF", "BORROWS_FROM", "CLIENT_OF", "COMPETES_WITH",
    "CONSULTANT_FOR", "CONTRACT_WITH", "DELIVERS_TO", "DEVELOPS_FOR", "DIRECTS",
    "DISTRIBUTES_FOR", "EMPLOYS", "FINANCES", "GUARANTEES", "HEADQUARTERED_IN",
    "INDEMNIFIES", "INFRINGES", "INSURES", "INVESTS_IN", "JOINT_VENTURE_WITH",
    "LEASES_TO", "LENDS_TO", "LICENSES_TO", "LOCATED_IN", "MANAGES",
    "MANUFACTURES_FOR", "MERGED_WITH", "OCCUPIES", "OWNS", "OWNS_IP",
    "PARENT_OF", "PARTNER_OF", "PAYS", "PROVIDES_SERVICES_TO", "RELATED_TO",
    "RENEWS_WITH", "RENTS_FROM", "REPRESENTS", "SHAREHOLDER_OF", "SUBCONTRACTS_TO",
    "SUBLEASES_TO", "SUBSIDIARY_OF", "SUPPLIES_TO", "TERMINATES", "USES_FOR",
    "VENDORS_TO", "WARRANTS_TO"
}

RULE_TEMPLATES = {
    "LEASES_TO": [r"{0}.{{1,50}}leases?.{{1,50}}to {1}", r"{1}.{{1,50}}leased? from {0}"],
    "SUBLEASES_TO": [r"{0}.{{1,50}}subleases?.{{1,50}}to {1}"],
    "RENTS_FROM": [r"{0}.{{1,50}}rents?.{{1,50}}from {1}"],
    "SUPPLIES_TO": [r"{0}.{{1,50}}supplies?.{{1,50}}to {1}", r"{0}.{{1,50}}supplier (?:of|for) {1}"],
    "SUBSIDIARY_OF": [r"{0}.{{1,50}}subsidiary of {1}", r"{1}.{{1,50}}parent (?:company )?of {0}"],
    "CONTRACT_WITH": [r"{0}.{{1,50}}agrees? to.*?with {1}", r"{0}.{{1,50}}contracts? with {1}", r"{0}.{{1,50}}entered into.*?with {1}"],
    "REPRESENTS": [r"{0}.{{1,50}}represents? {1}", r"{0}.{{1,50}}acting on behalf of {1}"],
    "LOCATED_IN": [r"{0}.{{1,50}}located (?:in|at) {1}", r"{0}.{{1,50}}situated (?:in|at) {1}"],
    "PROVIDES_SERVICES_TO": [r"{0}.{{1,50}}provides?.*?services? to {1}"],
    "INDEMNIFIES": [r"{0}.{{1,50}}indemnifies {1}", r"{0}.{{1,50}}shall indemnify {1}", r"{0}.{{1,50}}holds? harmless {1}"],
    "WARRANTS_TO": [r"{0}.{{1,50}}warrants? to {1}", r"{0}.{{1,50}}represents and warrants to {1}"],
    "GUARANTEES": [r"{0}.{{1,50}}guarantees? {1}", r"{0}.{{1,50}}acts? as guarantor for {1}"],
    "LICENSES_TO": [r"{0}.{{1,50}}licenses?.{{1,50}}to {1}", r"{0}.{{1,50}}grants a license to {1}"],
    "SUBCONTRACTS_TO": [r"{0}.{{1,50}}subcontracts?.{{1,50}}to {1}"],
    "MANAGES": [r"{0}.{{1,50}}manages? {1}", r"{0}.{{1,50}}acts as manager for {1}"],
    "PAYS": [r"{0}.{{1,50}}pays? {1}", r"{0}.{{1,50}}shall pay {1}", r"{0}.{{1,50}}remits payment to {1}"],
    "OWNS": [r"{0}.{{1,50}}owns? {1}", r"{0}.{{1,50}}owner of {1}"],
    "ACQUIRES": [r"{0}.{{1,50}}acquires? {1}", r"{0}.{{1,50}}purchases? {1}"],
    "MERGED_WITH": [r"{0}.{{1,50}}merges? with {1}", r"{0}.{{1,50}}merged into {1}"],
    "JOINT_VENTURE_WITH": [r"{0}.{{1,50}}joint venture with {1}"],
    "PARTNER_OF": [r"{0}.{{1,50}}partners? with {1}", r"{0}.{{1,50}}in partnership with {1}"],
    "EMPLOYS": [r"{0}.{{1,50}}employs? {1}", r"{0}.{{1,50}}employer of {1}"],
    "AGENT_OF": [r"{0}.{{1,50}}acts? as agent (?:for|of) {1}"],
    "AUDITS": [r"{0}.{{1,50}}audits? {1}", r"{0}.{{1,50}}auditor (?:for|of) {1}"],
    "INSURES": [r"{0}.{{1,50}}insures? {1}", r"{0}.{{1,50}}provides insurance to {1}"],
    "FINANCES": [r"{0}.{{1,50}}finances? {1}", r"{0}.{{1,50}}provides funding to {1}"],
    "LENDS_TO": [r"{0}.{{1,50}}lends? to {1}", r"{0}.{{1,50}}loaned to {1}"],
    "BORROWS_FROM": [r"{0}.{{1,50}}borrows? from {1}"],
    "OWNS_IP": [r"{0}.{{1,50}}owns (?:the )?(?:intellectual property|ip) (?:of|in) {1}"],
    "ASSIGNS_TO": [r"{0}.{{1,50}}assigns?.{{1,50}}to {1}", r"{0}.{{1,50}}transfers?.{{1,50}}to {1}"]
}

print("Loading NLP Model (en_core_web_sm)...")
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Error: spaCy model missing. Run: python -m spacy download en_core_web_sm")
    exit(1)

def flatten_text(text):
    return re.sub(r'\s+', ' ', text).strip()

def clean_llm_json(response_text, expect_list=False):
    try:
        if expect_list:
            match = re.search(r'\[.*\]', response_text, re.DOTALL)
            return json.loads(match.group(0)) if match else []
        else:
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            return json.loads(match.group(0)) if match else {}
    except Exception:
        return [] if expect_list else {}

def normalize_company(name):
    name = name.lower()
    name = re.sub(r'\b(ltd|limited|inc|corp|corporation|pvt|llc|co)\b\.?', '', name)
    return name.strip()

def resolve_entity(name, alias_map):
    if not isinstance(name, str): return name
    clean_name = flatten_text(name).lower()
    if clean_name.startswith("the "): clean_name = clean_name[4:]
        
    if clean_name in alias_map: return alias_map[clean_name]
        
    close_matches = difflib.get_close_matches(clean_name, alias_map.keys(), n=1, cutoff=0.8)
    if close_matches: return alias_map[close_matches[0]]
        
    return clean_name

def generate_alias_map(first_chunk_text):
    print("Running Scout Pass to resolve contract aliases...")
    first_chunk_text = flatten_text(first_chunk_text)
    prompt = f"""
    Identify the main parties and their roles (e.g., Lessor, Lessee, Bank).
    Return ONLY a valid JSON dictionary: {{"role": "exact company name"}}
    Text: {first_chunk_text}
    """
    try:
        payload = {"model": OLLAMA_MODEL, "prompt": prompt, "format": "json", "stream": False}
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=LLM_TIMEOUT)
        response.raise_for_status()
        
        raw_text = response.json().get("response", "{}")
        dynamic_map = clean_llm_json(raw_text, expect_list=False)
        
        expanded_map = {}
        if isinstance(dynamic_map, dict):
            for role, name in dynamic_map.items():
                clean_name = flatten_text(name).lower()
                expanded_map[role.lower()] = clean_name
                expanded_map[f"the {role.lower()}"] = clean_name
        return expanded_map
        
    except requests.exceptions.Timeout:
        print("Scout Pass Timeout: LLM took too long. Defaulting to empty map.")
        return {}
    except Exception as e:
        print(f"Scout Pass Warning (Defaulting to empty map): {e}")
        return {} 

def extract_entities_hybrid(text, dynamic_alias_map):
    text_flat = flatten_text(text)
    doc = nlp(text_flat)
    entities = []
    seen = set()
    text_lower = text_flat.lower()
    
    # 1. FORCED DICTIONARY OVERRIDE
    for role, actual_name in dynamic_alias_map.items():
        if role in text_lower or actual_name.lower() in text_lower:
            norm_name = normalize_company(actual_name)
            if norm_name not in seen:
                seen.add(norm_name)
                entities.append({
                    "name": actual_name, 
                    "label": "Company",
                    "normalized_name": norm_name
                })
    
    # 2. DETERMINISTIC SPACY EXTRACTION WITH JUNK FILTER
    junk_words = {
        "page", "schedule", "annexure", "article", "clause", "section", 
        "paragraph", "sba", "kwh", "btu", "party", "parties", "deposit", 
        "proportionate", "rupees", "amount", "herein", "witnesseth", "date",
        "definitions", "interpretations", "state", "law", "laws", "lien", "term"
    }
    roman_numeral_pattern = re.compile(r'^(?=[mdclxvi])m*(c[md]|d?c*)(x[cl]|l?x*)(i[xv]|v?i*)$')
    list_item_pattern = re.compile(r'^[a-z]\.\s+')

    for ent in doc.ents:
        if ent.label_ in ["ORG", "PERSON", "GPE"]:
            clean_name = flatten_text(ent.text).lower()
            
            if len(clean_name) <= 2: continue 
            if list_item_pattern.match(clean_name): continue 
            if any(junk in clean_name.split() for junk in junk_words): continue 
            if roman_numeral_pattern.match(clean_name): continue 
            if clean_name.isnumeric(): continue 
            
            resolved_name = resolve_entity(clean_name, dynamic_alias_map)
            norm_name = normalize_company(resolved_name)
            
            if norm_name not in seen:
                seen.add(norm_name)
                label = "Company" if ent.label_ == "ORG" else "Person" if ent.label_ == "PERSON" else "Location"
                entities.append({
                    "name": resolved_name, 
                    "label": label,
                    "normalized_name": norm_name
                })
                
    return entities

def extract_relationships_hybrid(text, entities):
    if len(entities) < 2: return [] 
    
    relationships = []
    # FIX: Use exact display names so builder.py can find the nodes in the database
    entity_names = [e["name"] for e in entities]
    
    text_lower = flatten_text(text).lower()
    
    # 1. ROBUST DETERMINISTIC REGEX ENGINE
    for i, ent1 in enumerate(entity_names):
        safe_ent1 = re.escape(ent1.lower())
        for ent2 in entity_names[i+1:]:
            safe_ent2 = re.escape(ent2.lower())
            
            for rel_type, templates in RULE_TEMPLATES.items():
                for template in templates:
                    pattern_ab = template.format(safe_ent1, safe_ent2)
                    if re.search(pattern_ab, text_lower):
                        relationships.append({"from": ent1, "to": ent2, "type": rel_type})
                        
                    pattern_ba = template.format(safe_ent2, safe_ent1)
                    if re.search(pattern_ba, text_lower):
                        relationships.append({"from": ent2, "to": ent1, "type": rel_type})

    # 2. LLM SEMANTIC REASONING (Fallback)
    prompt = f"""
    Extract business relationships between these entities ONLY: {entity_names}
    Use ONLY these relationship types: {list(ENTITY_RELATIONSHIPS)}
    Return ONLY a valid JSON object matching this schema: {{"relationships": [{{"from": "string", "to": "string", "type": "string"}}]}}
    Text: {text_lower}
    """
    try:
        payload = {"model": OLLAMA_MODEL, "prompt": prompt, "format": "json", "stream": False}
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=LLM_TIMEOUT)
        
        raw_text = response.json().get("response", "{}")
        llm_data = clean_llm_json(raw_text, expect_list=False)
        llm_rels = llm_data.get("relationships", [])
        relationships.extend(llm_rels)
    except Exception: 
        pass
        
    return relationships

def extract_from_text(chunk_meta, doc_meta, dynamic_alias_map):
    chunk_meta["text"] = flatten_text(chunk_meta["text"])
    
    valid_entities = extract_entities_hybrid(chunk_meta["text"], dynamic_alias_map)
    raw_relationships = extract_relationships_hybrid(chunk_meta["text"], valid_entities)
            
    valid_relationships = []
    seen_edges = set() 
    
    for rel in raw_relationships:
        if isinstance(rel, dict):
            # FIX: Do not normalize the relationship names here; builder.py needs exact matches
            rel_from = resolve_entity(rel.get('from', ''), dynamic_alias_map)
            rel_to = resolve_entity(rel.get('to', ''), dynamic_alias_map)
            
            rel_type = rel.get('type', 'RELATED_TO').upper()
            if rel_type not in ENTITY_RELATIONSHIPS:
                rel_type = "RELATED_TO" 
            
            if rel_from and rel_to and rel_from != rel_to:
                # Ensure the display names match our extracted valid_entities list
                valid_names = [e["name"] for e in valid_entities]
                if rel_from in valid_names and rel_to in valid_names:
                    
                    edge_sig = f"{rel_from}-{rel_type}-{rel_to}"
                    if edge_sig not in seen_edges:
                        seen_edges.add(edge_sig)
                        valid_relationships.append({
                            "from": rel_from, 
                            "to": rel_to, 
                            "type": rel_type
                        })
        
    if valid_entities or valid_relationships:
        ingest_document_data(doc_meta, chunk_meta, valid_entities, valid_relationships)
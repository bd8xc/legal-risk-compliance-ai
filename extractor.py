import json
import requests
import spacy
import difflib
from builder import ingest_document_data

# ---> UPGRADED THE ENGINE FOR SPEED AND RAM EFFICIENCY <---
OLLAMA_MODEL = "qwen2.5:3b"
OLLAMA_API_URL = "http://localhost:11434/api/generate"

print("⏳ Loading spaCy NLP model...")
nlp = spacy.load("en_core_web_sm")

def generate_alias_map(first_chunk_text):
    print("🕵️‍♂️ Running LLM Scout Pass to identify key parties...")
    
    prompt = f"""
    You are a strict legal data extractor. Read the preamble of this contract.
    Identify the main parties and their roles (e.g., Lessor, Lessee, Bank).
    
    CRITICAL RULES:
    1. Do NOT include blank lines or underscores (e.g., "___").
    2. Only extract the actual name (e.g., "shri smt", "state bank of india").
    3. Ensure generic roles are spelled correctly (lessee, lessor, bank).
    
    Return ONLY a valid JSON dictionary:
    {{
        "lessee": "company name",
        "lessor": "person name",
        "bank": "company name"
    }}

    Text:
    {first_chunk_text}
    """

    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "format": "json", "stream": False}

    try:
        response = requests.post(OLLAMA_API_URL, json=payload)
        response.raise_for_status()
        dynamic_map = json.loads(response.json().get("response", "{}"))
        print(f"🗺️ Scout Pass generated alias map: {dynamic_map}")
        
        expanded_map = {}
        if isinstance(dynamic_map, dict):
            for role, name in dynamic_map.items():
                clean_name = name.replace("_", "").strip() 
                expanded_map[role] = clean_name
                expanded_map[f"the {role}"] = clean_name
                expanded_map[f"{role}s"] = clean_name 
        return expanded_map
    except Exception as e:
        print(f"⚠️ Scout Pass failed: {e}")
        return {} 

import re

def extract_entities_with_spacy(text):
    """PURE PYTHON NER: Now with an aggressive Junk Filter."""
    doc = nlp(text)
    entities = []
    seen = set()
    
    # 🚫 The Blacklist: Words that are never valid entities
    junk_words = {"page", "schedule", "annexure", "article", "clause", "section", "paragraph", "sba", "kwh", "btu", "tneb"}
    
    # Regex to catch roman numerals (i, ii, iii, xiv, etc.)
    roman_numeral_pattern = re.compile(r'^(?=[mdclxvi])m*(c[md]|d?c*)(x[cl]|l?x*)(i[xv]|v?i*)$')

    for ent in doc.ents:
        if ent.label_ in ["ORG", "PERSON", "GPE"]:
            clean_name = ent.text.strip().lower()
            
            # THE FILTER GAUNTLET:
            if len(clean_name) <= 2: continue # Kill 1 or 2 letter words
            if any(junk in clean_name for junk in junk_words): continue # Kill blacklist words
            if roman_numeral_pattern.match(clean_name): continue # Kill Roman numerals
            if clean_name.isnumeric(): continue # Kill pure numbers
            
            if clean_name not in seen:
                seen.add(clean_name)
                label = "Company" if ent.label_ == "ORG" else "Person" if ent.label_ == "PERSON" else "Location"
                entities.append({"name": clean_name, "label": label})
                
    return entities

def extract_relationships_with_llm(text, entities):
    if not entities: return []
    print(f"🤖 Sending text to {OLLAMA_MODEL} for relationship parsing...")
    
    entity_names = [e["name"] for e in entities]
    
    # ---> KEPT YOUR ORIGINAL ROBUST PROMPT <---
    prompt = f"""
    Extract relationships between these specific entities ONLY: {entity_names}
    Relationships must have a "from" (entity name), "to" (entity name), and "type" (e.g., LEASES_TO).
    Return ONLY a valid JSON object matching this schema: {{"relationships": [{{"from": "string", "to": "string", "type": "string"}}]}}
    Text: {text}
    """
    try:
        payload = {"model": OLLAMA_MODEL, "prompt": prompt, "format": "json", "stream": False}
        response = requests.post(OLLAMA_API_URL, json=payload)
        return json.loads(response.json().get("response", "{}")).get("relationships", [])
    except Exception as e: 
        return []

def resolve_entity(name, alias_map):
    if not isinstance(name, str): return name
    clean_name = name.lower().strip()
    if clean_name.startswith("the "):
        clean_name = clean_name[4:]
        
    if clean_name in alias_map:
        return alias_map[clean_name]
        
    close_matches = difflib.get_close_matches(clean_name, alias_map.keys(), n=1, cutoff=0.8)
    if close_matches:
        matched_key = close_matches[0]
        return alias_map[matched_key]
        
    return clean_name

def extract_from_text(text, doc_meta, dynamic_alias_map):
    raw_entities = extract_entities_with_spacy(text)
    raw_relationships = extract_relationships_with_llm(text, raw_entities)
    
    valid_entities = []
    for ent in raw_entities:
        ent_name = resolve_entity(ent.get('name', ''), dynamic_alias_map)
        ent_label = ent.get('label', 'Company')
        if ent_name:
            valid_entities.append({"name": ent_name, "label": ent_label})
            
    valid_relationships = []
    for rel in raw_relationships:
        if isinstance(rel, dict):
            rel_from = resolve_entity(rel.get('from', ''), dynamic_alias_map)
            rel_to = resolve_entity(rel.get('to', ''), dynamic_alias_map)
            rel_type = rel.get('type', 'RELATED_TO')
            
            if rel_from and rel_to:
                valid_relationships.append({
                    "from": rel_from, 
                    "to": rel_to, 
                    "type": rel_type
                })
        
    print(f"✅ Extracted {len(valid_entities)} entities and {len(valid_relationships)} valid relationships.")
    
    if valid_entities or valid_relationships:
        ingest_document_data(doc_meta, valid_entities, valid_relationships)
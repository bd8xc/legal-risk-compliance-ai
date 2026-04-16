"""
synthetic_graph.py
==================
Populates the KuzuDB knowledge graph with a synthetic corporate network
for testing the Conflict of Interest Agent.

Network spec (from LEXGUARD implementation plan):
  - 10 companies
  - 5 vendors
  - 3 law firms
  - Simulated litigation relationships

Run once before running tests:
    python synthetic_graph.py [--reset]
"""

import sys
import os
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
_KG_ROOT = os.path.join(_HERE, "..", "kg",
                        "legal-risk-compliance-ai-feature-knowledge-graph-ingestion")
if os.path.isdir(_KG_ROOT):
    sys.path.insert(0, _KG_ROOT)


COMPANIES = [
    "Alpha Corp",
    "Beta Technologies",
    "Gamma Holdings",
    "Delta Solutions",
    "Epsilon Ventures",
    "Zeta Industries",
    "Eta Partners",
    "Theta Capital",
    "Iota Systems",
    "Kappa Group",
]

VENDORS = [
    "Vendor One Ltd",
    "Vendor Two Inc",
    "Vendor Three LLC",
    "Vendor Four GmbH",
    "Vendor Five Co",
]

LAW_FIRMS = [
    "LawFirm Alpha & Associates",
    "LawFirm Beta Partners LLP",
    "LawFirm Gamma Solicitors",
]

# (from_entity, to_entity, relationship_type)
RELATIONSHIPS = [
    # Corporate structure
    ("Beta Technologies",    "Gamma Holdings",   "SUBSIDIARY_OF"),
    ("Delta Solutions",      "Gamma Holdings",   "SUBSIDIARY_OF"),
    ("Epsilon Ventures",     "Kappa Group",      "SUBSIDIARY_OF"),
    ("Vendor One Ltd",       "Gamma Holdings",   "AFFILIATED_WITH"),
    ("Vendor Two Inc",       "Kappa Group",      "AFFILIATED_WITH"),

    # Litigation  ← adversarial, triggers HIGH severity
    ("Gamma Holdings",       "Alpha Corp",       "LITIGATING_AGAINST"),
    ("Iota Systems",         "Eta Partners",     "LITIGATING_AGAINST"),

    # Competition  ← MEDIUM severity
    ("Delta Solutions",      "Alpha Corp",       "COMPETES_WITH"),
    ("Zeta Industries",      "Theta Capital",    "COMPETES_WITH"),

    # Legal representation
    ("LawFirm Alpha & Associates", "Alpha Corp",        "REPRESENTS"),
    ("LawFirm Alpha & Associates", "Gamma Holdings",    "REPRESENTS"),  # same firm!
    ("LawFirm Beta Partners LLP",  "Beta Technologies", "REPRESENTS"),
    ("LawFirm Gamma Solicitors",   "Iota Systems",      "REPRESENTS"),

    # Contract relationships (neutral – needed for traversal)
    ("Alpha Corp",       "Vendor One Ltd",  "CONTRACT_WITH"),
    ("Beta Technologies","Vendor Three LLC", "CONTRACT_WITH"),
    ("Theta Capital",    "Vendor Four GmbH", "CONTRACT_WITH"),

    # Board member / director overlap  ← LOW severity
    ("Kappa Group",  "Alpha Corp",    "SHARED_DIRECTOR"),

    # Partner chains
    ("Vendor Five Co", "Eta Partners", "PARTNER_OF"),
]


def seed(db_path: str = "lexguard_db", reset: bool = False):
    try:
        from graph_manager import LexGraph  # type: ignore
    except ImportError:
        print("ERROR: graph_manager.py not found. Check that _KG_ROOT is correct.")
        sys.exit(1)

    g = LexGraph(db_path=db_path, reset=reset)

    all_entities = (
        [(name, "Company")  for name in COMPANIES]
        + [(name, "Vendor")   for name in VENDORS]
        + [(name, "LawFirm")  for name in LAW_FIRMS]
    )

    print(f"Seeding {len(all_entities)} entity nodes…")
    for name, label in all_entities:
        g.execute(
            "MERGE (e:Entity {name: $name}) ON CREATE SET e.label = $label, e.normalized_name = $name",
            {"name": name, "label": label},
        )

    print(f"Seeding {len(RELATIONSHIPS)} relationships…")
    ok = 0
    for from_e, to_e, rel_type in RELATIONSHIPS:
        try:
            g.execute(
                "MATCH (a:Entity {name: $a}) MATCH (b:Entity {name: $b}) "
                "MERGE (a)-[r:RELATES_TO {type: $t}]->(b)",
                {"a": from_e, "b": to_e, "t": rel_type},
            )
            ok += 1
        except Exception as exc:
            print(f"  ⚠ Skipped ({from_e} → {to_e} [{rel_type}]): {exc}")

    print(f"Done. {ok}/{len(RELATIONSHIPS)} relationships inserted into '{db_path}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed synthetic LEXGUARD graph")
    parser.add_argument("--db",    default="lexguard_db", help="Path to KuzuDB database")
    parser.add_argument("--reset", action="store_true",   help="Wipe DB before seeding")
    args = parser.parse_args()
    seed(db_path=args.db, reset=args.reset)

# LEXGUARD Conflict of Interest Agent

Deterministic graph-based Conflict of Interest (COI) analysis for legal risk pipelines.

This repository implementation is designed as a production-safe component in a multi-agent legal risk workflow. The COI agent does not use an LLM for decision logic. It uses bounded graph traversal over a Kuzu-backed knowledge graph and returns auditable evidence paths plus scalar risk outputs.

## Table of contents

1. Overview
2. Why this exists
3. Core capabilities
4. Repository map
5. COI data flow
6. Risk model and traversal behavior
7. Entity resolution behavior
8. Output contract and LexState integration
9. Skip semantics and safety guarantees
10. Performance guards and scaling behavior
11. Setup and local development
12. Usage examples
13. Testing strategy
14. Troubleshooting
15. Extension guide
16. Known limitations

## Overview

The COI agent detects direct and indirect adversarial relationships between contract parties by traversing entity links in a knowledge graph.

Typical pattern detected:

Client -> CONTRACT_WITH -> Vendor -> SUBSIDIARY_OF -> Parent -> LITIGATING_AGAINST -> Client

Without graph traversal this conflict usually remains invisible in raw contract text.

This implementation is intentionally deterministic:

- Fixed maximum traversal depth.
- Explicit relationship scoring map.
- Explicit skip reasons when checks cannot be trusted.
- Repeatable outputs for identical inputs.

## Why this exists

Downstream risk scoring and litigation prediction depend on two classes of COI outputs:

- Scalar signal for models and rules: conflict_flag, conflict_severity.
- Explainable evidence for legal audit: graph_results, conflict_path_details, summaries.

This project separates those concerns so downstream components do not need to parse internal structures to consume the scalar signal.

## Core capabilities

1. Deterministic BFS traversal with a configurable hop cap (default 3).
2. Relationship-aware severity scoring with high/medium/low tiers.
3. Entity canonicalization with confidence scoring.
4. Path deduplication preserving distinct relationship sequences.
5. Structured skip reasons for unresolved entities or unavailable graph.
6. Run metadata for auditability and operational monitoring.
7. Performance caps for pairwise expansion and path collection.
8. LangGraph/LexState-compatible node update payload.

## Repository map

Primary files:

- [conflict_agent.py](conflict_agent.py): core engine, scoring, traversal, resolver, report model, LangGraph node adapter.
- [ldi/conflict_detection/conflict_rules.py](ldi/conflict_detection/conflict_rules.py): wrapper functions used by the LDI layer.
- [ldi/schemas/outputs.py](ldi/schemas/outputs.py): typed shared output state contract.
- [synthetic_graph.py](synthetic_graph.py): synthetic graph seeding utility for test data.
- [tests/test_conflict_agent.py](tests/test_conflict_agent.py): focused COI regression tests.

## COI data flow

High-level flow:

1. Input arrives with doc_id, client_entity, counterparty_entity, optional additional_entities.
2. Input entity names are validated and normalized.
3. Graph health check is validated at agent startup.
4. Required entities are resolved to canonical graph names with confidence scores.
5. BFS runs between resolved client and resolved counterparty.
6. Optional pairwise BFS runs across additional resolved entities under configured caps.
7. Candidate paths are scored and sorted.
8. Report is emitted with scalar outputs, explainable path details, skip metadata, and run metadata.

## Risk model and traversal behavior

### Severity tiers and relationship scores

The highest scored relationship along a path determines path severity.

Current relationship score map:

- High:
  - LITIGATING_AGAINST = 1.0
  - DISPUTE_WITH = 0.9
  - SUING = 0.9
- Medium:
  - COMPETES_WITH = 0.6
  - SUBSIDIARY_OF = 0.5
  - PARENT_OF = 0.5
  - AFFILIATED_WITH = 0.4
- Low:
  - SHARED_DIRECTOR = 0.3
  - BOARD_MEMBER_OF = 0.2

### Traversal relationship scope

The BFS traverses a broader relationship set than adversarial-only edges, including neutral bridge edges such as PARTNER_OF and CONTRACT_WITH. This allows conflict discovery through indirect chains while still requiring adversarial evidence for conflict classification.

### Deduplication strategy

Path dedup uses:

- Node sequence
- Relationship sequence

This preserves semantically different paths that share the same nodes but differ in legal meaning due to different edge types.

### Seen-set strategy

Traversal tracks visited states as (node, depth), not node-only, preventing premature pruning of potentially stronger paths discovered at different depths.

## Entity resolution behavior

Resolution algorithm:

1. Exact graph entity match: confidence 1.0.
2. Rapidfuzz fuzzy match (if available): confidence score/100 with a floor threshold.
3. difflib fallback: accepted above threshold with conservative confidence 0.5.

Key constants:

- ENTITY_RESOLUTION_MIN_CONFIDENCE = 0.75

The threshold is conservative for legal contexts because incorrect canonicalization can be more harmful than skipping analysis.

## Output contract and LexState integration

Primary output method:

- ConflictReport.to_lex_state_update()

Returns fields including:

- graph_results: full structured report payload.
- conflict_detected: boolean indicator.
- conflict_flag: integer 0/1 for downstream model features.
- conflict_severity: string enum value.
- conflict_paths: human-readable path descriptions.
- conflict_path_details: structured per-path payload.
- skipped_reason: typed skip reason or null.
- unresolved_entities: list of unresolved required entities.
- resolution_confidence: minimum confidence across resolved entities.
- run_metadata: execution metadata for audit/ops.

Schema definitions live in [ldi/schemas/outputs.py](ldi/schemas/outputs.py).

Integration wrappers live in [ldi/conflict_detection/conflict_rules.py](ldi/conflict_detection/conflict_rules.py).

## Skip semantics and safety guarantees

Conflict_flag alone must not be interpreted as safe-to-proceed when skipped_reason is non-null.

Typed skip reasons:

- entity_resolution_failed
  - Trigger: client or counterparty cannot be resolved above threshold.
  - Includes unresolved_entities list.
- graph_unavailable
  - Trigger: graph connectivity/health check fails.

Operational rule:

- If skipped_reason is set, downstream orchestration should treat COI output as indeterminate and route for fallback handling or review.

## Performance guards and scaling behavior

Two guards protect runtime and memory under dense graphs or high entity counts.

1. Pairwise expansion cap

- MAX_ADDITIONAL_PAIRS = 10
- Pair candidates are sorted by combined entity confidence before capping.

2. Path collection cap

- MAX_PATHS_COLLECTED = 500
- Applies during BFS collection to avoid unbounded growth.

Run metadata reports:

- pairwise_pairs_checked
- pairwise_pairs_total
- paths_found
- paths_capped
- entities_examined
- duration_ms
- max_hops_used
- graph_entity_count

## Setup and local development

### Prerequisites

- Python 3.9+
- Kuzu-compatible environment

### Environment

If using the local workspace venv pattern in this repository:

Windows PowerShell:

```powershell
.\capstone\Scripts\python.exe -m pip install -U pip
.\capstone\Scripts\python.exe -m pip install kuzu rapidfuzz pytest
```

If rapidfuzz is not installed, the resolver falls back to difflib.

### Seed synthetic graph data

```powershell
.\capstone\Scripts\python.exe synthetic_graph.py --reset
```

## Usage examples

### Standalone agent usage

```python
from conflict_agent import ConflictOfInterestAgent

agent = ConflictOfInterestAgent(db_path="lexguard_db")

report = agent.run(
    doc_id="CONTRACT_007",
    client_entity="Alpha Corp",
    counterparty_entity="Beta Technologies",
    additional_entities=["LawFirm Alpha & Associates"],
)

print(report.conflict_flag)
print(report.conflict_severity.value)
print(report.summary())
print(report.to_lex_state_update())
```

### LangGraph-style node usage

```python
from conflict_agent import conflict_agent_node

state = {
    "doc_id": "DOC_001",
    "entities": {
        "client_entity": "Alpha Corp",
        "counterparty_entity": "Beta Technologies",
        "all_entities": ["Gamma Holdings", "LawFirm Alpha & Associates"],
    },
}

update = conflict_agent_node(state)
state.update(update)
```

### LDI wrapper usage

```python
from ldi.conflict_detection.conflict_rules import run_conflict_check

update = run_conflict_check(
    doc_id="DOC_001",
    client_entity="Alpha Corp",
    counterparty_entity="Beta Technologies",
    additional_entities=["Gamma Holdings"],
)
```

## Testing strategy

Focused COI regression suite:

- [tests/test_conflict_agent.py](tests/test_conflict_agent.py)

Covers:

1. Dedup by nodes + relationship sequence.
2. SHARED_DIRECTOR low-severity scoring.
3. Typed skip outputs for unresolved entities.
4. Separation of conflict_flag and graph_results.
5. PARTNER_OF traversability with adversarial edge requirement.
6. Pairwise expansion cap behavior.
7. Graph-unavailable skip behavior.
8. Seen-set node+depth behavior.
9. Relationship-property explainability path formatting.
10. No-conflict summary clarity.

Run:

```powershell
.\capstone\Scripts\python.exe -m pytest tests/test_conflict_agent.py -q
```

If pytest is unavailable:

```powershell
.\capstone\Scripts\python.exe -m py_compile conflict_agent.py ldi/schemas/outputs.py ldi/conflict_detection/conflict_rules.py tests/test_conflict_agent.py
```

## Troubleshooting

### Error: kuzu has no attribute Database

Cause: incompatible kuzu package/runtime mix.

Action:

- Reinstall/align kuzu in the active environment.
- Confirm interpreter path matches expected environment.

### Error: pytest module not found

Action:

- Install pytest into active environment:
  - .\capstone\Scripts\python.exe -m pip install pytest

### Frequent skip_reason = entity_resolution_failed

Action:

- Improve upstream entity extraction quality.
- Add canonical aliases into graph entities.
- Tune ENTITY_RESOLUTION_MIN_CONFIDENCE only with controlled evaluation.

## Extension guide

Safe extension points:

1. Add relationship types:
   - Update RELATIONSHIP_SCORES if adversarial.
   - Update TRAVERSABLE_RELATIONSHIPS if traversable.
2. Add legal metadata fields:
   - Extend LEGAL_RELATIONSHIP_PROPERTIES and graph query projection.
3. Adjust scale controls:
   - MAX_ADDITIONAL_PAIRS
   - MAX_PATHS_COLLECTED
4. Add policy hooks:
   - Build downstream orchestrator logic that gates on skipped_reason and resolution_confidence.

## Known limitations

1. Conflict quality depends on graph freshness and entity extraction quality.
2. Relationship metadata extraction supports selected legal fields only.
3. Pairwise cap may omit lower-confidence cross-entity paths by design.
4. Resolver confidence is heuristic and should be calibrated against representative data.
5. This component is deterministic and explainable, but not a substitute for legal counsel.

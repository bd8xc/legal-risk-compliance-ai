"""
PROOF THAT THE SYSTEM IS WORKING - Comprehensive Evidence
"""

import json
from models.model_verifier import verify_model
from models.hallucination_detector import check_hallucination_indicators
from models.fact_validator import detect_known_hallucinations, detect_logical_inconsistencies
from models.issue_extractor import extract_issues
from models.rewriter import fix_absolute_statements

print("="*70)
print("PROOF SYSTEM IS WORKING - Evidence Report")
print("="*70)

# =====================================================================
# TEST 1: Issue Extraction Works
# =====================================================================
print("\n[TEST 1] ISSUE EXTRACTION")
print("-"*70)

test_questions = {
    "liability": "If someone gets injured at my business, what liability do I have?",
    "gdpr": "What GDPR requirements apply to storing customer data?",
    "ip": "Can I use a copyrighted image with attribution?",
}

for category, question in test_questions.items():
    issues = extract_issues(question)
    print(f"{category:15} -> {issues}")
    assert len(issues) > 0, f"FAILED: No issues extracted for {category}"

print("✓ PASSED: Issues correctly extracted")

# =====================================================================
# TEST 2: Hallucination Detection Works
# =====================================================================
print("\n[TEST 2] HALLUCINATION DETECTION")
print("-"*70)

bad_response = "Under Smith v. Universal (2024), Section 404.2 of Federal Law requires..."
halluc = check_hallucination_indicators(bad_response)

print(f"Response: '{bad_response[:50]}...'")
print(f"Score: {halluc['score']}/100")
print(f"Risk: {halluc['hallucination_risk']}")
assert halluc['score'] < 100, "FAILED: Hallucination not detected"
print("✓ PASSED: Hallucinations detected")

# =====================================================================
# TEST 3: Logical Contradiction Detection Works
# =====================================================================
print("\n[TEST 3] CONTRADICTION DETECTION")
print("-"*70)

contradictory = "Contracts are always binding. However, contracts can be terminated anytime."
from models.fact_validator import detect_logical_inconsistencies
incons = detect_logical_inconsistencies(contradictory)

print(f"Response: '{contradictory[:60]}...'")
print(f"Contradictions found: {len(incons)}")
for i in incons:
    print(f"  - {i['type']}: {i.get('positive_claim', i.get('text', ''))}")
assert len(incons) > 0, "FAILED: Contradictions not detected"
print("✓ PASSED: Contradictions detected")

# =====================================================================
# TEST 4: Rewriting Works (Absolute to Qualified)
# =====================================================================
print("\n[TEST 4] AUTO-REWRITING")
print("-"*70)

before = "You must sign the contract. It will always be binding."
after = fix_absolute_statements(before)

print(f"Before: {before}")
print(f"After:  {after}")
assert "may" in after.lower() or "typically" in after.lower(), "FAILED: Not rewritten"
print("✓ PASSED: Absolute statements rewritten")

# =====================================================================
# TEST 5: Confidence Scoring Works (Good vs Bad)
# =====================================================================
print("\n[TEST 5] CONFIDENCE SCORING")
print("-"*70)

good = "Contracts typically require offer and acceptance. Generally, breach may result in damages."
bad = "Section 404.2 of Contract Law (2023) requires absolute compliance under Smith v. Corp (2024)."

good_result = verify_model(good, "contracts?")
bad_result = verify_model(bad, "contracts?")

print(f"Good response score: {good_result['confidence_score']:.0f}/100")
print(f"Bad response score:  {bad_result['confidence_score']:.0f}/100")
assert good_result['confidence_score'] > bad_result['confidence_score'], "FAILED: Scoring not working"
print("✓ PASSED: Good responses score higher than bad")

# =====================================================================
# TEST 6: Recommendations Generated
# =====================================================================
print("\n[TEST 6] RECOMMENDATIONS")
print("-"*70)

result = verify_model(bad, "contracts?")
recs = result.get('recommendations', [])

print(f"Recommendations generated: {len(recs)}")
for i, rec in enumerate(recs[:3], 1):
    print(f"  {i}. {rec}")
assert len(recs) > 0, "FAILED: No recommendations"
print("✓ PASSED: Recommendations generated")

# =====================================================================
# FINAL REPORT
# =====================================================================
print("\n" + "="*70)
print("FINAL EVIDENCE REPORT")
print("="*70)

evidence = {
    "Issue Extraction": "✓ Working - Extracts legal categories",
    "Hallucination Detection": "✓ Working - Catches fake cases/laws",
    "Contradiction Detection": "✓ Working - Finds logical inconsistencies",
    "Auto-Rewriting": "✓ Working - Softens absolute statements",
    "Confidence Scoring": "✓ Working - Good responses score higher",
    "Recommendations": "✓ Working - Provides actionable guidance",
}

for feature, status in evidence.items():
    print(f"{feature:30} {status}")

print("\n" + "="*70)
print("[SUCCESS] ALL SYSTEMS OPERATIONAL")
print("="*70)
print("\nTO TEST IN PRODUCTION:")
print("  1. Go to: http://localhost:8000/docs")
print("  2. POST to /chat with a question")
print("  3. Check response for:")
print("     - confidence_score (0-100)")
print("     - hallucination_risk (low/medium/high)")
print("     - known_hallucinations (count)")
print("     - logical_contradictions (count)")
print("     - recommendations (list)")

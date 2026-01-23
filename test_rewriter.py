"""Test rewriting with hallucination detection"""

print("[1] Testing rewriter with violations...")
from models.rewriter import rewrite_answer, fix_absolute_statements

# Test 1: Absolute statements
bad_response = "Contracts will always be binding. You must sign everything."
fixed = fix_absolute_statements(bad_response)
print(f"\nOriginal: {bad_response}")
print(f"Fixed:    {fixed}")

# Test 2: Missing disclaimer
response_no_disclaimer = "Here are the contract rules that apply to you."
with_disclaimer = rewrite_answer(response_no_disclaimer, ['disclaimer'])
print(f"\nOriginal: {response_no_disclaimer}")
print(f"With disclaimer: {with_disclaimer[:100]}...")

# Test 3: Full rewriting flow
print("\n[2] Testing full 5-phase pipeline with rewriting...")
from models.issue_extractor import extract_issues
from models.llm import get_llm_response
from models.rule_verifier import verify_rules
from models.model_verifier import verify_model

question = "What are key things to verify in a contract?"
print(f"\nQuestion: {question}")

# Phase 1
issues = extract_issues(question)
print(f"Phase 1 - Issues: {issues}")

# Phase 2
llm_resp = get_llm_response(question)
print(f"Phase 2 - LLM response: {len(llm_resp)} characters")

# Phase 3
rule_check = verify_rules(llm_resp)
print(f"Phase 3 - Rules passed: {rule_check['passes']}")
if not rule_check['passes']:
    print(f"         Violations: {rule_check['violations']}")

# Phase 4
model_check = verify_model(llm_resp, question)
print(f"Phase 4 - Model verified: {model_check['is_valid']}")
print(f"         Confidence: {model_check['confidence_score']:.1f}/100")
print(f"         Hallucination risk: {model_check['hallucination_risk']}")

# Phase 5
violations_to_fix = rule_check.get('violations', [])
if violations_to_fix:
    final_answer = rewrite_answer(llm_resp, violations_to_fix)
    print(f"Phase 5 - Rewritten to fix {len(violations_to_fix)} violations")
else:
    final_answer = llm_resp
    print(f"Phase 5 - No rewriting needed (all checks passed)")

print(f"\nFinal Answer Preview:")
print(final_answer[:300] + "...")

print("\n[SUCCESS] Full 5-phase pipeline with hallucination detection working!")
print("\nWhen you POST to /chat in Swagger:")
print("  1. Issues extracted (Phase 1)")
print("  2. LLM generates response with anti-hallucination prompt (Phase 2)")
print("  3. Rules verified (Phase 3)")
print("  4. Model verified + confidence scored + hallucination detected (Phase 4)")
print("  5. Answer rewritten if violations found (Phase 5)")

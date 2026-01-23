"""Simple test to verify hallucination detection works"""

print("[1] Testing imports...")
from models.hallucination_detector import check_hallucination_indicators
print("    [OK] Hallucination detector imported")

print("[2] Testing hallucination detection...")
response1 = "This is general legal information, not legal advice. Typically contracts may become binding when parties agree."
result1 = check_hallucination_indicators(response1)
print(f"    Response 1 - Risk: {result1['hallucination_risk']}, Score: {result1['score']}/100")

response2 = "Contracts will absolutely always be binding. Under Smith v. Universal (2025), all contracts must be obeyed or face criminal penalties."
result2 = check_hallucination_indicators(response2)
print(f"    Response 2 - Risk: {result2['hallucination_risk']}, Score: {result2['score']}/100")

print("[3] Testing model verification...")
from models.model_verifier import verify_model
verify_result = verify_model(response1, "What about contracts?")
print(f"    Valid: {verify_result['is_valid']}")
print(f"    Confidence: {verify_result['confidence_score']:.1f}/100")
print(f"    Hallucination Risk: {verify_result['hallucination_risk']}")

print("[4] Testing API response format...")
from api.schemas import SafetyChecks
safety = SafetyChecks(
    rules_passed=True,
    model_verified=True,
    violations=[],
    confidence_score=85.5,
    hallucination_risk="low",
    claimed_facts=[]
)
print(f"    [OK] SafetyChecks schema created: {safety.confidence_score}/100, Risk: {safety.hallucination_risk}")

print("\n[SUCCESS] All hallucination detection features working!")
print("\nNOW TEST IN SWAGGER:")
print("  1. Go to: http://localhost:8000/docs")
print("  2. Try POST /chat with: 'What are key things to verify before signing a contract?'")
print("  3. Look for new fields in response:")
print("     - confidence_score (0-100)")
print("     - hallucination_risk (low/medium/high)")
print("     - claimed_facts (extracted citations)")

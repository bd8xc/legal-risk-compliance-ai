"""
Comprehensive test of enhanced robustness system - Full API Integration
"""

import requests
import json

print("[COMPREHENSIVE ROBUSTNESS TEST - FULL API]\n")

api_url = "http://localhost:8000"

# Test different questions that will trigger different robustness checks
test_questions = [
    {
        "name": "Good Question (Contract Basics)",
        "q": "What are the key things I should verify before signing a commercial contract?"
    },
    {
        "name": "Liability Question",
        "q": "If someone is injured at my business due to my negligence, what am I liable for?"
    },
    {
        "name": "Data Protection Question",
        "q": "What are my GDPR obligations when handling customer personal data?"
    },
]

for i, test in enumerate(test_questions, 1):
    print(f"\n{'='*70}")
    print(f"TEST {i}: {test['name']}")
    print(f"{'='*70}")
    print(f"Question: {test['q']}\n")
    
    try:
        response = requests.post(
            f"{api_url}/chat",
            json={"question": test['q']},
            timeout=150
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract key information
            safety = data.get('safety_checks', {})
            debug = data.get('debug_trace', [])
            
            print("Phase Results:")
            for trace in debug[:5]:  # Show first 5 traces
                print(f"  {trace}")
            
            print(f"\nRobustness Metrics:")
            print(f"  Confidence Score:    {safety.get('confidence_score', 0):.0f}/100")
            print(f"  Hallucination Risk:  {safety.get('hallucination_risk', 'unknown')}")
            print(f"  Hallucinations Found: {safety.get('known_hallucinations', 0)}")
            print(f"  Contradictions Found: {safety.get('logical_contradictions', 0)}")
            
            print(f"\nRecommendations:")
            for rec in safety.get('recommendations', [])[:3]:
                print(f"  -> {rec}")
            
            print(f"\nAnswer Preview:")
            answer = data.get('answer', '')
            print(f"  {answer[:150]}...")
            
        else:
            print(f"[ERROR] Status {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("[TIMEOUT] LLM took too long to respond - try enabling MOCK_LLM in .env")
    except Exception as e:
        print(f"[ERROR] {str(e)}")

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
print("\nWhat the system is now checking:")
print("  [1] Basic checks (relevance, length, JSON validity)")
print("  [2] Hallucination patterns (fake cases, fake laws)")
print("  [3] Logical contradictions")
print("  [4] Verified legal facts")
print("  [5] Confidence calibration")
print("  [6] Human review recommendations")
print("\nEach response now gets:")
print("  - Adjusted confidence score (0-100)")
print("  - Hallucination count")
print("  - Contradiction count")
print("  - Specific recommendations for review/rejection")

"""Test different legal issue categories"""

import requests
import json

print("[TEST] Legal Issue Categories\n")

# Define test questions for different legal areas
test_cases = {
    "liability": "If someone is injured at my business because of my negligence, what am I liable for?",
    "data_protection": "What are my GDPR obligations when storing customer personal data?",
    "intellectual_property": "Can I use someone else's copyrighted image if I credit them?",
    "termination": "What are the rules for terminating a contract early without penalty?",
    "compliance": "What regulatory requirements apply to my small business?",
}

api_url = "http://localhost:8000"

for issue_type, question in test_cases.items():
    print(f"\n{'='*70}")
    print(f"TESTING: {issue_type.upper()}")
    print(f"{'='*70}")
    print(f"Question: {question}\n")
    
    try:
        response = requests.post(
            f"{api_url}/chat",
            json={"question": question},
            timeout=150
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Show debug trace to see extracted issues
            debug = data.get('debug_trace', [])
            print("Debug Trace:")
            for trace in debug:
                print(f"  - {trace}")
            
            # Show safety checks
            safety = data.get('safety_checks', {})
            print(f"\nSafety Checks:")
            print(f"  Rules Passed:       {safety.get('rules_passed', False)}")
            print(f"  Model Verified:     {safety.get('model_verified', False)}")
            print(f"  Confidence Score:   {safety.get('confidence_score', 0):.1f}/100")
            print(f"  Hallucination Risk: {safety.get('hallucination_risk', 'unknown')}")
            
            # Show answer preview
            answer = data.get('answer', '')
            print(f"\nAnswer Preview:")
            print(f"  {answer[:200]}...")
            
        else:
            print(f"Error: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"Failed: {str(e)}")

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
print("\nYou can now test in Swagger with various legal questions:")
print("  - Liability: injury, damages, negligence")
print("  - Data Protection: GDPR, privacy, personal data")
print("  - IP: copyright, patent, trademark")
print("  - Termination: cancel, end, close")
print("  - Compliance: regulation, requirement, law")

"""
Comprehensive test suite for hallucination detection and reduction.

Tests:
1. Anti-hallucination prompt engineering
2. Hallucination indicator detection
3. Confidence scoring
4. Claim extraction
5. Contradiction detection
6. Full pipeline with real LLM
"""

import requests
import json
import logging
from models.hallucination_detector import (
    check_hallucination_indicators,
    extract_claims,
    detect_contradictions,
    calculate_confidence_score
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test responses with varying hallucination levels
TEST_CASES = {
    "high_quality_safe": """This is general legal information, not legal advice.

Typically, a contract becomes binding when all parties agree to its terms, subject to applicable jurisdiction and local laws. Generally speaking, key things to verify typically include:

1. Party Identification - Ensure all parties are correctly identified according to legal name conventions
2. Terms and Conditions - Review all obligations and terms that may vary by jurisdiction
3. Consideration - Verify that adequate consideration is exchanged, which generally means something of value
4. Governing Law - Determines which jurisdiction's laws apply

Important variables that affect this answer include the type of contract, jurisdiction, and specific circumstances. Please consult with a qualified legal professional for advice specific to your situation.""",

    "medium_quality": """A contract usually becomes binding when parties agree. Key things:

1. Identify all parties correctly
2. Review terms and obligations
3. Check for consideration (value exchange)
4. Determine governing law and jurisdiction

The effectiveness depends on jurisdiction and contract type. You should probably consult a lawyer.""",

    "high_hallucination_risky": """A contract becomes binding immediately and absolutely always when signed. Under Section 404.2 of the Federal Contract Law (2023), all contracts automatically become legally enforceable within 2 hours.

In the landmark case Smith v. Universal Contracts (2024), the court definitively ruled that all terms in any contract must be obeyed or you will definitely face criminal penalties. The Johnson clause of 1999 absolutely requires all parties to abide by every word.

You will always face severe legal consequences if you violate any contract term.""",

    "mixed_hallucination": """Generally speaking, contracts typically become binding when parties agree. However, under the definitely permanent Law of Contract Enforcement (2025), all contracts must be absolutely obeyed. 

The case Anderson v. Corp typically shows that contracts may vary by jurisdiction. But the Smith Doctrine of 2024 will absolutely require compliance.

It's important to consider jurisdiction and circumstances, but you must always follow every term or face consequences.""",
}

def test_hallucination_detection():
    """Test hallucination detection on various response types."""
    print("\n" + "="*70)
    print("HALLUCINATION DETECTION TESTS")
    print("="*70)
    
    for name, response in TEST_CASES.items():
        print(f"\n-> Testing: {name}")
        print(f"  Response length: {len(response)} characters")
        
        # Check for hallucination indicators
        indicators = check_hallucination_indicators(response)
        
        print(f"  Hallucination Risk: {indicators['hallucination_risk'].upper()}")
        print(f"  Confidence Score: {indicators['score']}/100")
        print(f"  Suspicious Patterns: {len(indicators['suspicious_patterns'])}")
        
        if indicators['suspicious_patterns']:
            print(f"  Detected suspicious:")
            for pattern in indicators['suspicious_patterns'][:3]:
                print(f"    - {pattern.get('type', 'unknown')}: {pattern.get('match', '')[:50]}")
        
        print(f"  Uncertainty Markers: {indicators['uncertainty_markers']}")
        print(f"  Confidence Markers: {indicators['confidence_markers']}")
        print(f"  Citations: {indicators['citation_count']}")

def test_claim_extraction():
    """Test extraction of factual claims."""
    print("\n" + "="*70)
    print("CLAIM EXTRACTION TESTS")
    print("="*70)
    
    for name, response in TEST_CASES.items():
        print(f"\n-> {name}")
        claims = extract_claims(response)
        
        if claims:
            print(f"  Extracted {len(claims)} claim type(s):")
            for claim in claims:
                print(f"    • {claim['type']}: {len(claim['values'])} items")
                for value in claim['values'][:2]:
                    print(f"      - {value}")
        else:
            print(f"  No claims extracted")

def test_contradiction_detection():
    """Test detection of internal contradictions."""
    print("\n" + "="*70)
    print("CONTRADICTION DETECTION TESTS")
    print("="*70)
    
    contradiction_test = """The contract will absolutely always be binding. However, the contract may not be binding in some cases. The law definitely requires compliance but also allows flexibility."""
    
    print(f"\n-> Testing response with contradictions...")
    contradictions = detect_contradictions(contradiction_test)
    
    if contradictions:
        print(f"  Found {len(contradictions)} contradiction(s):")
        for contra in contradictions:
            print(f"    • {contra['type']}")
            print(f"      Line 1: {contra['line1']}")
            print(f"      Line 2: {contra['line2']}")
    else:
        print(f"  No contradictions detected")

def test_api_with_hallucination_detection():
    """Test the actual API with hallucination detection."""
    print("\n" + "="*70)
    print("API INTEGRATION TESTS")
    print("="*70)
    
    api_url = "http://localhost:8000"
    test_questions = [
        "What are the key things I should verify before signing a contract?",
        "What happens if I breach an employment contract?",
        "How long do I have to sign a contract after it's offered?"
    ]
    
    for question in test_questions:
        print(f"\n-> Question: {question[:60]}...")
        
        try:
            response = requests.post(
                f"{api_url}/chat",
                json={"question": question},
                timeout=150
            )
            
            if response.status_code == 200:
                data = response.json()
                safety = data.get('safety_checks', {})
                
                print(f"  Status: {data.get('status')}")
                print(f"  Confidence: {safety.get('confidence_score', 'N/A'):.1f}/100")
                print(f"  Hallucination Risk: {safety.get('hallucination_risk', 'N/A')}")
                print(f"  Rules Passed: {safety.get('rules_passed', False)}")
                print(f"  Model Verified: {safety.get('model_verified', False)}")
                
                if safety.get('claimed_facts'):
                    print(f"  Claimed Facts: {len(safety['claimed_facts'])} type(s) extracted")
                
                # Show response preview
                answer = data.get('answer', '')
                print(f"  Response preview: {answer[:100]}...")
                
            else:
                print(f"  Error: {response.status_code}")
                print(f"  Response: {response.text}")
                
        except Exception as e:
            print(f"  Failed: {str(e)}")

def test_confidence_scoring():
    """Test confidence score calculation."""
    print("\n" + "="*70)
    print("CONFIDENCE SCORING TESTS")
    print("="*70)
    
    for name, response in TEST_CASES.items():
        print(f"\n-> {name}")
        
        indicators = check_hallucination_indicators(response)
        model_checks = {
            'checks': {
                'relevant': True,
                'length': len(response.split()) > 10,
                'json_valid': True
            }
        }
        
        confidence = calculate_confidence_score(response, indicators, model_checks)
        
        print(f"  Final Confidence Score: {confidence:.1f}/100")
        
        if confidence >= 80:
            recommendation = "[SAFE] High confidence, ready for production"
        elif confidence >= 60:
            recommendation = "[CAUTION] Medium confidence, review recommended"
        else:
            recommendation = "[REJECT] Low confidence, do not use"
        
        print(f"  Recommendation: {recommendation}")

def main():
    """Run all hallucination detection tests."""
    print("\n" + "COMPREHENSIVE HALLUCINATION DETECTION TEST SUITE")
    
    # Test hallucination detection algorithms
    test_hallucination_detection()
    
    # Test claim extraction
    test_claim_extraction()
    
    # Test contradiction detection
    test_contradiction_detection()
    
    # Test confidence scoring
    test_confidence_scoring()
    
    # Test full API pipeline
    test_api_with_hallucination_detection()
    
    print("\n" + "="*70)
    print("ALL HALLUCINATION DETECTION TESTS COMPLETED")
    print("="*70)

if __name__ == "__main__":
    main()

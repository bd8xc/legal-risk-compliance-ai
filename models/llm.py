"""
LLM client for Legal Risk & Compliance AI System

Handles communication with Ollama/Mistral LLM service with proper error handling,
timeout management, and retry logic. Supports mock mode for testing.
"""

import requests
import logging
import time
from config import LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT, LLM_MAX_RETRIES, MOCK_LLM_ENABLED

logger = logging.getLogger(__name__)

# =====================================================================
# ANTI-HALLUCINATION PROMPT ENGINEERING
# =====================================================================
# This prompt is designed to minimize hallucinations through:
# 1. Chain-of-thought (explicit reasoning)
# 2. Confidence requirements
# 3. Uncertainty acknowledgment
# 4. Citation preferences
# 5. Structured output format
# =====================================================================

ANTI_HALLUCINATION_PROMPT = """You are a legal information assistant. When answering legal questions:

CRITICAL REQUIREMENTS:
1. ACCURACY: Only provide information you are confident is accurate.
2. UNCERTAINTY: Always express uncertainty using "may", "might", "could", "often", "typically", "generally"
3. DISCLAIMERS: Start with "This is general legal information, not legal advice."
4. CONFIDENCE: Include phrases like "subject to jurisdiction", "may vary by location", "generally speaking"
5. CITATIONS: Reference specific law sections, statutes, or regulations when applicable
6. REASONING: Show your thinking - explain WHY before answering

FORBIDDEN:
- DO NOT make up specific case names or statute numbers
- DO NOT use absolute language like "always", "will", "must" without qualification
- DO NOT cite specific laws unless you are very confident they exist
- DO NOT provide definitive legal conclusions - these require professional review

RESPONSE STRUCTURE:
1. Start with a disclaimer
2. Provide general principles (use cautious language)
3. Explain what TYPICALLY happens
4. List important VARIABLES that affect the answer
5. STRONGLY recommend consulting a lawyer

Remember: It's better to say "I'm not sure" than to make something up.

Now answer this question with appropriate caution and confidence-qualifying language:

"""

# Mock responses for testing without LLM
MOCK_RESPONSES = {
    "contract": """A contract typically becomes binding when all parties agree to its terms. Key things to look for when signing:

1. **Party Identification**: Ensure all parties are correctly identified with legal names and signatures.

2. **Terms and Conditions**: Carefully review all terms, conditions, and obligations you're committing to.

3. **Consideration**: Verify there's adequate consideration (something of value) exchanged by all parties.

4. **Governing Law**: Check which jurisdiction's laws govern the contract and where disputes would be handled.

5. **Termination Clauses**: Look for any provisions on how the contract can be ended and what happens then.

6. **Liability Limitations**: Review any caps on liability and exemptions from responsibility.

7. **Confidentiality**: Check if you're agreeing to keep certain information private.

8. **Dispute Resolution**: Look for clauses on arbitration, mediation, or litigation procedures.

This is general information and not legal advice. Please consult with a qualified legal professional for advice specific to your situation.""",
    "employment": """Employment contracts typically contain important provisions:

1. **Position and Duties**: Clearly defined job title and responsibilities.

2. **Compensation**: Salary, benefits, bonuses, and payment terms.

3. **Duration**: Whether it's permanent, fixed-term, or at-will employment.

4. **Termination**: Notice periods, severance, and grounds for termination.

5. **Confidentiality**: Restrictions on sharing company information.

6. **Non-Compete**: Restrictions on working for competitors after employment.

7. **Intellectual Property**: Who owns work created during employment.

This depends on your specific circumstances and jurisdiction. Consider consulting an employment lawyer.""",
    "default": """This is general legal information. The specific answer depends on your circumstances, jurisdiction, and the exact facts of your situation. I recommend consulting with a qualified legal professional who can review your specific case details and provide appropriate guidance. This is not legal advice."""
}

def get_mock_response(question: str) -> str:
    """
    Get a mock LLM response for testing purposes.
    
    Args:
        question: The legal question
        
    Returns:
        str: A mock response based on question keywords
    """
    question_lower = question.lower()
    
    if any(word in question_lower for word in ['contract', 'signing', 'agree']):
        return MOCK_RESPONSES["contract"]
    elif any(word in question_lower for word in ['employment', 'employee', 'job', 'hire']):
        return MOCK_RESPONSES["employment"]
    else:
        return MOCK_RESPONSES["default"]

def get_llm_response(question: str) -> str:
    """
    Get response from LLM (Ollama/Mistral) with retry logic and anti-hallucination prompting.
    
    Args:
        question: The legal question to ask the LLM
        
    Returns:
        str: The LLM response text
        
    Raises:
        Exception: On timeout, connection error, or invalid response
    """
    # Return mock response if mock mode is enabled
    if MOCK_LLM_ENABLED:
        logger.info("Using mock LLM response (mock mode enabled)")
        return get_mock_response(question)
    
    # Prepend anti-hallucination prompt engineering to question
    engineered_prompt = ANTI_HALLUCINATION_PROMPT + question
    
    # Retry logic
    last_error = None
    for attempt in range(1, LLM_MAX_RETRIES + 1):
        try:
            logger.debug(f"LLM call attempt {attempt}/{LLM_MAX_RETRIES} ({LLM_MODEL}) at {LLM_BASE_URL}")
            
            response = requests.post(
                f"{LLM_BASE_URL}/api/generate",
                json={
                    "prompt": engineered_prompt,
                    "stream": False,
                    "model": LLM_MODEL,
                    "temperature": 0.3,  # Lower temperature = more deterministic, fewer hallucinations
                    "top_p": 0.8,        # Nucleus sampling = more focused, less random
                },
                timeout=LLM_TIMEOUT
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse JSON response
            result = response.json()
            
            # Validate response structure
            if 'response' not in result:
                logger.error(f"Invalid LLM response structure: {result.keys()}")
                raise ValueError("Missing 'response' field in LLM response")
            
            llm_response = result['response'].strip()
            logger.info(f"LLM response received ({len(llm_response)} characters)")
            
            return llm_response
            
        except requests.exceptions.Timeout as e:
            last_error = e
            logger.warning(f"LLM timeout on attempt {attempt}/{LLM_MAX_RETRIES}: {LLM_TIMEOUT}s")
            if attempt < LLM_MAX_RETRIES:
                wait_time = attempt * 2
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        
        except requests.exceptions.ConnectionError as e:
            last_error = e
            logger.warning(f"Connection error on attempt {attempt}/{LLM_MAX_RETRIES}: {str(e)}")
            if attempt < LLM_MAX_RETRIES:
                wait_time = attempt * 2
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        
        except requests.exceptions.HTTPError as e:
            logger.error(f"LLM HTTP error: {e.response.status_code} - {str(e)}")
            raise RuntimeError(f"LLM service error: {e.response.status_code}")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"LLM request failed: {str(e)}")
            raise Exception(f"LLM request error: {str(e)}")
        
        except ValueError as e:
            logger.error(f"Invalid LLM response: {str(e)}")
            raise Exception(f"Invalid LLM response: {str(e)}")
    
    # If we get here, all retries failed
    if last_error:
        logger.error(f"All {LLM_MAX_RETRIES} retries failed. Last error: {str(last_error)}")
        raise Exception(f"LLM service failed after {LLM_MAX_RETRIES} retries: {str(last_error)}")
    else:
        raise Exception(f"LLM service failed after {LLM_MAX_RETRIES} retries")

__all__ = ['get_llm_response']

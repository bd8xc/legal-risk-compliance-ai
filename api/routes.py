"""
Chat endpoint implementation with 5-phase safety pipeline
"""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from slowapi.util import get_remote_address
from slowapi import Limiter

from config import (
    MIN_QUESTION_LENGTH,
    MAX_QUESTION_LENGTH,
    ENABLE_QUERY_LOGGING
)

from api.schemas import (
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    SafetyChecks
)

from models.issue_extractor import extract_issues
from models.llm import get_llm_response
from models.rule_verifier import verify_rules
from models.model_verifier import verify_model
from models.rewriter import rewrite_answer

logger = logging.getLogger(__name__)
router = APIRouter()

# Rate limiter (passed from main.py)
limiter = None

def set_limiter(l):
    """Set the limiter from main.py"""
    global limiter
    limiter = l

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint with 5-phase safety pipeline.
    
    Phases:
    1. Issue Extraction - Categorize the legal question
    2. LLM Generation - Get response from Mistral/Ollama
    3. Rule Verification - Check hard safety rules
    4. Model Verification - Detect hallucinations
    5. Rewriting - Fix safety violations
    
    Args:
        request: ChatRequest with question field
        
    Returns:
        ChatResponse with answer and safety checks
        
    Raises:
        HTTPException: On validation or processing errors
    """
    question = request.question.strip()
    debug_trace = []
    safety_checks = {
        'rules_passed': False,
        'model_verified': False,
        'violations': []
    }
    
    try:
        # ====================================================================
        # Input Validation
        # ====================================================================
        if not question:
            logger.warning("Empty question received")
            raise HTTPException(
                status_code=400,
                detail="Question cannot be empty"
            )
        
        if len(question) < MIN_QUESTION_LENGTH:
            logger.warning(f"Question too short: {len(question)} chars")
            raise HTTPException(
                status_code=400,
                detail=f"Question must be at least {MIN_QUESTION_LENGTH} characters"
            )
        
        if len(question) > MAX_QUESTION_LENGTH:
            logger.warning(f"Question too long: {len(question)} chars")
            raise HTTPException(
                status_code=413,
                detail=f"Question cannot exceed {MAX_QUESTION_LENGTH} characters"
            )
        
        if ENABLE_QUERY_LOGGING:
            logger.info(f"Chat request received: {question[:100]}...")
        
        debug_trace.append(f"Question validated: {len(question)} characters")
        
        # ====================================================================
        # Phase 1: Issue Extraction
        # ====================================================================
        try:
            issues = extract_issues(question)
            debug_trace.append(f"Phase 1 - Issues extracted: {', '.join(issues)}")
            logger.info(f"Issues identified: {issues}")
        except Exception as e:
            logger.error(f"Issue extraction failed: {str(e)}")
            debug_trace.append(f"Phase 1 - Error: {str(e)}")
            # Continue with generic response
            issues = ['compliance']
        
        # ====================================================================
        # Phase 2: LLM Generation
        # ====================================================================
        try:
            logger.debug(f"Calling LLM for question")
            llm_response = get_llm_response(question)
            debug_trace.append(
                f"Phase 2 - LLM response received: {len(llm_response)} characters"
            )
            logger.info(f"LLM response received: {len(llm_response)} chars")
        except TimeoutError:
            logger.error("LLM request timed out")
            raise HTTPException(
                status_code=504,
                detail="LLM service timed out. Please try again."
            )
        except ConnectionError:
            logger.error("Cannot connect to LLM service")
            raise HTTPException(
                status_code=503,
                detail="LLM service unavailable. Please try again later."
            )
        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail=f"Error communicating with LLM: {str(e)}"
            )
        
        # ====================================================================
        # Phase 3: Rule Verification
        # ====================================================================
        try:
            rule_result = verify_rules(llm_response)
            safety_checks['rules_passed'] = rule_result.get('passes', False)
            violations = rule_result.get('violations', [])
            safety_checks['violations'].extend(violations)
            
            if rule_result.get('passes'):
                debug_trace.append("Phase 3 - Rule verification: PASSED")
            else:
                debug_trace.append(
                    f"Phase 3 - Rule violations: {', '.join(violations)}"
                )
            
            logger.info(f"Rule verification: {'PASSED' if rule_result['passes'] else 'FAILED'}")
        except Exception as e:
            logger.error(f"Rule verification failed: {str(e)}")
            debug_trace.append(f"Phase 3 - Error: {str(e)}")
            safety_checks['rules_passed'] = False
            violations = []
        
        # ====================================================================
        # Phase 4: Model Verification (with Advanced Robustness Checking)
        # ====================================================================
        try:
            model_result = verify_model(llm_response, question)
            safety_checks['model_verified'] = model_result.get('is_valid', False)
            
            # Extract confidence score and hallucination info
            safety_checks['confidence_score'] = model_result.get('confidence_score', 0)
            safety_checks['hallucination_risk'] = model_result.get('hallucination_risk', 'unknown')
            safety_checks['claimed_facts'] = model_result.get('claimed_facts', [])
            
            # Enhanced robustness metrics
            known_halluc = model_result.get('known_hallucinations', {})
            safety_checks['known_hallucinations'] = len(known_halluc.get('detected_hallucinations', []))
            
            logical_incons = model_result.get('logical_inconsistencies', [])
            safety_checks['logical_contradictions'] = len(logical_incons)
            
            safety_checks['recommendations'] = model_result.get('recommendations', [])
            
            if model_result.get('is_valid'):
                debug_trace.append(
                    f"Phase 4 - Robustness check: PASSED "
                    f"(confidence: {safety_checks['confidence_score']:.1f}, "
                    f"risk: {safety_checks['hallucination_risk']})"
                )
            else:
                debug_trace.append(
                    f"Phase 4 - Model verification failed: {model_result.get('reason', 'Unknown')} "
                    f"(confidence: {safety_checks['confidence_score']:.1f}, "
                    f"risk: {safety_checks['hallucination_risk']})"
                )
            
            logger.info(
                f"Model verification: {'PASSED' if model_result['is_valid'] else 'FAILED'} "
                f"(confidence: {safety_checks['confidence_score']:.1f})"
            )
        except Exception as e:
            logger.error(f"Model verification failed: {str(e)}")
            debug_trace.append(f"Phase 4 - Error: {str(e)}")
            safety_checks['model_verified'] = False
        
        # ====================================================================
        # Phase 5: Rewriting (if needed)
        # ====================================================================
        answer = llm_response
        if not safety_checks['rules_passed'] or not safety_checks['model_verified']:
            try:
                violations_to_fix = safety_checks.get('violations', [])
                rewritten = rewrite_answer(llm_response, violations_to_fix)
                answer = rewritten
                debug_trace.append(
                    f"Phase 5 - Answer rewritten to address {len(violations_to_fix)} violation(s)"
                )
                logger.info("Answer rewritten for safety")
            except Exception as e:
                logger.warning(f"Rewriting failed, using original: {str(e)}")
                debug_trace.append(f"Phase 5 - Rewriting error, using original: {str(e)}")
                answer = llm_response
        else:
            debug_trace.append("Phase 5 - No rewriting needed")
        
        # ====================================================================
        # Success Response
        # ====================================================================
        debug_trace.append("All phases completed successfully")
        
        response = ChatResponse(
            question=question,
            answer=answer,
            safety_checks=SafetyChecks(**safety_checks),
            debug_trace=debug_trace,
            status="success"
        )
        
        logger.info(f"Chat request completed successfully")
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error. Please try again."
        )

@router.get("/chat/verify-rules")
async def verify_rules_endpoint(question: str):
    """
    Debug endpoint to test rule verification without LLM call.
    
    Args:
        question: Question to analyze
        
    Returns:
        dict: Rule verification results
    """
    try:
        from models.rule_verifier import verify_rules
        from models.issue_extractor import extract_issues
        
        issues = extract_issues(question)
        
        return {
            "question": question,
            "issues": issues,
            "sample_verification": "Rule verification endpoint for debugging"
        }
    except Exception as e:
        logger.error(f"Debug endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

__all__ = ['router', 'set_limiter']

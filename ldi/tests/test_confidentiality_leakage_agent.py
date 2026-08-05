from __future__ import annotations

from agents.confidentiality_leakage.agent import ConfidentialityLeakageAgent
from agents.confidentiality_leakage.classifier import classify_findings
from agents.confidentiality_leakage.content_detector import detect_confidential_content
from agents.confidentiality_leakage.ner_detector import detect_ner_sensitive_info
from agents.confidentiality_leakage.regex_detector import detect_regex_sensitive_info
from agents.confidentiality_leakage.scorer import score_confidentiality


def test_email_detection():
    detections = detect_regex_sensitive_info("Contact john.doe@example.com for details.")
    assert any(item["type"] == "EMAIL" for item in detections)


def test_phone_detection():
    detections = detect_regex_sensitive_info("Call +91 98765 43210 today.")
    assert any(item["type"] == "PHONE_NUMBER" for item in detections)


def test_pan_detection():
    detections = detect_regex_sensitive_info("PAN is ABCDE1234F.")
    assert any(item["type"] == "PAN_NUMBER" for item in detections)


def test_aadhaar_detection():
    detections = detect_regex_sensitive_info("Aadhaar: 1234 5678 9012")
    assert any(item["type"] == "AADHAAR_NUMBER" for item in detections)


def test_postal_code_detection():
    detections = detect_regex_sensitive_info("Office location pin is 400013.")
    assert any(item["type"] == "POSTAL_CODE" for item in detections)


def test_address_detection():
    text = "Registered office at 95 Ganpatrao Kadam Marg, Lower Parel, Mumbai 400013"
    detections = detect_regex_sensitive_info(text)
    assert any(item["type"] == "ADDRESS" for item in detections)


def test_valid_credit_card_detection_using_luhn():
    detections = detect_regex_sensitive_info("Card 4111 1111 1111 1111 is listed.")
    assert any(item["type"] == "CREDIT_CARD" for item in detections)


def test_invalid_credit_card_like_number_rejection():
    detections = detect_regex_sensitive_info("Card 4111 1111 1111 1112 is listed.")
    assert all(item["type"] != "CREDIT_CARD" for item in detections)


def test_person_ner_detection():
    detections = detect_ner_sensitive_info("John Doe signed the agreement.")
    assert any(item["type"] == "PERSON" for item in detections)


def test_org_context_dependent_detection():
    detections = detect_ner_sensitive_info("Acme Corporation approved the change.")
    assert any(item["type"] == "ORG" for item in detections)


def test_ner_filters_legal_boilerplate_terms():
    detections = detect_ner_sensitive_info("Confidential Information may be shared only for the Purpose by the Party.")
    values = {item["value"].lower() for item in detections}
    assert "confidential information" not in values
    assert "purpose" not in values
    assert "party" not in values


def test_ner_filters_address_phrase_from_person():
    detections = detect_ner_sensitive_info("95 Ganpatrao Kadam Marg, Lower Parel, Mumbai")
    assert not any(item["type"] == "PERSON" and "Kadam Marg" in item["value"] for item in detections)


def test_ner_keeps_real_company_names():
    detections = detect_ner_sensitive_info("TATA DIGITAL PRIVATE LIMITED and STAR INDIA PRIVATE LIMITED signed.")
    org_values = [item["value"] for item in detections if item["type"] == "ORG"]
    assert any("TATA DIGITAL PRIVATE LIMITED" in value for value in org_values)


def test_regex_legal_entity_detection_for_company_names():
    detections = detect_regex_sensitive_info("Agreement between STAR INDIA PRIVATE LIMITED and TATA DIGITAL PRIVATE LIMITED")
    org_values = [item["value"] for item in detections if item["type"] == "ORG"]
    assert any("STAR INDIA PRIVATE LIMITED" in value for value in org_values)


def test_confidential_content_detection():
    detections = detect_confidential_content("This includes business plans, trade secret material, and customer lists.")
    types = {item["type"] for item in detections}
    assert "CONFIDENTIAL_STRATEGY" in types
    assert "CONFIDENTIAL_TRADE_SECRET" in types
    assert "CONFIDENTIAL_CUSTOMER" in types


def test_multiple_findings_in_one_clause():
    agent = ConfidentialityLeakageAgent()
    report = agent.analyze(
        "contract_001",
        [{"clause_id": "4.2", "section": "Employee Information", "text": "John Doe can be reached at john.doe@example.com."}],
    )
    assert report.total_findings >= 2


def test_response_values_are_masked():
    agent = ConfidentialityLeakageAgent()
    report = agent.analyze(
        "contract_003",
        [{"clause_id": "3.1", "section": "Contacts", "text": "Contact John Doe at john.doe@example.com or +91 98765 43210."}],
    )
    assert report.total_findings >= 2
    assert all(getattr(finding, "masked_value", "") for finding in report.findings)
    for finding in report.findings:
        assert "value" not in finding.model_dump()


def test_duplicate_overlapping_finding_removal():
    findings = [
        {"type": "PERSON", "value": "John Doe", "source": "ner", "start": 0, "end": 8},
        {"type": "PERSON", "value": "John Doe", "source": "ner", "start": 0, "end": 8},
    ]
    classified = classify_findings(findings, clause_id="1", section="S")
    assert len(classified) == 1


def test_empty_clause():
    agent = ConfidentialityLeakageAgent()
    report = agent.analyze("empty_doc", [{"clause_id": "1", "section": "S", "text": ""}])
    assert report.total_findings == 0
    assert report.sensitive_data_detected is False


def test_document_containing_no_sensitive_information():
    agent = ConfidentialityLeakageAgent()
    report = agent.analyze("clean_doc", [{"clause_id": "1", "section": "S", "text": "This agreement is effective upon signature."}])
    assert report.total_findings == 0
    assert report.risk_score == 0


def test_risk_score_calculation():
    score = score_confidentiality(
        [
            {"sensitivity": "HIGH"},
            {"sensitivity": "MEDIUM"},
            {"sensitivity": "CONTEXT_DEPENDENT"},
        ]
    )
    assert 0 <= score["risk_score"] <= 100
    assert score["risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def test_context_heavy_findings_do_not_auto_become_critical():
    score = score_confidentiality([{"sensitivity": "CONTEXT_DEPENDENT"} for _ in range(60)])
    assert score["risk_score"] < 75
    assert score["risk_level"] in {"LOW", "MEDIUM", "HIGH"}


def test_high_sensitivity_findings_drive_higher_risk_than_context_only():
    context_only = score_confidentiality([{"sensitivity": "CONTEXT_DEPENDENT"} for _ in range(20)])
    with_high = score_confidentiality(
        [{"sensitivity": "HIGH"}, {"sensitivity": "HIGH"}] + [{"sensitivity": "CONTEXT_DEPENDENT"} for _ in range(5)]
    )
    assert with_high["risk_score"] > context_only["risk_score"]


def test_multiple_clauses_preserve_clause_id_and_section():
    agent = ConfidentialityLeakageAgent()
    report = agent.analyze(
        "contract_002",
        [
            {"clause_id": "1", "section": "Alpha", "text": "john.doe@example.com"},
            {"clause_id": "2", "section": "Beta", "text": "Google approved the change."},
        ],
    )
    assert {finding.clause_id for finding in report.findings} == {"1", "2"}
    assert {finding.section for finding in report.findings} == {"Alpha", "Beta"}

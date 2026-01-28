from typing import Dict, List


LEGAL_GROUNDING = {
    "us": {
        "cyber_law": {
            "category": "United States computer crime law (federal and state)",
            "allowed_concepts": [
                "unauthorized access",
                "exceeding authorized access",
                "computer misuse",
                "computer fraud",
            ],
            "forbidden": [
                "section",
                "article",
                "ipc",
                "gdpr",
            ],
        },
        "contract_law": {
            "category": "United States contract law",
            "allowed_concepts": [
                "offer",
                "acceptance",
                "consideration",
                "breach",
                "damages",
                "enforceability",
            ],
            "forbidden": [
                "arrest",
                "imprisonment",
                "criminal offence",
            ],
        },
        "criminal_law": {
            "category": "United States criminal law",
            "allowed_concepts": [
                "offence",
                "intent",
                "prosecution",
                "penalties",
            ],
            "forbidden": [
                "civil damages",
                "contract breach",
            ],
        },
        "employment_law": {
            "category": "United States employment and labor law",
            "allowed_concepts": [
                "termination",
                "discrimination",
                "wrongful dismissal",
                "employee rights",
            ],
            "forbidden": [
                "criminal punishment",
                "imprisonment",
            ],
        },
        "data_protection": {
            "category": "United States data protection and privacy law",
            "allowed_concepts": [
                "data privacy",
                "consumer data rights",
                "regulatory compliance",
            ],
            "forbidden": [
                "criminal offence",
                "imprisonment",
                "gdpr",
            ],
        },
    },

    "uk": {
        "cyber_law": {
            "category": "United Kingdom computer misuse and cybercrime law",
            "allowed_concepts": [
                "unauthorized access",
                "computer misuse",
                "unauthorized modification",
            ],
            "forbidden": [
                "cfaa",
                "ipc",
                "gdpr",
            ],
        },
        "contract_law": {
            "category": "United Kingdom contract law",
            "allowed_concepts": [
                "offer",
                "acceptance",
                "consideration",
                "breach",
                "remedies",
            ],
            "forbidden": [
                "criminal offence",
                "imprisonment",
            ],
        },
        "criminal_law": {
            "category": "United Kingdom criminal law",
            "allowed_concepts": [
                "offence",
                "intent",
                "penalties",
                "prosecution",
            ],
            "forbidden": [
                "civil remedies",
                "contractual liability",
            ],
        },
        "employment_law": {
            "category": "United Kingdom employment law",
            "allowed_concepts": [
                "unfair dismissal",
                "discrimination",
                "worker rights",
            ],
            "forbidden": [
                "criminal penalties",
            ],
        },
        "data_protection": {
            "category": "United Kingdom data protection law",
            "allowed_concepts": [
                "personal data",
                "data controller obligations",
                "regulatory enforcement",
            ],
            "forbidden": [
                "criminal offence",
            ],
        },
    },

    "eu": {
        "cyber_law": {
            "category": "European Union cyber regulation (non-criminal)",
            "allowed_concepts": [
                "regulatory obligations",
                "member state criminal law",
            ],
            "forbidden": [
                "criminal offence",
                "imprisonment",
                "section",
            ],
        },
        "contract_law": {
            "category": "European Union contract and consumer law",
            "allowed_concepts": [
                "consumer protection",
                "contract fairness",
                "harmonisation",
            ],
            "forbidden": [
                "criminal penalties",
            ],
        },
        "criminal_law": {
            "category": "EU criminal law coordination (member-state based)",
            "allowed_concepts": [
                "harmonisation",
                "minimum standards",
                "member state enforcement",
            ],
            "forbidden": [
                "direct criminal offence",
                "imprisonment",
            ],
        },
        "employment_law": {
            "category": "European Union labour and employment regulation",
            "allowed_concepts": [
                "worker protections",
                "equal treatment",
            ],
            "forbidden": [
                "criminal sanctions",
            ],
        },
        "data_protection": {
            "category": "European Union data protection regulation",
            "allowed_concepts": [
                "personal data",
                "lawful processing",
                "data subject rights",
            ],
            "forbidden": [
                "criminal offence",
            ],
        },
    },

    "india": {
        "cyber_law": {
            "category": "Indian cyber and computer-related law",
            "allowed_concepts": [
                "unauthorized access",
                "computer-related offences",
            ],
            "forbidden": [
                "cfaa",
                "gdpr",
            ],
        },
        "contract_law": {
            "category": "Indian contract law",
            "allowed_concepts": [
                "agreement",
                "consideration",
                "breach",
                "damages",
            ],
            "forbidden": [
                "criminal punishment",
            ],
        },
        "criminal_law": {
            "category": "Indian criminal law",
            "allowed_concepts": [
                "offence",
                "intent",
                "punishment",
            ],
            "forbidden": [
                "civil remedies",
            ],
        },
        "employment_law": {
            "category": "Indian labour and employment law",
            "allowed_concepts": [
                "termination",
                "labour rights",
            ],
            "forbidden": [
                "criminal imprisonment",
            ],
        },
        "data_protection": {
            "category": "Indian data protection and privacy law",
            "allowed_concepts": [
                "personal data",
                "data fiduciary obligations",
            ],
            "forbidden": [
                "gdpr",
                "criminal offence",
            ],
        },
    },
}


def get_grounding_context(
    jurisdiction: str,
    domains: List[str]
) -> Dict:
    """
    Returns grounding constraints for the given jurisdiction + domains.
    """
    context = {}

    for domain in domains:
        domain_info = LEGAL_GROUNDING.get(jurisdiction, {}).get(domain)
        if domain_info:
            context[domain] = domain_info

    return context

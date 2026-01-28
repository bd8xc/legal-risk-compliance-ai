from typing import List

DOMAIN_KEYWORDS = {
    "contract_law": [
        "contract", "agreement", "document", "sign", "signing",
        "terms", "conditions", "clause", "obligation"
    ],
    "criminal_law": [
        "crime", "criminal", "offence", "offense",
        "ipc", "fir", "arrest", "bail", "punishment"
    ],
    "civil_law": [
        "civil", "damages", "injunction", "dispute", "liability"
    ],
    "employment_law": [
        "employee", "employer", "termination", "salary", "workplace"
    ],
    "consumer_law": [
        "consumer", "defective", "refund", "warranty", "product"
    ],
    "cyber_law": [
        "cyber", "hacking", "data breach",
        "unauthorized access", "computer system", "it act"
    ],
    "constitutional_law": [
        "constitution", "fundamental right", "article"
    ],
    "procedural_law": [
        "court", "trial", "procedure", "appeal", "jurisdiction"
    ]
}

def extract_domains(question: str) -> List[str]:
    q = question.lower()
    domains = []

    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(keyword in q for keyword in keywords):
            domains.append(domain)

    return domains

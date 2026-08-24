"""Controlled vocabularies used by semantic, category detectors."""

SENSITIVE_PERSONAL = {
    "MEDICAL_HISTORY": ("medical history", "medical record", "medical records", "health history"),
    "DIAGNOSIS": ("diagnosis", "diagnosed", "clinical condition"),
    "PRESCRIPTION": ("prescription", "medication", "treatment"),
    "HEALTH_INSURANCE": ("health insurance", "medical insurance"),
    "BLOOD_GROUP": ("blood group", "blood type"),
    "BIOMETRIC_DATA": ("biometric", "fingerprint", "retina", "iris scan", "face id", "facial recognition"),
    "GENETIC_INFORMATION": ("genetic information", "genetic data", "dna"),
    "DISABILITY": ("disability", "disabled status"),
    "RELIGION": ("religion", "religious affiliation"),
    "POLITICAL_AFFILIATION": ("political affiliation", "political party membership"),
    "SEXUAL_ORIENTATION": ("sexual orientation",),
}

BUSINESS_CONFIDENTIAL = {
    "CONFIDENTIAL_TRADE_SECRET": ("trade secret", "proprietary information", "source code", "algorithm"),
    "CONFIDENTIAL_FINANCIAL": ("financial statement", "financial forecast", "revenue", "profit margin", "pricing", "budget"),
    "CONFIDENTIAL_CUSTOMER": ("customer list", "customer lists", "client list", "client lists", "supplier list", "supplier lists", "vendor list", "vendor lists"),
    "CONFIDENTIAL_STRATEGY": ("business plan", "business plans", "internal strategy", "product roadmap", "acquisition plan"),
    "CONFIDENTIAL_RESEARCH": ("research and development", "research data", "patent information"),
    "CONFIDENTIAL_CONTRACT": ("confidential contract", "contract terms", "non-public agreement"),
    "CONFIDENTIAL_CREDENTIAL": ("encryption key", "api secret", "password", "credential"),
}

PROCESSING_ACTIVITIES = (
    "collect", "store", "retain", "delete", "erase", "share", "transfer", "transmit", "process",
    "third party", "vendor", "processor", "cloud", "backup", "archive", "cross-border transfer",
    "consent", "purpose limitation",
)

LEGAL_BOILERPLATE = {
    "company", "employee", "applicable law", "cause", "agreement", "schedule", "section", "party",
    "receiving party", "disclosing party", "confidential information", "affiliate", "affiliates",
}

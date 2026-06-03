"""
Contract risk comparison and scoring helpers.

Note: avoid importing FastAPI router at package import time so the package
can be imported in test environments where FastAPI may not be installed.
Import `ldi.contract_risk.router` explicitly when wiring the application.
"""

__all__ = [
    "service",
    "schemas",
    "storage",
    "scoring",
    "router",
]
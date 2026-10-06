import os
import json
import logging
from app.agents.nodes import risk_analysis_node, compliance_node, negotiation_node

logging.basicConfig(level=logging.ERROR)

clauses = [
  {"clause_type": "Governing Law", "original_text": "Governing Law: California"},
  {"clause_type": "Contract Value", "original_text": "Contract Value: $111,111"},
  {"clause_type": "Term", "original_text": "Term: 12 months"},
  {"clause_type": "Indemnification", "original_text": "Supplier shall indemnify Customer against third-party claims arising from intellectual property infringement."},
  {"clause_type": "Liability", "original_text": "Liability shall not exceed the fees paid during the preceding 12 months."},
  {"clause_type": "Privacy", "original_text": "The parties acknowledge compliance obligations under the California Consumer Privacy Act (CCPA)."},
  {"clause_type": "Payment", "original_text": "Late payments accrue interest at 2% per month."},
  {"clause_type": "Termination", "original_text": "Either party may terminate with 30 days written notice."}
]

state = {
    "extracted_clauses": clauses,
    "query": ""
}

print("=== TESTING RISK ===")
try:
    res = risk_analysis_node(state)
    print("RISK OUT:", res.get("risk_matrix"))
except Exception as e:
    print("RISK ERR:", e)

print("=== TESTING COMPLIANCE ===")
try:
    res = compliance_node(state)
    print("COMPLIANCE OUT:", res.get("compliance_report"))
except Exception as e:
    print("COMPLIANCE ERR:", e)

print("=== TESTING NEGOTIATION ===")
try:
    # negotiation expects risk_matrix and compliance_report
    state["risk_matrix"] = res.get("risk_matrix", [])
    state["compliance_report"] = res.get("compliance_report", [])
    res = negotiation_node(state)
    print("NEGOTIATION OUT:", res.get("negotiation_suggestions"))
except Exception as e:
    print("NEGOTIATION ERR:", e)

"""
Retrieval Configuration and Constants

Defines legal synonyms, ranking weights, and configuration for the retrieval pipeline.
"""

from typing import Dict, List, Final

# ============================================================================
# LEGAL QUERY EXPANSION SYNONYMS
# ============================================================================

LEGAL_QUERY_SYNONYMS: Final[Dict[str, List[str]]] = {
    # Termination
    "termination": ["terminate", "cancel", "end", "exit", "ending", "cessation", "close"],
    "termination clause": ["termination provision", "termination rights", "termination conditions"],
    "early termination": ["premature termination", "immediate termination", "expedited termination"],
    "termination rights": ["right to terminate", "termination options", "termination trigger"],
    "contract termination": ["contract cancellation", "contract ending"],
    "termination notice": ["notice of termination", "termination notification", "termination warning"],
    "termination for cause": ["termination cause", "cause termination", "grounds for termination"],
    "termination for convenience": ["termination convenience", "termination at will"],
    
    # Payment & Financial
    "payment terms": ["payment schedule", "payment conditions", "payment provision", "billing"],
    "payment terms": ["payment obligation", "payment due", "payment deadline"],
    "price": ["cost", "fee", "amount", "compensation", "consideration", "rate"],
    "invoice": ["billing", "bill", "payment request", "statement"],
    "late payment": ["overdue", "delinquent", "non-payment", "payment delay"],
    "payment penalty": ["late fee", "interest", "default rate", "penalty rate"],
    "deposit": ["upfront payment", "security deposit", "retainer"],
    
    # Confidentiality & NDA
    "confidentiality": ["confidential", "non-disclosure", "nda", "secret", "proprietary"],
    "confidential information": ["trade secret", "proprietary information", "sensitive data"],
    "non-disclosure": ["confidentiality", "information protection", "secrecy"],
    "confidentiality clause": ["confidentiality provision", "confidentiality obligation"],
    "breach of confidentiality": ["confidentiality breach", "nda violation"],
    
    # Liability & Indemnity
    "limitation of liability": ["liability cap", "liability limit", "capped liability", "limited liability"],
    "indemnification": ["indemnify", "hold harmless", "indemnity", "indemnification clause"],
    "indemnification clause": ["indemnity provision", "indemnification obligation"],
    "liability exclusion": ["excluded liability", "liability carve-out", "liability exception"],
    "damages": ["loss", "harm", "injury", "injury", "monetary loss"],
    "consequential damages": ["indirect damages", "special damages", "loss of profits"],
    "liability cap amount": ["maximum liability", "liability threshold"],
    
    # Intellectual Property
    "intellectual property": ["ip", "patent", "copyright", "trademark", "proprietary rights"],
    "ownership": ["own", "owned", "owner", "ownership rights", "property rights"],
    "copyright": ["author rights", "work ownership", "copyright protection"],
    "patent": ["patented", "patent rights", "patent protection", "patent claims"],
    "trademark": ["brand", "mark", "brand protection"],
    "license": ["licensed", "licensing", "licensed rights", "grant of rights"],
    "licensing rights": ["license grant", "permitted use"],
    
    # Dispute Resolution
    "dispute resolution": ["dispute handling", "conflict resolution", "dispute process"],
    "arbitration": ["arbitrate", "arbitrator", "arbitration process"],
    "mediation": ["mediate", "mediator", "settlement discussion"],
    "litigation": ["lawsuit", "court proceedings", "legal action"],
    "governing law": ["applicable law", "jurisdiction", "legal jurisdiction"],
    "choice of law": ["governing law", "jurisdiction clause"],
    "venue": ["jurisdiction", "forum", "place of litigation"],
    
    # Warranty & Representation
    "warranty": ["warranted", "warrant", "guarantee", "guaranteed"],
    "representation": ["represent", "represented", "assertion", "statement"],
    "warranties and representations": ["warranty clause", "representation clause"],
    "warranty disclaimer": ["warranty exclusion", "no warranty"],
    "breach of warranty": ["warranty breach", "warranty violation"],
    
    # Force Majeure
    "force majeure": ["act of god", "unforeseeable event", "impossibility", "act of nature"],
    "force majeure clause": ["force majeure provision", "impossibility clause"],
    "force majeure event": ["qualifying event", "covered event"],
    
    # Term & Duration
    "term": ["duration", "period", "tenure", "time period", "length"],
    "contract term": ["contract duration", "agreement period"],
    "renewal": ["renew", "extend", "extension", "continued"],
    "automatic renewal": ["renewal automatic", "auto-renewal"],
    "renewal clause": ["renewal provision", "renewal option"],
    "termination date": ["end date", "expiration date", "contract expiration"],
    
    # Assignment & Transfer
    "assignment": ["assign", "transfer", "reassign", "delegation"],
    "non-assignable": ["non-assignable", "no assignment", "assignment prohibited"],
    "consent to assignment": ["assignment consent", "approval of assignment"],
    
    # Data Protection & Privacy
    "data protection": ["data privacy", "personal data", "data security"],
    "gdpr": ["gdpr compliance", "general data protection"],
    "privacy": ["private", "personal data", "privacy protection"],
    "data security": ["security measures", "data protection", "information security"],
    "breach notification": ["notification requirement", "breach reporting"],
    
    # Non-Compete & Non-Solicit
    "non-compete": ["non-competition", "compete restriction", "competition clause"],
    "non-solicitation": ["non-solicit", "solicitation prohibition", "employee non-solicit"],
    
    # SLA & Performance
    "service level": ["sla", "performance standard", "uptime"],
    "sla": ["service level agreement", "performance level"],
    "uptime": ["availability", "uptime requirement", "service availability"],
    "performance metric": ["performance standard", "performance measure"],
    
    # Entire Agreement & Amendment
    "entire agreement": ["integration clause", "entire understanding"],
    "amendment": ["modify", "modification", "change", "revised"],
    "waiver": ["waive", "waived", "waiver of"],
    
    # Severability & Interpretation
    "severability": ["severable", "severable clause", "validity clause"],
    "interpretation": ["interpret", "construction", "meaning"],
    "definitions": ["define", "defined term", "definition"],
}

# ============================================================================
# RANKING WEIGHTS
# ============================================================================

RANKING_WEIGHTS: Final[Dict[str, float]] = {
    "semantic_similarity": 0.40,        # FAISS semantic score
    "keyword_overlap": 0.25,            # BM25 keyword score
    "parent_relevance": 0.15,           # Parent chunk relevance boost
    "chunk_position": 0.10,             # Proximity to start of document
    "citation_density": 0.05,           # References/citations per chunk
    "length_normalization": 0.05,       # Chunk length optimization
}

# ============================================================================
# RETRIEVAL CONFIGURATION
# ============================================================================

RETRIEVAL_CONFIG: Final[Dict[str, int]] = {
    "default_top_k": 10,                # Default retrieval limit
    "max_top_k": 50,                    # Maximum retrieval limit
    "min_semantic_score": 0.3,          # Minimum semantic similarity threshold
    "min_keyword_score": 0.1,           # Minimum BM25 score threshold
    "min_combined_score": 0.25,         # Minimum combined ranking score
    "chunk_overlap": 2,                 # Sentences overlap between chunks
    "dedupe_threshold": 0.85,           # Similarity threshold for deduplication
}

# ============================================================================
# CHUNK QUALITY FACTORS
# ============================================================================

CHUNK_QUALITY_FACTORS: Final[Dict[str, float]] = {
    "min_length": 50,                   # Minimum characters for quality chunk
    "max_length": 5000,                 # Maximum characters for quality chunk
    "optimal_length": 1000,             # Optimal chunk length
    "citation_weight": 0.1,             # Weight for citation presence
}

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

RETRIEVAL_LOGGER_NAME: Final[str] = "legalgpt.retrieval"
ENABLE_RETRIEVAL_DEBUG: Final[bool] = True  # Set to False in production if verbose

# ============================================================================
# PERFORMANCE TARGETS
# ============================================================================

PERFORMANCE_TARGETS: Final[Dict[str, int]] = {
    "max_query_expansion_ms": 10,       # Max time for query expansion
    "max_semantic_retrieval_ms": 200,   # Max time for FAISS retrieval
    "max_keyword_retrieval_ms": 150,    # Max time for BM25 retrieval
    "max_ranking_ms": 100,              # Max time for context ranking
    "max_deduplication_ms": 50,         # Max time for deduplication
    "max_total_retrieval_ms": 500,      # Max total retrieval time
}

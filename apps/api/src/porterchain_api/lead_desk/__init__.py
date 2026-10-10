"""Lead desk — read-only helpers that get every lead a reply in < 5 minutes.

Pure computation over a lead (fit score, instant quote, reply draft, speed
metrics). Writes stay in ``collaboration_engine`` (model ownership §3.2.6).
"""

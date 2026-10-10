"""Interac e-Transfer reconciliation: parse bank notification emails, verify they are
genuinely from Interac, propose an invoice match, and wait for one-click admin approval.

Nothing here sends email or applies money on its own.
"""

"""Customer fast-book: guest checkout, one tracking page actions, Send-again + email preferences.

Book in ~30 seconds with no account: the calculator price becomes a quote, the guest pays with
Stripe Checkout (cards, Apple Pay, Google Pay), and a pending customer row is created from the
email. The first Clerk sign-in (magic link in the confirmation email) adopts it (C-14).
"""

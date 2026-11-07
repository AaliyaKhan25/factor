# Demo script (about 5 minutes)

1. Sign up, create the business, show the business code.
2. Load the sample catalog. Show stock, a made-to-order item and a rental.
3. Run `scripts/simulate_inbox.py` with chat c1: the agent answers with availability, an exact price and a hold. The order appears in the sheet.
4. Chat c3 (custom request): the agent hands over and the owner sees a summary card.
5. Upload the sample bank statement and match the payment for c5. Reuse the same reference on a second order to show the duplicate check.
6. Mark packed with a photo, then shipped, then delivered with the code.
7. Chat c6 (not delivered): triage checks tracking and the evidence timeline, and suggests a decision.
8. Show a second teammate joining with the business code and waiting for approval.
9. Show the dashboard, overdue returns and the activity log.

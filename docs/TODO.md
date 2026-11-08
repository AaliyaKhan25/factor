# Known gaps

- Memberships need a `department_id`, and `Department` must be a real model, for department heads to see their department's assets.
- Business needs an `asset_prefix` setting (default FX) for asset tags such as FX-0001.
- Rate limiting for business-code guesses and login (`core/rate_limit.py`).
- Alembic: generate the first migration once the models settle.
- Forgot password needs an email sender.
- Everything marked as a stub in the file tree.
- docker-compose has only the database. Add api and web services.
- Web CI.
- Check whether the BharatCode API supports tool calling and speech. If not, return JSON and run the tools in code, and pick a separate speech service.
- Instagram production access needs Meta app review.
- Check telecom and data-protection rules before adding reminder calls.
- Talk to real sellers and replace assumptions with their numbers.
- Outbound replies: owner and agent messages are saved in the thread but not sent through the Instagram or WhatsApp APIs yet.
- The agent is rule-based. An LLM could improve intent detection, but prices, stock and escalation must stay in code.
- Instagram webhooks give a numeric sender id, not the @handle, so names show as "Instagram user 1234" until profile lookup is added.
- Payments: orders have a payment status but statement matching and unique amounts are not built.
- Webhook and Google sign-in code is tested with mocks. It has not been run against real Meta or Google.
- Dashboard day buckets use UTC, not IST.

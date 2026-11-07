# Architecture

## Layers

1. **Core (the problem statement):** organisation setup, assets and lifecycle, allocation and transfers, bookings, maintenance, audits, dashboard, reports, notifications, activity log.
2. **Seller layer:** inbox agent, catalog and holds, orders, payment verification, delivery proof, disputes, customer book, Google Sheet sync.
3. **Input layer:** DM webhooks, share or paste, voice notes, public pay, track and complain pages.

## Request flow

Router (thin) -> service (rules) -> model. Routers validate input and permissions only. Services hold the business rules, so the AI agent and the HTTP API share the same logic.

## AI boundary

The AI extracts intent and writes replies. Services decide availability, price and holds. `ai/guardrails.py` rejects any reply that quotes a price or promise the tools did not return. Every AI result is a suggestion the owner can override.

## Business scope

Every record carries a business id. `deps.get_ctx` resolves the caller's active business, and every query filters by it. `tests/test_business_scope.py` proves one business cannot reach another.

## Access

Signup makes a plain account. Creating a business makes you its admin. Joining by code creates a pending Employee with no access. Only the admin approves and grants permissions. The admin role cannot be assigned.

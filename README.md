# Factor

Factor is a free, mobile-first operations app for solo Instagram and WhatsApp sellers in India. It turns DMs into orders, verifies payments, keeps delivery proof and sorts disputes by evidence, so one owner can run hundreds of orders.

It is built for the BharatCode Build League on the BharatCode API, and follows the AssetFlow problem statement: assets and lifecycle, allocation with a conflict rule, bookings without overlaps, maintenance approval, audits, role-based access, notifications and logs.

## Main ideas

- An AI inbox agent answers standard requests with real availability and exact prices, and hands custom requests to the owner.
- Code decides availability and price. The AI never invents either.
- Every order has an evidence timeline: policy accepted, payment verified, packed, shipped, delivered.
- Disputes are checked against that timeline. Clear cases resolve automatically, unclear ones go to the owner.
- One owner by default. Teammates join with a business code and get no access until the owner approves.

## Run the API

```
cd apps/api
pip install -r requirements.txt
python -m pytest -q
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs. It uses a local SQLite file unless `DATABASE_URL` is set. `docker compose up -d db` starts Postgres.

## Run the web app

```
cd apps/web
npm install
npm run dev
```

## Where things are

- `docs/architecture.md`: how the pieces fit
- `docs/problem-statement-mapping.md`: every requirement and where it lives
- `docs/workflow.md`, `docs/permissions.md`, `docs/data-model.md`
- `docs/decisions.md`: deliberate trade-offs
- `docs/demo-script.md`: the demo, step by step
- `docs/TODO.md`: known gaps
- `scripts/sample_data/`: fictional chats, catalog and bank statement

## Status

Working and tested (71 API tests, plus a browser run of the main flow):
accounts and Google sign-in, business and business code, team approval, catalog, orders with stock and capacity checks and an evidence timeline, the inbox with a rule-based agent (answers price and stock questions, books orders on "confirm", hands custom requests, bargaining, complaints and payment claims to the owner), Meta webhooks for Instagram and WhatsApp, a live-updating overview, customers.
Everything else is scaffolded. See `docs/TODO.md`.

## Try the demo without Meta access

Sign up, create a business, add two catalog items, open Inbox and press "Simulate a DM". Pick a message and watch it land under "Handled by agent" or "Needs you". The lists refresh every few seconds on their own.

## Turn on Google sign-in

Create an OAuth client (type Web) in Google Cloud, add `http://localhost:3000` as an authorised JavaScript origin, and start the API with `GOOGLE_CLIENT_ID=<your id>`. The button appears by itself.

## Connect real Instagram or WhatsApp

Settings > Connect Instagram gives you a callback URL and a verify token for the Meta app. Meta needs a public HTTPS address (a tunnel such as ngrok works for testing) and app review before it delivers real customer DMs. Set `META_APP_SECRET` so incoming webhooks are signature-checked. Sending replies back out through Meta is not built yet.

## Honest limits

- Instagram messaging needs Meta app review before it reaches real customers. The demo uses test accounts or a simulated inbox.
- Payments are confirmed by the owner against a bank statement. There is no paid gateway.
- The AI suggests, and the owner confirms any rejection.

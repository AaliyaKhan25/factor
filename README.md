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

Core workflows include accounts and Google sign-in, business and business code, team approval, catalog, orders with stock and capacity checks, evidence timelines, a rule-based inbox agent, Meta webhooks, live overview, customers, inventory history, one-way Sheets snapshots, manual and signed courier tracking, and proposed voice actions. Real carrier APIs and delivery of replies through Meta still require provider credentials and their send APIs.

## Try the demo without Meta access

Sign up, create a business, add two catalog items, open Inbox and press "Simulate a DM". Pick a message and watch it land under "Handled by agent" or "Needs you". The lists refresh every few seconds on their own.

## Turn on Google sign-in

Create an OAuth client (type Web) in Google Cloud, add `http://localhost:3000` as an authorised JavaScript origin, and start the API with `GOOGLE_CLIENT_ID=<your id>`. The button appears by itself.

## Connect real Instagram or WhatsApp

Settings > Connect Instagram gives you a callback URL and a verify token for the Meta app. Meta needs a public HTTPS address (a tunnel such as ngrok works for testing) and app review before it delivers real customer DMs. Set `META_APP_SECRET` so incoming webhooks are signature-checked. Sending replies back out through Meta is not built yet.

## Inventory, Sheets, courier tracking and voice

- Inventory keeps a movement ledger for opening stock, orders, cancellations, restocks and counts. The Inventory screen refreshes live and shows low or empty stock; made-to-order products show open orders against capacity.
- Google Sheets sync is one way from Factor to three tabs: Orders, Inventory and Stock log. Set `GOOGLE_SERVICE_ACCOUNT_JSON` on the API, share the destination sheet with that service account email, then paste the Sheet link in Settings. Cells are sent as `RAW` text. The app does not import edits from Sheets.
- Courier tracking works in manual mode without any connection. Sellers can add a courier name, AWB and optional URL, then record status updates. Optional generic signed webhooks and adapter connections are configured per seller. Set `COURIER_ENCRYPTION_KEY` to a Fernet key before creating a connection with credentials; generate one with `python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`.
- Voice commands use the server side `GNANI_API_KEY` for transcription and speech output. The browser records WAV audio and sends it to the API; the key is never sent to the browser. Read commands can run immediately. Orders, restocks and replies show a short lived proposal that needs confirmation; reply confirmation can also be spoken. Teammate approval is tap only.
- Run the web capture state tests with `cd apps/web && npm test`; run the API suite with `cd apps/api && python -m pytest -q`.

## Honest limits

- Instagram messaging needs Meta app review before it reaches real customers. The demo uses test accounts or a simulated inbox.
- Payments are confirmed by the owner against a bank statement. There is no paid gateway.
- The AI suggests, and the owner confirms any rejection.

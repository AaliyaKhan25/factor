.PHONY: db-up api-install api-test api-dev web-install web-dev
db-up:
	docker compose up -d db
api-install:
	cd apps/api && pip install -r requirements.txt
api-test:
	cd apps/api && python -m pytest -q
api-dev:
	cd apps/api && uvicorn app.main:app --reload
web-install:
	cd apps/web && npm install
web-dev:
	cd apps/web && npm run dev

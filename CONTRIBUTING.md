# Contributing

- Branch per feature. Keep pull requests small.
- Routers stay thin. Rules live in `services/`.
- Anything with an access rule gets a test. See `tests/` for the pattern.
- The AI suggests. Code decides prices, availability and permissions.
- Never commit `.env` or real keys. Copy `.env.example`.
- Run `python -m pytest -q` in `apps/api` before pushing.

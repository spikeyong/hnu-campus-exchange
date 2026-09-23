# Project Rules

## Mission

Build the MVP for the Hainan University Campus Resource Exchange and Skill Mutual-Aid Platform. The product scope and acceptance criteria are defined in `PRD.md`.

## Required context

At the beginning of every session, read:

1. `CLAUDE.md`
2. `progress.txt`
3. `lessons.md`
4. The relevant sections of `PRD.md`, `APP_FLOW.md`, `TECH_STACK.md`, `FRONTEND_GUIDELINES.md`, `BACKEND_STRUCTURE.md`, and `IMPLEMENTATION_PLAN.md`

## Technical rules

- Use Python 3.12, FastAPI, SQLAlchemy, Alembic, MySQL, Vue 3, TypeScript and Element Plus according to `TECH_STACK.md`.
- Do not introduce a new package, framework, database, payment service or authentication provider without updating `TECH_STACK.md` first.
- Keep API routes thin. Put business rules in services and data access in repositories.
- Validate input with Pydantic and enforce authorization in the backend.
- Use migrations for schema changes. Do not modify production schema manually.
- Use the transaction state machine defined in `BACKEND_STRUCTURE.md`.
- Do not let the frontend invent or skip transaction states.

## Product rules

- Do not expand scope beyond `PRD.md` without an explicit decision.
- The platform does not hold money or claim to verify offline WeChat payments.
- Only both-party confirmation can complete a transaction.
- Only completed transactions can create reviews.
- Disputed transactions pause reviews and credit settlement.
- Student verification materials, payment QR codes and transaction messages are private.

## Security rules

- Never commit `.env`, tokens, passwords, private keys or real student data.
- Never log passwords, complete student numbers, verification materials or payment details.
- Hash passwords with Argon2. Encrypt sensitive fields where required.
- Check ownership or participant permissions on every read and write endpoint.
- Keep uploaded private files behind an authorized download endpoint.

## Working method

- Make one small, testable change at a time.
- Before implementing a feature, identify its requirement, route, data model, state changes and acceptance test.
- After implementing a feature, run the smallest relevant test set and update `progress.txt`.
- When a correction reveals a reusable rule, add it to `lessons.md` and update this file if the rule is permanent.
- Explain changed files and verification results in plain language.
- Do not claim a feature works without running its test or demonstrating its flow.

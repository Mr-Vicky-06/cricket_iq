# CricketIQ Frontend API Contract & Type Generation

This directory contains the typed API client, contract types, domain validation, and auto-generated OpenAPI type definitions for connecting to the CricketIQ backend.

---

## 1. Files

- **`openapi.d.ts`**: Auto-generated TypeScript definitions generated from the FastAPI backend's `http://127.0.0.1:8000/openapi.json`.
- **`types.ts`**: Domain-level ergonomic TypeScript interfaces and types, verified for 100% contract parity with `openapi.d.ts` and FastAPI Pydantic schemas.
- **`client.ts`**: Production fetch client featuring configurable timeout (30s default), abort controller, request ID forwarding, and error normalization.
- **`urlValidator.ts`**: Strict HTTPS domain allowlist validator (`icc-cricket.com`, `lords.org`) preventing SSRF and malicious external redirects.

---

## 2. Re-generating OpenAPI Types

To re-generate `openapi.d.ts` when backend schemas change:

1. Ensure the FastAPI backend is running locally on port 8000:
   ```powershell
   .venv\Scripts\uvicorn cricketiq.backend.app.main:app --port 8000 --host 127.0.0.1
   ```
2. Run the type generation script from the `frontend/` directory:
   ```powershell
   pnpm api:types
   ```
   Or from repository root:
   ```powershell
   pnpm --dir frontend run api:types
   ```

# CLAUDE.md

Always read MASTERPLAN.md before working. Implement only the chunk asked for. Keep code simple.

## Coding rules

### Backend
- Use plain `def` routes, never `async def`. They use sync SQLAlchemy and LLM clients, so FastAPI runs them in its thread pool and one slow call doesn't block the server.
- Create tables with `Base.metadata.create_all`; no migrations. Changing the schema means running `python -m app.seed --reset`.
- **Money:** compute in `Decimal` and store as `Numeric`. At the API boundary, rupee amounts become `int` (rounded half-up) and rates become `float`.
- All API JSON is **camelCase**: every schema inherits `BaseSchema` (alias generator `to_camel`, `populate_by_name=True`, `from_attributes=True`).
- Validate everything with Pydantic `Field` constraints.
- Errors always use this format: `{"error": {"code": "...", "message": "...", "requestId": "..."}}`. Raise `AppError(status, code, message)`.
- The LLM **never** does arithmetic. Use `temperature=0`.
- Call `mask_pii` before any LLM call or log write. Every important action calls `log_audit`.
- Status changes go **only** through `set_status` (the state machine).
- Keep code simple and readable, with small functions and docstrings. No over-engineering.

### Frontend
- Functional components only, using `useState`, `useEffect`, Context and axios. No other state or data-fetching libraries.
- **Every API call handles 4 states:** loading (Spinner), success, empty (EmptyState with a next action), and error (toast with `getErrorMessage(err)`).
- Format money with `formatINR` (`₹5,00,000`). Use Badge colors consistently: green = OK, amber = attention, red = blocked.
- No placeholder or "coming soon" UI in the final app. Disable buttons while a request is running.
- Tailwind for styling: clean, white background, navy headings (`#0B2545`), teal accents (`#13A89E`), responsive layouts.

### Fairness
- There are NO gender, religion, caste, marital-status or age fields anywhere.

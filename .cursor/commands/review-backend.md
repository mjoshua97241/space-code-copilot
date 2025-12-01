# review-backend

# Command: /review-backend

When I invoke `/review-backend <path>`, you will:

- Read the specified Python file.
- Check for:
  - Consistency with project patterns in .cursor/memory_bank/systemPatterns.md.
  - FastAPI / pydantic best practices.
  - Clarity of function boundaries and side effects.
- Return:
  - A bullet list of issues.
  - Concrete patches or code suggestions.

Prompt template:

`/review-backend backend/app/services/compliance_checker.py`

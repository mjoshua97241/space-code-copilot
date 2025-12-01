# Command: /use-lesson-pattern

When I invoke `/use-lesson-pattern <description>`, you will:

- Search internal/lessons/ for any relevant examples.
- Show me:
  - The specific example file(s) you are using.
  - The minimal snippet you propose to adapt.
  - The adapted version, rewritten to fit this project:
    - Correct module paths (backend/app/_, frontend/src/_).
    - Domain names: Room, Door, Rule, Issue, etc.
- Do NOT copy entire files. Only patterns.

Prompt template example:

`/use-lesson-pattern Implement a LangChain RAG retrieval helper similar to the lesson that used Qdrant, but adapted to backend/app/services/vector_store.py in this project.`

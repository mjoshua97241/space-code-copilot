# Project Brief

Name: Code-Aware Space Planning Copilot

Goal:
Help architects and designers check early space planning (rooms, doors, corridors) against building codes and internal standards, without relying on full BIM.

Scope:

- One sample project for MVP: 1 floor plan, 1–2 code PDFs, CSV schedules for rooms and doors, overlay JSON for viewer.
- Backend: FastAPI + LangChain/LangGraph agents to:
  - Parse CSV schedules into Room and Door models.
  - Load building code PDFs, chunk, embed, and store in vector DB.
  - Seed or extract structured rules (Rule models).
  - Run compliance checks → Issue models.
- Frontend: React + TS + Vite with:
  - Left: static floor plan image + overlays from JSON.
  - Bottom: issue list.
  - Right: chat over RAG + issues.

Non-goals (for MVP):

- No real BIM/IFC parsing.
- No multi-floor, no complex auth, no real-time collaboration.

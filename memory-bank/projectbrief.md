# Project Brief

Name: Code-Aware Space Planning Copilot

Goal:
Help architects and designers check early space planning (rooms, doors, corridors) against building codes and internal standards, without relying on full BIM.

**Context**: Architects work across multiple jurisdictions, each with different building codes (e.g., National Building Code of Philippines, IBC, local codes). Reading and familiarizing with many code documents is time-consuming. This tool uses LLM/RAG to ingest multiple code PDFs and answer questions without requiring architects to read entire documents.

Scope:

- One sample project for MVP: 1 floor plan, 1–2 code PDFs, CSV schedules for rooms and doors, overlay JSON for viewer.
- Backend: FastAPI + LangChain/LangGraph agents to:
  - Parse CSV schedules into Room and Door models.
  - Load building code PDFs (supports multiple codes/jurisdictions), chunk, embed, and store in vector DB.
  - Seed or extract structured rules (Rule models) from code PDFs using LLM.
  - Run compliance checks → Issue models.
- Frontend: Plain HTML/CSS + minimal inline JavaScript, served directly by FastAPI:
  - Single-page web UI (`app/templates/index.html`) with:
    - Left: static floor plan image + overlays from JSON.
    - Bottom: issue list.
    - Right: chat over RAG + issues.
  - No Node/npm, no React, no build toolchain.
  - Static assets served via FastAPI (`/static/plan.png`, `/static/styles.css`).

Non-goals (for MVP):

- No real BIM/IFC parsing.
- No multi-floor, no complex auth, no real-time collaboration.

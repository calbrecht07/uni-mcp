# uni-mcp

A full-stack MCP-enabled application with a Python backend and React frontend.

## Architecture Overview

The project is split into three main layers:

- `backend/`: FastAPI-based orchestration and RAG-oriented service logic.
- `frontend/`: React dashboard and onboarding interface for user interactions.
- Root configuration: workspace-level Node tooling and shared project settings.

## Repository Structure

- `backend/` contains routers, providers, and service modules for intent routing, identity mapping, and tool invocation.
- `frontend/` contains the dashboard UI, onboarding flows, and client-side build configuration.

## Development Notes

- Keep secrets in local `.env` files only; use `*.template` files for shared configuration.
- Do not commit local runtime artifacts (virtualenvs, caches, DB files, build outputs).

# Uni-MCP: Unified Intelligent Workflow Agent

**Note:** This repository is a sanitised technical showcase of a private development project. It is maintained to demonstrate full-stack architecture, intent-based routing, and cross-platform identity management.

##  Overview
Uni-MCP unifies fragmented enterprise tools into a single intelligent layer. It allows teams to query documentation and manage tasks across Slack, Notion, and Jira without switching platforms.

---

##  Technical Architecture & "Spikes"

### 1. Intelligence & Routing Layer (`/backend/services`)
Instead of a "brute force" approach that sends every query to costly LLM's, I designed an **Intent Recognition Gateway**:
* **Cost OptimizatsationThe gateway classifies queries to determine if they require a Vector DB search, a live API call, or a simple conversational response.
* **Latency Reduction:** This reduces unnecessary token consumption and significantly speeds up response times for "shallow" queries.

### 2. Multi-Platform Identity Schema (`/backend/models`)
A core challenge was the "Identity Problem" (User X in Slack = User Y in Jira). 
* **Unified Schema:** I implemented a mapping layer that reconciles disparate IDs across Slack, Jira, and Notion, ensuring the assistant maintains a consistent context of "who" is asking, regardless of the platform.

### 3. Frictionless Onboarding & Integration (`/frontend/src`)
To solve the adoption hurdle, I built:
* **Click-and-Play Connectors:** Automated OAuth and configuration flows for Slack and Jira.
* **Native Slack Bot:** Deployed as a primary interface to meet users where they already work, eliminating the need for a separate platform.

---

##  Repository Structure
* `/backend`: FastAPI-based service layer with modular routers and providers.
* `/frontend`: React/Vite dashboard for managing integrations and monitoring agent activity.
* `package-lock.json` & `requirements.txt`: Locked dependencies for reproducible builds.

---

## 🛠️ Tech Stack
* **Backend:** Python (FastAPI), Pydantic, Redis
* **Frontend:** React, Vite, Tailwind CSS, Shadcn/UI

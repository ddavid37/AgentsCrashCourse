# AGENTS.md

## Cursor Cloud specific instructions

### Overview

This is an educational course repository ("Master AI Agentic Engineering") with Jupyter notebooks and Python scripts organized into 6 weekly modules. It is **not** a production application — the "services" are individual lab scripts/notebooks and Gradio-based demo apps.

### Key Development Commands

- **Install dependencies:** `uv sync` (uses `pyproject.toml` + `uv.lock`)
- **Run a script:** `uv run python <script.py>`
- **Run a notebook cell:** use `uv run` as the kernel, or activate `.venv`
- **CrewAI (Week 3):** installed as a uv tool (`uv tool install crewai==0.130.0 --python 3.12`); run with `crewai run` inside a crew project directory
- **Playwright (Weeks 4 & 6):** `uv run playwright install --with-deps chromium` (Linux)

### Non-obvious Caveats

1. **OpenAI Agents SDK import:** The package is `openai-agents` but the import is `from agents import Agent, Runner` (not `from openai_agents`).
2. **No global linter/test suite:** This repo has no unified lint or test command. Each week's labs are independent notebooks. To verify the environment, run `uv run python setup/diagnostics.py`.
3. **`.env` file:** Labs use `python-dotenv` and call `load_dotenv(override=True)`. Ensure a `.env` file exists at the project root with at least `OPENAI_API_KEY=<key>`. The key is also needed as an environment variable for some scripts.
4. **Gradio apps:** Many labs launch Gradio UIs on port 7860. Use `server_name='0.0.0.0'` for cloud environments.
5. **Node.js:** Required for MCP servers (Weeks 4 & 6) via `npx`. v22+ is needed.
6. **The notebook `1_foundations/1_lab1.ipynb`** in this fork has been modified to use Azure OpenAI. Standard OpenAI usage: `from openai import OpenAI; client = OpenAI(); client.chat.completions.create(model='gpt-4.1-nano', ...)`.

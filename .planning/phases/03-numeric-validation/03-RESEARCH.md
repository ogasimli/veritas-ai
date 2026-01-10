# Phase 03: Google ADK Research

**Research Date**: 2026-01-11  
**Research Focus**: Google Agent Development Kit (ADK) patterns for building production-ready agents  
**Confidence**: High (based on official ADK docs and adk-samples repo)

## Sources

- [ADK Official Documentation](https://google.github.io/adk-docs)
- [ADK Samples Repository](https://github.com/google/adk-samples) (specifically `python/agents/llm-auditor`)
- ADK Python package version: `^1.0.0`

---

## 1. Standard Stack

### Core Dependencies

```toml
[tool.poetry.dependencies]
python = "^3.10"
google-adk = "^1.0.0"
google-cloud-aiplatform = { extras = ["adk", "agent-engines"], version = "^1.93.0" }
google-genai = "^1.9.0"
pydantic = "^2.10.6"
python-dotenv = "^1.0.1"

[tool.poetry.group.dev]
optional = true

[tool.poetry.group.dev.dependencies]
google-adk = { version = "^1.0.0", extras = ["eval"] }
pytest = "^8.3.5"
pytest-asyncio = "^0.26.0"

[tool.poetry.group.deployment]
optional = true

[tool.poetry.group.deployment.dependencies]
absl-py = "^2.2.1"
```

### Key Imports

```python
# Core ADK
from google.adk import Agent
from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent
from google.adk.runners import InMemoryRunner
from google.adk.tools import google_search  # Built-in tools

# For programmatic access
from google.genai.types import Part, UserContent

# For evaluation
from google.adk.evaluation import AgentEvaluator

# For Vertex AI deployment
from vertexai import agent_engines
from vertexai.preview.reasoning_engines import AdkApp
```

---

## 2. Folder Structure (adk-samples Pattern)

### Project-Level Structure

```
agents/
├── my_agent/                    # Agent project directory (kebab-case for dir)
│   ├── my_agent/                # Python package (snake_case, matches pyproject.toml name)
│   │   ├── __init__.py          # Imports agent module
│   │   ├── agent.py             # Root agent definition, exports `root_agent`
│   │   └── sub_agents/          # Sub-agents directory (if multi-agent)
│   │       ├── __init__.py      # Exports sub-agents
│   │       ├── planner/
│   │       │   ├── __init__.py  # Exports agent from agent.py
│   │       │   ├── agent.py     # Sub-agent definition
│   │       │   └── prompt.py    # Prompt/instruction constants
│   │       └── validator/
│   │           ├── __init__.py
│   │           ├── agent.py
│   │           └── prompt.py
│   ├── tests/                   # Unit tests
│   │   └── test_agents.py       # pytest tests for agent functionality
│   ├── eval/                    # Evaluation tests
│   │   ├── data/                # Eval test data files
│   │   │   ├── case1.test.json  # Individual test cases (.test.json suffix)
│   │   │   └── test_config.json # Optional test configuration
│   │   └── test_eval.py         # Pytest wrapper for AgentEvaluator
│   ├── deployment/              # Vertex AI deployment scripts
│   │   └── deploy.py            # Deployment script using AdkApp
│   ├── .env.example             # Environment variable template
│   ├── .env                     # Local environment (gitignored)
│   ├── pyproject.toml           # Poetry project config
│   └── README.md                # Agent documentation
```

### Critical File Patterns

#### `__init__.py` (root package)
```python
"""Agent description."""
from . import agent
```

#### `agent.py` (root agent)
```python
"""Root agent definition."""
from google.adk.agents import SequentialAgent
from .sub_agents.planner import planner_agent
from .sub_agents.validator import validator_agent

root_agent = SequentialAgent(
    name='my_agent',
    description='Agent purpose',
    sub_agents=[planner_agent, validator_agent],
)
```

#### Sub-agent `__init__.py`
```python
"""Sub-agent exports."""
from .agent import my_sub_agent
```

#### Sub-agent `agent.py`
```python
"""Sub-agent definition."""
from google.adk import Agent
from . import prompt

my_sub_agent = Agent(
    model='gemini-2.5-flash',  # or 'gemini-2.5-pro'
    name='my_sub_agent',
    instruction=prompt.INSTRUCTION,
    tools=[...],
)
```

#### Sub-agent `prompt.py`
```python
"""Prompts for the sub-agent."""

INSTRUCTION = """
Your detailed instruction here.

# Section 1
Content...

# Section 2
Content...
"""
```

---

## 3. ADK CLI Commands

### Running Agents Locally

```bash
# Terminal CLI - interactive chat
adk run my_agent

# Web UI - browser-based interface
adk web --port 8000
```

**Important**: Run from the **parent directory** containing the agent folder:
```bash
# If agent is at agents/my_agent/
cd agents/
adk run my_agent
adk web
```

### Deployment to Vertex AI Agent Engine

```bash
# CLI deployment
adk deploy agent_engine \
  --project=$PROJECT_ID \
  --region=$LOCATION_ID \
  --staging_bucket=$GCS_BUCKET \
  --display_name="My Agent" \
  my_agent
```

### Evaluation CLI

```bash
# Run eval on eval set file
adk eval \
  <AGENT_MODULE_PATH> \
  <EVAL_SET_FILE_PATH> \
  [--config_file_path=<CONFIG_PATH>] \
  [--print_detailed_results]

# Example
adk eval \
  my_agent \
  my_agent/eval/data/case1.test.json
```

---

## 4. Pytest Patterns

### Unit Tests (`tests/test_agents.py`)

```python
"""Test cases for the agent."""
import textwrap
import dotenv
import pytest
from google.adk.runners import InMemoryRunner
from google.genai.types import Part, UserContent
from my_agent.agent import root_agent

pytest_plugins = ("pytest_asyncio",)

@pytest.fixture(scope="session", autouse=True)
def load_env():
    dotenv.load_dotenv()

@pytest.mark.asyncio
async def test_happy_path():
    """Runs the agent on a simple input and expects a normal response."""
    user_input = "Your test input here"

    runner = InMemoryRunner(agent=root_agent)
    session = await runner.session_service.create_session(
        app_name=runner.app_name, user_id="test_user"
    )
    content = UserContent(parts=[Part(text=user_input)])
    response = ""
    async for event in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=content,
    ):
        if event.content.parts and event.content.parts[0].text:
            response = event.content.parts[0].text

    # Assert expected behavior
    assert "expected_keyword" in response.lower()
```

### Running Tests

```bash
# Install dev dependencies
poetry install --with dev

# Run unit tests
python3 -m pytest tests

# Run evaluations
python3 -m pytest eval
```

---

## 5. Evaluation Data Pattern

### Test File Format (`.test.json`)

Files must use `.test.json` suffix. Each file contains a single session with one or more turns:

```json
{
  "eval_set_id": "my_agent_test_set",
  "name": "",
  "description": "Eval set for testing X behavior",
  "eval_cases": [
    {
      "eval_id": "eval_case_001",
      "conversation": [
        {
          "invocation_id": "uuid-here",
          "user_content": {
            "parts": [{ "text": "User query here" }],
            "role": "user"
          },
          "final_response": {
            "parts": [{ "text": "Expected response text" }],
            "role": "model"
          },
          "intermediate_data": {
            "tool_uses": [
              {
                "args": { "arg1": "value1" },
                "name": "tool_name"
              }
            ],
            "intermediate_responses": []
          }
        }
      ],
      "session_input": {
        "app_name": "my_agent",
        "user_id": "test_user",
        "state": {}
      }
    }
  ]
}
```

### Simplified Format (also valid)

```json
[
  {
    "query": "User query here",
    "expected_tool_use": [],
    "reference": "Expected response text"
  }
]
```

### `test_eval.py` Pattern

```python
"""Evaluation tests for agent."""
import pathlib
import dotenv
import pytest
from google.adk.evaluation import AgentEvaluator

pytest_plugins = ("pytest_asyncio",)

@pytest.fixture(scope="session", autouse=True)
def load_env():
    dotenv.load_dotenv()

@pytest.mark.asyncio
async def test_all():
    """Test the agent's basic ability on a few examples."""
    await AgentEvaluator.evaluate(
        "my_agent",  # Agent module name
        str(pathlib.Path(__file__).parent / "data"),  # Path to eval data
        num_runs=5,  # Number of runs per test case
    )
```

---

## 6. Vertex AI Agent Engine Deployment

### Deployment Script (`deployment/deploy.py`)

```python
"""Deployment script for agent."""
import os
from absl import app, flags
from dotenv import load_dotenv
from my_agent.agent import root_agent
import vertexai
from vertexai import agent_engines
from vertexai.preview.reasoning_engines import AdkApp

FLAGS = flags.FLAGS
flags.DEFINE_string("project_id", None, "GCP project ID.")
flags.DEFINE_string("location", None, "GCP location.")
flags.DEFINE_string("bucket", None, "GCP bucket.")
flags.DEFINE_string("resource_id", None, "ReasoningEngine resource ID.")

flags.DEFINE_bool("list", False, "List all agents.")
flags.DEFINE_bool("create", False, "Creates a new agent.")
flags.DEFINE_bool("delete", False, "Deletes an existing agent.")
flags.mark_bool_flags_as_mutual_exclusive(["create", "delete"])

def create() -> None:
    """Creates an agent engine."""
    adk_app = AdkApp(agent=root_agent, enable_tracing=True)
    
    remote_agent = agent_engines.create(
        adk_app,
        display_name=root_agent.name,
        requirements=[
            "google-adk (>=1.0.0)",
            "google-cloud-aiplatform[agent_engines] (>=1.88.0,<2.0.0)",
            "google-genai (>=1.5.0,<2.0.0)",
            "pydantic (>=2.10.6,<3.0.0)",
        ],
        extra_packages=["./my_agent"],  # Include agent package
    )
    print(f"Created remote agent: {remote_agent.resource_name}")

def delete(resource_id: str) -> None:
    remote_agent = agent_engines.get(resource_id)
    remote_agent.delete(force=True)
    print(f"Deleted remote agent: {resource_id}")

def list_agents() -> None:
    remote_agents = agent_engines.list()
    for agent in remote_agents:
        print(f"{agent.name} (\"{agent.display_name}\")")

def main(argv: list[str]) -> None:
    del argv
    load_dotenv()
    
    project_id = FLAGS.project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
    location = FLAGS.location or os.getenv("GOOGLE_CLOUD_LOCATION")
    bucket = FLAGS.bucket or os.getenv("GOOGLE_CLOUD_STORAGE_BUCKET")
    
    vertexai.init(
        project=project_id,
        location=location,
        staging_bucket=f"gs://{bucket}",
    )
    
    if FLAGS.list:
        list_agents()
    elif FLAGS.create:
        create()
    elif FLAGS.delete:
        if not FLAGS.resource_id:
            print("resource_id is required for delete")
            return
        delete(FLAGS.resource_id)

if __name__ == "__main__":
    app.run(main)
```

### Required Environment Variables

```bash
# For Vertex AI deployment
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_CLOUD_PROJECT=<your-project-id>
export GOOGLE_CLOUD_LOCATION=<your-project-location>
export GOOGLE_CLOUD_STORAGE_BUCKET=<your-storage-bucket>

# For local development with API key
export GOOGLE_GENAI_USE_VERTEXAI=false
export GOOGLE_API_KEY=<your-api-key>
```

---

## 7. Don't Hand-Roll

| Problem | Use This Instead |
|---------|------------------|
| Agent orchestration | `SequentialAgent`, `ParallelAgent`, `LoopAgent` |
| Session management | `InMemoryRunner.session_service` |
| Evaluation framework | `AgentEvaluator` from `google.adk.evaluation` |
| Web search | `google_search` tool from `google.adk.tools` |
| Code execution | `code_executor` built-in tool |
| Deployment packaging | `adk deploy agent_engine` CLI |
| Tracing/Observability | `AdkApp(enable_tracing=True)` |

---

## 8. Common Pitfalls

### 8.1 Agent Discovery

**Issue**: ADK CLI can't find your agent.

**Fix**: 
- Agent package must export `root_agent` in `agent.py`
- `__init__.py` must import the agent module: `from . import agent`
- Run CLI from parent directory of agent folder

### 8.2 Async Patterns

**Issue**: Tests hang or fail silently.

**Fix**:
- Use `pytest-asyncio` with `pytest_plugins = ("pytest_asyncio",)`
- Mark tests with `@pytest.mark.asyncio`
- Use `runner.run_async()` not `runner.run()` in tests

### 8.3 Environment Variables

**Issue**: API key not found.

**Fix**:
- Use `dotenv.load_dotenv()` in tests and deployment
- Create `.env` file in agent root directory
- Add fixture with `@pytest.fixture(scope="session", autouse=True)`

### 8.4 Deployment Requirements

**Issue**: Deployment fails with missing dependencies.

**Fix**:
- Explicitly list all requirements in `agent_engines.create()`
- Include agent package via `extra_packages=["./my_agent"]`
- Version constraints must use parentheses: `"google-adk (>=1.0.0)"`

### 8.5 Eval File Format

**Issue**: Evaluation tests not discovered.

**Fix**:
- Files must end with `.test.json` suffix
- Use `AgentEvaluator.evaluate()` with directory path, not file path
- Ensure `eval_set_id` is unique per file

---

## 9. Architecture Patterns

### Sequential Pipeline (Recommended for Numeric Validation)

```python
from google.adk.agents import SequentialAgent

pipeline = SequentialAgent(
    name='validation_pipeline',
    description='Sequential validation workflow',
    sub_agents=[
        planner_agent,    # Identify FSLIs
        validator_agent,  # Validate each FSLI
        manager_agent,    # Aggregate results
    ],
)
```

### Parallel Agents (For Independent Validation)

```python
from google.adk.agents import ParallelAgent

parallel_validators = ParallelAgent(
    name='parallel_validators',
    description='Run validators in parallel',
    sub_agents=[
        validator_1,
        validator_2,
    ],
)
```

### Agent with Tools

```python
from google.adk import Agent
from google.adk.tools import code_executor

validator_agent = Agent(
    model='gemini-2.5-flash',
    name='validator_agent',
    instruction=prompt.VALIDATOR_INSTRUCTION,
    tools=[code_executor],  # Built-in code execution
    output_schema=ValidatorOutput,  # Pydantic model for structured output
)
```

---

## 10. Recommendations for Veritas AI

Based on research, refactor current agent structure to:

### Target Structure

```
backend/
├── agents/                      # Top-level agents directory
│   ├── numeric_validation/      # Agent package
│   │   ├── __init__.py
│   │   ├── agent.py             # Root agent (SequentialAgent)
│   │   └── sub_agents/
│   │       ├── __init__.py
│   │       ├── planner/
│   │       │   ├── __init__.py
│   │       │   ├── agent.py
│   │       │   └── prompt.py
│   │       ├── validator/
│   │       │   ├── __init__.py
│   │       │   ├── agent.py
│   │       │   └── prompt.py
│   │       └── manager/
│   │           ├── __init__.py
│   │           ├── agent.py
│   │           └── prompt.py
│   ├── tests/
│   │   └── test_numeric_validation.py
│   ├── eval/
│   │   ├── data/
│   │   │   └── fsli_extraction.test.json
│   │   └── test_eval.py
│   ├── deployment/
│   │   └── deploy.py
│   ├── .env.example
│   └── pyproject.toml
```

### Key Changes from Current Implementation

1. **Separate `agent.py` and `prompt.py`** per sub-agent
2. **Export `root_agent`** from main agent.py
3. **Use `SequentialAgent`** instead of manual orchestration
4. **Add `tests/`, `eval/`, `deployment/`** directories
5. **Use Poetry** with optional dependency groups
6. **Follow `.test.json` format** for eval data

---

## Summary

| Requirement | Pattern/Solution |
|-------------|------------------|
| ADK terminal commands | `adk run`, `adk web` from parent directory |
| pytest for each agent | `tests/test_agents.py` with `InMemoryRunner` |
| adk-samples folder structure | `agent_name/agent.py` + `sub_agents/*/agent.py` + `prompt.py` |
| Vertex AI Agent Engine deployment | `adk deploy agent_engine` or `deployment/deploy.py` script |
| Eval data and test_eval.py | `eval/data/*.test.json` + `AgentEvaluator.evaluate()` |
| agent.py + prompt.py separation | Each sub-agent in own directory with both files |

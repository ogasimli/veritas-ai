# Phase 03: Google ADK Research

**Research Date**: 2026-01-11
**Updated**: 2026-01-12 (added CustomAgent pattern for dynamic parallelism)
**Research Focus**: Google Agent Development Kit (ADK) patterns for building production-ready agents
**Confidence**: High (based on official ADK docs and adk-samples repo)

## Sources

- [ADK Official Documentation](https://google.github.io/adk-docs)
- [ADK Samples Repository](https://github.com/google/adk-samples) (specifically `python/agents/llm-auditor`)
- [Building Dynamic Parallel Workflows in Google ADK](https://dev.to/masahide/building-dynamic-parallel-workflows-in-google-adk-lmn)
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
from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent, BaseAgent
from google.adk.runners import InMemoryRunner
from google.adk.tools import google_search  # Built-in tools
from google.adk.code_executors import BuiltInCodeExecutor

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
│   │       ├── extractor/
│   │       │   ├── __init__.py  # Exports agent from agent.py
│   │       │   ├── agent.py     # Sub-agent definition
│   │       │   ├── prompt.py    # Prompt/instruction constants
│   │       │   └── schema.py    # Pydantic output schemas
│   │       ├── fan_out_verifier/
│   │       │   ├── __init__.py
│   │       │   ├── agent.py     # CustomAgent definition
│   │       │   ├── verifier.py  # Factory function for VerifierAgent
│   │       │   ├── prompt.py
│   │       │   └── schema.py
│   │       └── reviewer/
│   │           ├── __init__.py
│   │           ├── agent.py
│   │           ├── prompt.py
│   │           └── schema.py
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
from .sub_agents.extractor import extractor_agent
from .sub_agents.fan_out_verifier import fan_out_verifier_agent
from .sub_agents.reviewer import reviewer_agent

root_agent = SequentialAgent(
    name='numeric_validation',
    description='Pipeline for financial statement numeric validation',
    sub_agents=[extractor_agent, fan_out_verifier_agent, reviewer_agent],
)
```

#### Sub-agent `__init__.py`
```python
"""Sub-agent exports."""
from .agent import extractor_agent
```

#### Sub-agent `agent.py`
```python
"""Sub-agent definition."""
from google.adk.agents import LlmAgent
from google.adk.planners import BuiltInPlanner
from google.genai import types
from . import prompt
from .schema import ExtractorAgentOutput

extractor_agent = LlmAgent(
    model='gemini-3-pro-preview',
    name='ExtractorAgent',
    instruction=prompt.INSTRUCTION,
    output_key='extractor_output',
    output_schema=ExtractorAgentOutput,
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(thinking_level="high")
    ),
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

#### Sub-agent `schema.py`
```python
"""Output schemas for the sub-agent."""
from typing import List
from pydantic import BaseModel

class ExtractorAgentOutput(BaseModel):
    fsli_names: List[str]
```

---

## 3. CustomAgent Pattern for Dynamic Parallelism

### Problem

ADK's `ParallelAgent` requires a **static list of sub-agents** at initialization time. For **dynamic parallelism** (spawning N agents based on runtime data), we need a different approach.

### Solution: CustomAgent

Create a custom agent that extends `BaseAgent` and dynamically creates a `ParallelAgent` inside `_run_async_impl()`.

### Implementation Pattern

```python
from typing import ClassVar, AsyncGenerator
from google.adk.agents import BaseAgent, ParallelAgent, LlmAgent
from google.adk.events import Event, EventActions
from google.adk.agents.invocation_context import InvocationContext
from google.genai import types


class FanOutVerifierAgent(BaseAgent):
    """
    CustomAgent that dynamically spawns parallel VerifierAgents,
    one per FSLI extracted by ExtractorAgent.

    Maintains ADK observability by using ParallelAgent internally.
    """

    model: str = "gemini-3-pro-preview"

    async def _run_async_impl(
        self,
        ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # 1. Read data from session state (set by previous agent)
        extractor_output = ctx.session.state.get("extractor_output", {})
        fsli_names = extractor_output.get("fsli_names", [])

        if not fsli_names:
            yield Event(
                author=self.name,
                content=types.Content(
                    role="agent",
                    parts=[types.Part(text="No FSLIs found to verify.")]
                )
            )
            return

        # 2. Create fresh agent instances (single-parent rule)
        verifier_agents = [
            create_verifier_agent(
                name=f"verify_{fsli_name.replace(' ', '_')}",
                fsli_name=fsli_name,
                output_key=f"checks:{fsli_name}"
            )
            for fsli_name in fsli_names
        ]

        # 3. Wrap in ParallelAgent for concurrent execution
        parallel = ParallelAgent(
            name="verifier_parallel_block",
            sub_agents=verifier_agents
        )

        # 4. Yield all events (preserves ADK observability)
        async for event in parallel.run_async(ctx):
            yield event
```

### Factory Function for Dynamic Agents

```python
from google.adk.agents import LlmAgent
from google.adk.code_executors import BuiltInCodeExecutor
from .schema import VerifierAgentOutput


def create_verifier_agent(
    name: str,
    fsli_name: str,
    output_key: str
) -> LlmAgent:
    """
    Factory to create a fresh VerifierAgent for a specific FSLI.
    Must create new instances each time (ADK single-parent rule).
    """
    return LlmAgent(
        name=name,
        model="gemini-3-pro-preview",
        instruction=f"""You are verifying the FSLI: {fsli_name}

Analyze the document and perform:
1. In-table sum verification: Check if component parts sum to totals
2. Cross-table consistency: Check if this FSLI matches across tables

Use Python code execution for all mathematical verification.
Output your findings as structured verification checks.""",
        output_key=output_key,
        output_schema=VerifierAgentOutput,
        code_executor=BuiltInCodeExecutor(),
    )
```

### Critical Constraints

1. **Single-Parent Rule**: An agent instance can only have one parent. Always create **fresh instances** for each ParallelAgent.

2. **ClassVar Annotation**: Static class variables need `ClassVar` annotation to prevent Pydantic validation errors.

3. **Event Yielding**: Must yield events from the inner ParallelAgent to preserve ADK observability and tracing.

4. **State Keys**: Use prefixed keys like `checks:{fsli_name}` to prevent collisions.

### Benefits Over Manual asyncio.gather()

| Aspect | Manual asyncio | CustomAgent (ADK) |
|--------|---------------|-------------------|
| Observability | Lost | Preserved via event yielding |
| Session state | Manual management | Native ADK state sharing |
| Tracing/Logging | Custom implementation | Built-in ADK traces |
| Error handling | Manual | ADK framework handles |
| Agent lifecycle | Manual | ADK manages |

---

## 4. ADK CLI Commands

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

## 5. Pytest Patterns

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

## 6. Evaluation Data Pattern

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

## 7. Vertex AI Agent Engine Deployment

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

## 8. Don't Hand-Roll

| Problem | Use This Instead |
|---------|------------------|
| Agent orchestration | `SequentialAgent`, `ParallelAgent`, `LoopAgent` |
| Dynamic parallelism | `CustomAgent` pattern (BaseAgent + ParallelAgent) |
| Session management | `InMemoryRunner.session_service` |
| Evaluation framework | `AgentEvaluator` from `google.adk.evaluation` |
| Web search | `google_search` tool from `google.adk.tools` |
| Code execution | `BuiltInCodeExecutor` from `google.adk.code_executors` |
| Deployment packaging | `adk deploy agent_engine` CLI |
| Tracing/Observability | `AdkApp(enable_tracing=True)` |

---

## 9. Common Pitfalls

### 9.1 Agent Discovery

**Issue**: ADK CLI can't find your agent.

**Fix**:
- Agent package must export `root_agent` in `agent.py`
- `__init__.py` must import the agent module: `from . import agent`
- Run CLI from parent directory of agent folder

### 9.2 Async Patterns

**Issue**: Tests hang or fail silently.

**Fix**:
- Use `pytest-asyncio` with `pytest_plugins = ("pytest_asyncio",)`
- Mark tests with `@pytest.mark.asyncio`
- Use `runner.run_async()` not `runner.run()` in tests

### 9.3 Environment Variables

**Issue**: API key not found.

**Fix**:
- Use `dotenv.load_dotenv()` in tests and deployment
- Create `.env` file in agent root directory
- Add fixture with `@pytest.fixture(scope="session", autouse=True)`

### 9.4 Deployment Requirements

**Issue**: Deployment fails with missing dependencies.

**Fix**:
- Explicitly list all requirements in `agent_engines.create()`
- Include agent package via `extra_packages=["./my_agent"]`
- Version constraints must use parentheses: `"google-adk (>=1.0.0)"`

### 9.5 Eval File Format

**Issue**: Evaluation tests not discovered.

**Fix**:
- Files must end with `.test.json` suffix
- Use `AgentEvaluator.evaluate()` with directory path, not file path
- Ensure `eval_set_id` is unique per file

### 9.6 Single-Parent Rule (CustomAgent)

**Issue**: Agent reuse in ParallelAgent fails.

**Fix**:
- Always create **fresh agent instances** for each ParallelAgent
- Use factory functions to generate new agents
- Never reuse agent instances across parallel blocks

---

## 10. Architecture Patterns

### Sequential Pipeline

```python
from google.adk.agents import SequentialAgent

pipeline = SequentialAgent(
    name='validation_pipeline',
    description='Sequential validation workflow',
    sub_agents=[
        extractor_agent,       # Identify FSLIs
        fan_out_verifier,      # Parallel verification per FSLI
        reviewer_agent,        # Aggregate and format findings
    ],
)
```

### Static Parallel Agents

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

### Dynamic Parallel Agents (CustomAgent)

```python
from google.adk.agents import BaseAgent, ParallelAgent

class FanOutAgent(BaseAgent):
    async def _run_async_impl(self, ctx):
        # Read dynamic data from session state
        items = ctx.session.state.get("items", [])

        # Create fresh agents dynamically
        agents = [create_agent(item) for item in items]

        # Wrap in ParallelAgent
        parallel = ParallelAgent(name="dynamic_block", sub_agents=agents)

        # Yield events to preserve observability
        async for event in parallel.run_async(ctx):
            yield event
```

### Agent with Code Executor

```python
from google.adk.agents import LlmAgent
from google.adk.code_executors import BuiltInCodeExecutor

validator_agent = LlmAgent(
    model='gemini-3-pro-preview',
    name='ValidatorAgent',
    instruction=prompt.INSTRUCTION,
    code_executor=BuiltInCodeExecutor(),  # Exclusive - no other tools
    output_schema=ValidatorOutput,
)
```

---

## 11. Recommendations for Veritas AI

Based on research, the numeric_validation agent structure should be:

### Target Structure

```
backend/
├── agents/                      # Top-level agents directory
│   ├── numeric_validation/      # Agent package
│   │   ├── __init__.py
│   │   ├── agent.py             # Root agent (SequentialAgent)
│   │   └── sub_agents/
│   │       ├── __init__.py
│   │       ├── extractor/       # Identifies FSLI names
│   │       │   ├── __init__.py
│   │       │   ├── agent.py
│   │       │   ├── prompt.py
│   │       │   └── schema.py
│   │       ├── fan_out_verifier/ # CustomAgent for dynamic parallelism
│   │       │   ├── __init__.py
│   │       │   ├── agent.py     # FanOutVerifierAgent (BaseAgent)
│   │       │   ├── verifier.py  # create_verifier_agent() factory
│   │       │   ├── prompt.py
│   │       │   └── schema.py
│   │       └── reviewer/        # Filters, re-verifies, outputs findings
│   │           ├── __init__.py
│   │           ├── agent.py
│   │           ├── prompt.py
│   │           └── schema.py
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

### Key Implementation Points

1. **Model**: Use `gemini-3-pro-preview` for all agents
2. **ExtractorAgent**: Outputs only FSLI names (simplified)
3. **FanOutVerifierAgent**: CustomAgent that creates parallel VerifierAgents
4. **VerifierAgent**: Created per FSLI, uses `BuiltInCodeExecutor`
5. **ReviewerAgent**: Uses `BuiltInCodeExecutor` for re-verification
6. **State sharing**: Via `output_key` and `session.state`

---

## Summary

| Requirement | Pattern/Solution |
|-------------|------------------|
| ADK terminal commands | `adk run`, `adk web` from parent directory |
| pytest for each agent | `tests/test_agents.py` with `InMemoryRunner` |
| adk-samples folder structure | `agent_name/agent.py` + `sub_agents/*/agent.py` + `prompt.py` + `schema.py` |
| Dynamic parallelism | CustomAgent pattern (BaseAgent + ParallelAgent at runtime) |
| Vertex AI Agent Engine deployment | `adk deploy agent_engine` or `deployment/deploy.py` script |
| Eval data and test_eval.py | `eval/data/*.test.json` + `AgentEvaluator.evaluate()` |
| agent.py + prompt.py + schema.py separation | Each sub-agent in own directory with all three files |

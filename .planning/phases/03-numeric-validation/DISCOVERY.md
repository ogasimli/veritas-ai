# Phase 3: Numeric Validation - Discovery

## Research Level: Standard (Level 2)

Research conducted 2026-01-10 on Google ADK agent patterns and code_executor integration.

## Technology Decisions

### Google ADK Agent Patterns

**Core Components:**
- `LlmAgent`: Base agent with `model`, `instruction`, `output_key`
- `SequentialAgent`: Chains agents in order, passes state via session
- `BuiltInCodeExecutor`: Enables Python code execution in sandbox

**State Sharing Pattern:**
```python
planner = LlmAgent(
    name="Planner",
    instruction="Analyze the document and identify FSLIs.",
    output_key="fslis"  # Writes to session.state['fslis']
)

validator = LlmAgent(
    name="Validator",
    instruction="Validate each FSLI in {fslis}.",  # Reads from state
    output_key="validation_results"
)
```

**Pipeline Pattern:**
```python
pipeline = SequentialAgent(
    name="NumericValidationPipeline",
    sub_agents=[planner, validator, manager]
)
```

### Code Executor Limitations

**Critical constraint**: `BuiltInCodeExecutor` can only be used **by itself** within an agent instance. Cannot combine with other tools.

**Implication**: Validator agent must be dedicated to code execution. Any other tools (like structured output formatting) must be in separate agents.

**Available in sandbox**: numpy, pandas (for table operations - useful for financial tables)

### Architecture Decision

Given the code_executor limitation, the pipeline will be:

1. **Planner Agent** (LlmAgent): Parses extracted_text, identifies Financial Statement Line Items (FSLIs), outputs structured JSON with items to validate
2. **Validator Agent** (LlmAgent + BuiltInCodeExecutor): For each FSLI, generates Python code to verify math, executes, captures results
3. **Manager Agent** (LlmAgent): Aggregates validation results, deduplicates, assigns severity, formats findings

## Sources

- [Google ADK Sequential Agents](https://google.github.io/adk-docs/agents/workflow-agents/sequential-agents/)
- [Multi-Agent Systems in ADK](https://google.github.io/adk-docs/agents/multi-agents/)
- [Code Execution in ADK](https://google.github.io/adk-docs/tools/gemini-api/code-execution/)
- [Google GenAI SDK](https://github.com/googleapis/python-genai)

## Don't Hand-Roll

- Agent orchestration (use SequentialAgent)
- Code execution sandbox (use BuiltInCodeExecutor)
- State management between agents (use output_key and session.state)

## Implementation Notes

1. Use `gemini-3-pro` model (Gemini 3 Pro as specified in PROJECT.md)
2. Store findings in database via Finding model (already exists)
3. Update Job status throughout pipeline execution
4. FSLI = Financial Statement Line Item (e.g., "Revenue", "Total Assets")

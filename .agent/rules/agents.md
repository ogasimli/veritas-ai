---
trigger: model_decision
description: Rules to follow when working with LLM agents
---

- Always use Pydantic for structured outputs from LLM agents instead of relying on a prompt based instruction.
- Fields on all pydnatic objects should contain Field(description=...) to enhance the LLM's comprehension of each field's role.
- Always use gemini-3-pro model, unless instructed otherwise
- Initialize gemini-3-pro model with thinking_level=high, unless instructed otherwise
from google.adk.agents import LlmAgent
from google.adk.code_executors import BuiltInCodeExecutor
from .schema import VerifierAgentOutput
from .prompt import get_verifier_instruction

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
        model="gemini-1.5-pro",  # Updated from gemini-3-pro-preview based on common model names
        instruction=get_verifier_instruction(fsli_name),
        output_key=output_key,
        output_schema=VerifierAgentOutput,
        code_executor=BuiltInCodeExecutor(),
    )

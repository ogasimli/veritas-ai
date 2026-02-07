"""Callbacks for the CrossTableFormulaFanOut agent."""

from google.adk.agents.callback_context import CallbackContext


def after_fan_out_callback(callback_context: CallbackContext) -> None:
    """Copy cross-table fan-out output into the shared reconstructed_formulas list.

    The FanOutAgent writes to ``state["cross_table_fan_out_output"]``.
    This callback appends those formulas (already stamped with
    ``check_type="cross_table"``) to the shared ``reconstructed_formulas``
    list that the downstream aggregator consumes.
    """
    state = callback_context.state
    fan_out_output = state.get("cross_table_fan_out_output", {})
    if hasattr(fan_out_output, "model_dump"):
        fan_out_output = fan_out_output.model_dump()

    formulas = fan_out_output.get("formulas", [])
    state.setdefault("reconstructed_formulas", [])
    state["reconstructed_formulas"].extend(formulas)

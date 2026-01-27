# Dummy Agent Service

This folder contains the dummy agent service used for testing without incurring inference costs.

## Files

- **`dummy_agent_service.py`**: Mock implementation of the ADK runner interface
- **`dummy_events.json`**: Real event sequence extracted from an actual agent session

## How It Works

The `DummyAgentService` replays real events from `dummy_events.json`, which contains:
- Complete state deltas from actual agent runs
- Realistic timing between events
- All agent outputs (findings, errors, verification checks)

## Usage

Set `USE_DUMMY_AGENTS=true` in your `.env` file to use the dummy service instead of real agents.

```python
# In processor.py
if use_dummy_agents:
    runner = DummyAgentService(app=app)
else:
    runner = InMemoryRunner(app=app)
```

## Updating Events

To update `dummy_events.json` with a new session:

1. Export a session from ADK to JSON
2. Run the extraction script:
   ```bash
   python backend/scripts/extract_events_from_session.py path/to/session.json \
     --output backend/app/services/dummy_agent/dummy_events.json
   ```

The extracted events will include all state deltas exactly as they occurred in the real session, providing an authentic testing experience.

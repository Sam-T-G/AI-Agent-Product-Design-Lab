# Sequential Audit: AgentModel Attribute Access

## Issue Found
`AgentModel` object was being accessed with non-existent attributes:
- ❌ `agent.model` 
- ❌ `agent.temperature`
- ❌ `agent.description`

## Root Cause
The new `orchestrator_v2.py` was written assuming direct attributes, but `AgentModel` stores these in the `parameters` JSON field.

## AgentModel Schema (Actual Fields)
```python
class AgentModel(Base):
    id: str
    session_id: str
    name: str
    role: str
    system_prompt: str  # ✅ EXISTS
    tools: JSON
    parameters: JSON  # ✅ Contains: {"model": "...", "temperature": 0.7, ...}
    photo_injection_enabled: str
    photo_injection_features: JSON
    parent_id: str (optional)
    position_x: float (optional)
    position_y: float (optional)
    created_at: datetime
    updated_at: datetime
```

## Fixes Applied

### 1. `description` → `system_prompt`
**File**: `agent_selector.py`, `orchestrator_v2.py`
- Changed: `agent.description` → `agent.system_prompt`
- Status: ✅ Fixed

### 2. `model` → `parameters.get("model")`
**File**: `orchestrator_v2.py`
- Changed: `agent.model` → `agent.parameters.get("model", "gemini-2.5-flash")`
- Added: Model migration logic (same as old orchestrator)
- Status: ✅ Fixed

### 3. `temperature` → `parameters.get("temperature")`
**File**: `orchestrator_v2.py`
- Changed: `agent.temperature` → `agent.parameters.get("temperature", 0.7)`
- Status: ✅ Fixed

## Code Pattern (Correct)
```python
# ✅ CORRECT - How old orchestrator does it
model = agent.parameters.get("model", "gemini-2.5-flash")
temperature = agent.parameters.get("temperature", 0.7)

# ❌ WRONG - What new orchestrator was doing
model = agent.model  # AttributeError!
temperature = agent.temperature  # AttributeError!
```

## Verification
All attribute accesses now match the actual schema:
- ✅ `agent.name` - exists
- ✅ `agent.role` - exists
- ✅ `agent.system_prompt` - exists
- ✅ `agent.parameters.get("model")` - correct access
- ✅ `agent.parameters.get("temperature")` - correct access
- ✅ `agent.parameters.get("max_tokens")` - correct access (if needed)

## Testing
After restart, agents should execute without AttributeError.


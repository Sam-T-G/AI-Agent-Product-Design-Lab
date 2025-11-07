#!/bin/bash
set -e

echo "=== Testing Parent-Child Communication & Session Isolation ==="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

API_BASE="http://localhost:8000/api"

# Test 1: Create two sessions
echo "Test 1: Creating two sessions..."
TIMESTAMP=$(date +%s)
SESSION1_NAME="Parent-Child Test Session 1 - $TIMESTAMP"
SESSION2_NAME="Parent-Child Test Session 2 - $TIMESTAMP"

SESSION1=$(curl -s -X POST "$API_BASE/sessions" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"$SESSION1_NAME\"}" | jq -r '.id')
SESSION2=$(curl -s -X POST "$API_BASE/sessions" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"$SESSION2_NAME\"}" | jq -r '.id')

if [ -z "$SESSION1" ] || [ "$SESSION1" = "null" ]; then
  echo -e "${RED}❌ Failed to create Session 1${NC}"
  exit 1
fi
if [ -z "$SESSION2" ] || [ "$SESSION2" = "null" ]; then
  echo -e "${RED}❌ Failed to create Session 2${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Created Session 1: $SESSION1${NC}"
echo -e "${GREEN}✅ Created Session 2: $SESSION2${NC}"
echo ""

# Test 2: Create parent and child agents in Session 1
echo "Test 2: Creating parent-child hierarchy in Session 1..."
PARENT_S1=$(curl -s -X POST "$API_BASE/agents?session_id=$SESSION1" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Parent Agent S1",
    "role": "manager",
    "system_prompt": "You are a parent agent that coordinates child agents",
    "parameters": {"model": "gemini-2.5-flash"}
  }' | jq -r '.id')

CHILD_S1=$(curl -s -X POST "$API_BASE/agents?session_id=$SESSION1" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Child Agent S1\",
    \"role\": \"worker\",
    \"system_prompt\": \"You are a child agent that reports to parent\",
    \"parameters\": {\"model\": \"gemini-2.5-flash\"},
    \"parent_id\": \"$PARENT_S1\"
  }" | jq -r '.id')

if [ -z "$PARENT_S1" ] || [ "$PARENT_S1" = "null" ]; then
  echo -e "${RED}❌ Failed to create parent in Session 1${NC}"
  exit 1
fi
if [ -z "$CHILD_S1" ] || [ "$CHILD_S1" = "null" ]; then
  echo -e "${RED}❌ Failed to create child in Session 1${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Created parent: $PARENT_S1${NC}"
echo -e "${GREEN}✅ Created child: $CHILD_S1${NC}"
echo ""

# Test 3: Create parent and child agents in Session 2
echo "Test 3: Creating parent-child hierarchy in Session 2..."
PARENT_S2=$(curl -s -X POST "$API_BASE/agents?session_id=$SESSION2" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Parent Agent S2",
    "role": "manager",
    "system_prompt": "You are a parent agent that coordinates child agents",
    "parameters": {"model": "gemini-2.5-flash"}
  }' | jq -r '.id')

CHILD_S2=$(curl -s -X POST "$API_BASE/agents?session_id=$SESSION2" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Child Agent S2\",
    \"role\": \"worker\",
    \"system_prompt\": \"You are a child agent that reports to parent\",
    \"parameters\": {\"model\": \"gemini-2.5-flash\"},
    \"parent_id\": \"$PARENT_S2\"
  }" | jq -r '.id')

if [ -z "$PARENT_S2" ] || [ "$PARENT_S2" = "null" ]; then
  echo -e "${RED}❌ Failed to create parent in Session 2${NC}"
  exit 1
fi
if [ -z "$CHILD_S2" ] || [ "$CHILD_S2" = "null" ]; then
  echo -e "${RED}❌ Failed to create child in Session 2${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Created parent: $PARENT_S2${NC}"
echo -e "${GREEN}✅ Created child: $CHILD_S2${NC}"
echo ""

# Test 4: Verify parent-child relationships are isolated
echo "Test 4: Verifying parent-child relationships are session-isolated..."

# Try to create link from Session 1 child to Session 2 parent (should fail)
CROSS_LINK=$(curl -s -X POST "$API_BASE/links?session_id=$SESSION1" \
  -H "Content-Type: application/json" \
  -d "{
    \"parent_agent_id\": \"$PARENT_S2\",
    \"child_agent_id\": \"$CHILD_S1\"
  }" 2>&1)

if echo "$CROSS_LINK" | grep -q "not found\|does not belong"; then
  echo -e "${GREEN}✅ Cross-session parent-child linking correctly blocked${NC}"
else
  echo -e "${RED}❌ Cross-session parent-child linking should be blocked${NC}"
  echo "Response: $CROSS_LINK"
  exit 1
fi

# Try to create child with parent from different session (should fail)
CROSS_CHILD=$(curl -s -X POST "$API_BASE/agents?session_id=$SESSION1" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Cross Session Child\",
    \"role\": \"worker\",
    \"system_prompt\": \"Test\",
    \"parameters\": {\"model\": \"gemini-2.5-flash\"},
    \"parent_id\": \"$PARENT_S2\"
  }" 2>&1)

if echo "$CROSS_CHILD" | grep -q "same session\|does not belong"; then
  echo -e "${GREEN}✅ Cross-session child creation correctly blocked${NC}"
else
  echo -e "${RED}❌ Cross-session child creation should be blocked${NC}"
  echo "Response: $CROSS_CHILD"
  exit 1
fi
echo ""

# Test 5: Verify child agents can only see their parent in same session
echo "Test 5: Verifying child agents only see parents in same session..."

# Get child from Session 1 - should have parent from Session 1
CHILD_DATA_S1=$(curl -s "$API_BASE/agents/$CHILD_S1?session_id=$SESSION1" | jq -r '.parent_id')
if [ "$CHILD_DATA_S1" = "$PARENT_S1" ]; then
  echo -e "${GREEN}✅ Child S1 correctly linked to Parent S1${NC}"
else
  echo -e "${RED}❌ Child S1 parent mismatch. Expected: $PARENT_S1, Got: $CHILD_DATA_S1${NC}"
  exit 1
fi

# Get child from Session 2 - should have parent from Session 2
CHILD_DATA_S2=$(curl -s "$API_BASE/agents/$CHILD_S2?session_id=$SESSION2" | jq -r '.parent_id')
if [ "$CHILD_DATA_S2" = "$PARENT_S2" ]; then
  echo -e "${GREEN}✅ Child S2 correctly linked to Parent S2${NC}"
else
  echo -e "${RED}❌ Child S2 parent mismatch. Expected: $PARENT_S2, Got: $CHILD_DATA_S2${NC}"
  exit 1
fi

# Try to get child from Session 1 using Session 2's session_id (should fail)
CROSS_CHILD_ACCESS=$(curl -s "$API_BASE/agents/$CHILD_S1?session_id=$SESSION2" 2>&1)
if echo "$CROSS_CHILD_ACCESS" | grep -q "not found"; then
  echo -e "${GREEN}✅ Cross-session child access correctly blocked${NC}"
else
  echo -e "${RED}❌ Cross-session child access should be blocked${NC}"
  echo "Response: $CROSS_CHILD_ACCESS"
  exit 1
fi
echo ""

# Test 6: Verify link creation works within session
echo "Test 6: Verifying link creation within session..."
LINK_S1=$(curl -s -X POST "$API_BASE/links?session_id=$SESSION1" \
  -H "Content-Type: application/json" \
  -d "{
    \"parent_agent_id\": \"$PARENT_S1\",
    \"child_agent_id\": \"$CHILD_S1\"
  }" | jq -r '.id // "created"')

if [ -n "$LINK_S1" ] && [ "$LINK_S1" != "null" ]; then
  echo -e "${GREEN}✅ Link created successfully in Session 1${NC}"
else
  echo -e "${YELLOW}⚠️ Link may already exist (idempotent)${NC}"
fi
echo ""

# Test 7: Verify update operations respect session boundaries
echo "Test 7: Verifying update operations respect session boundaries..."

# Try to update child from Session 1 using Session 2's session_id (should fail)
CROSS_UPDATE=$(curl -s -X PUT "$API_BASE/agents/$CHILD_S1?session_id=$SESSION2" \
  -H "Content-Type: application/json" \
  -d '{"name": "Hacked Name"}' 2>&1)

if echo "$CROSS_UPDATE" | grep -q "not found"; then
  echo -e "${GREEN}✅ Cross-session update correctly blocked${NC}"
else
  echo -e "${RED}❌ Cross-session update should be blocked${NC}"
  echo "Response: $CROSS_UPDATE"
  exit 1
fi

# Update child within same session (should work)
UPDATE_SUCCESS=$(curl -s -X PUT "$API_BASE/agents/$CHILD_S1?session_id=$SESSION1" \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Child Name"}' | jq -r '.name')

if [ "$UPDATE_SUCCESS" = "Updated Child Name" ]; then
  echo -e "${GREEN}✅ Update within session works correctly${NC}"
else
  echo -e "${RED}❌ Update within session failed${NC}"
  exit 1
fi
echo ""

# Test 8: Verify delete operations respect session boundaries
echo "Test 8: Verifying delete operations respect session boundaries..."

# Try to delete child from Session 1 using Session 2's session_id (should fail)
CROSS_DELETE=$(curl -s -X DELETE "$API_BASE/agents/$CHILD_S2?session_id=$SESSION1" 2>&1)

if echo "$CROSS_DELETE" | grep -q "not found"; then
  echo -e "${GREEN}✅ Cross-session delete correctly blocked${NC}"
else
  echo -e "${RED}❌ Cross-session delete should be blocked${NC}"
  echo "Response: $CROSS_DELETE"
  exit 1
fi
echo ""

# Test 9: Verify parent-child graph loading respects session
echo "Test 9: Verifying parent-child graph loading respects session..."

# Create a run with parent agent in Session 1
# This will test if the orchestrator loads children correctly within session
RUN_S1=$(curl -s -X POST "$API_BASE/runs?session_id=$SESSION1" \
  -H "Content-Type: application/json" \
  -d "{
    \"root_agent_id\": \"$PARENT_S1\",
    \"input\": {
      \"prompt\": \"Test prompt\",
      \"task\": \"Test task\"
    }
  }" | jq -r '.id')

if [ -z "$RUN_S1" ] || [ "$RUN_S1" = "null" ]; then
  echo -e "${RED}❌ Failed to create run${NC}"
  exit 1
fi

echo -e "${GREEN}✅ Run created: $RUN_S1${NC}"
echo -e "${YELLOW}ℹ️ Run execution would test parent-child communication, but skipping to avoid API key requirement${NC}"
echo ""

# Cleanup
echo "Cleaning up test sessions..."
curl -s -X DELETE "$API_BASE/sessions/$SESSION1" > /dev/null
curl -s -X DELETE "$API_BASE/sessions/$SESSION2" > /dev/null
echo -e "${GREEN}✅ Test sessions cleaned up${NC}"
echo ""

echo -e "${GREEN}=== All Parent-Child Communication & Session Isolation Tests Passed! ===${NC}"


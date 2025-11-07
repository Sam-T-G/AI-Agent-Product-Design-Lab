#!/bin/bash
set -e

echo "=== Testing Session Isolation Pipeline ==="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

API_BASE="http://localhost:8000/api"

# Generate unique session names
TIMESTAMP=$(date +%s)
SESSION_NAME1="Test Session 1 - $TIMESTAMP"
SESSION_NAME2="Test Session 2 - $TIMESTAMP"

# Test 1: Create two sessions
echo "Test 1: Creating two sessions..."
RESPONSE1=$(curl -s -X POST "$API_BASE/sessions" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"$SESSION_NAME1\"}")
SESSION1=$(echo "$RESPONSE1" | jq -r '.id // empty')

if [ -z "$SESSION1" ] || [ "$SESSION1" = "null" ] || [ "$SESSION1" = "empty" ]; then
  echo -e "${RED}❌ Failed to create Session 1${NC}"
  echo "Response: $RESPONSE1"
  exit 1
fi

RESPONSE2=$(curl -s -X POST "$API_BASE/sessions" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"$SESSION_NAME2\"}")
SESSION2=$(echo "$RESPONSE2" | jq -r '.id // empty')

if [ -z "$SESSION2" ] || [ "$SESSION2" = "null" ] || [ "$SESSION2" = "empty" ]; then
  echo -e "${RED}❌ Failed to create Session 2${NC}"
  echo "Response: $RESPONSE2"
  exit 1
fi
echo -e "${GREEN}✅ Created Session 1: $SESSION1${NC}"
echo -e "${GREEN}✅ Created Session 2: $SESSION2${NC}"
echo ""

# Test 2: Create agents in Session 1
echo "Test 2: Creating agents in Session 1..."
AGENT1_S1=$(curl -s -X POST "$API_BASE/agents?session_id=$SESSION1" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Agent 1 in Session 1",
    "role": "worker",
    "system_prompt": "You are a worker",
    "parameters": {"model": "gemini-2.5-flash"}
  }' | jq -r '.id')

AGENT2_S1=$(curl -s -X POST "$API_BASE/agents?session_id=$SESSION1" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Agent 2 in Session 1",
    "role": "manager",
    "system_prompt": "You are a manager",
    "parameters": {"model": "gemini-2.5-flash"}
  }' | jq -r '.id')

if [ -z "$AGENT1_S1" ] || [ "$AGENT1_S1" = "null" ]; then
  echo -e "${RED}❌ Failed to create Agent 1 in Session 1${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Created Agent 1 in Session 1: $AGENT1_S1${NC}"
echo -e "${GREEN}✅ Created Agent 2 in Session 1: $AGENT2_S1${NC}"
echo ""

# Test 3: Create agents in Session 2
echo "Test 3: Creating agents in Session 2..."
AGENT1_S2=$(curl -s -X POST "$API_BASE/agents?session_id=$SESSION2" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Agent 1 in Session 2",
    "role": "worker",
    "system_prompt": "You are a worker",
    "parameters": {"model": "gemini-2.5-flash"}
  }' | jq -r '.id')

if [ -z "$AGENT1_S2" ] || [ "$AGENT1_S2" = "null" ]; then
  echo -e "${RED}❌ Failed to create Agent 1 in Session 2${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Created Agent 1 in Session 2: $AGENT1_S2${NC}"
echo ""

# Test 4: Verify isolation - list agents in Session 1
echo "Test 4: Verifying Session 1 agents..."
AGENTS_S1=$(curl -s "$API_BASE/agents?session_id=$SESSION1" | jq '. | length')
if [ "$AGENTS_S1" != "2" ]; then
  echo -e "${RED}❌ Expected 2 agents in Session 1, got $AGENTS_S1${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Session 1 has 2 agents (correct)${NC}"

# Test 5: Verify isolation - list agents in Session 2
echo "Test 5: Verifying Session 2 agents..."
AGENTS_S2=$(curl -s "$API_BASE/agents?session_id=$SESSION2" | jq '. | length')
if [ "$AGENTS_S2" != "1" ]; then
  echo -e "${RED}❌ Expected 1 agent in Session 2, got $AGENTS_S2${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Session 2 has 1 agent (correct)${NC}"
echo ""

# Test 6: Verify cross-session access fails
echo "Test 6: Verifying cross-session access is blocked..."
RESPONSE=$(curl -s "$API_BASE/agents/$AGENT1_S1?session_id=$SESSION2" | jq -r '.detail // .message // "success"')
if [[ "$RESPONSE" != *"not found"* ]] && [[ "$RESPONSE" != *"Agent not found"* ]]; then
  echo -e "${RED}❌ Cross-session access should be blocked, but got: $RESPONSE${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Cross-session access correctly blocked${NC}"
echo ""

# Test 7: Create link in Session 1
echo "Test 7: Creating link in Session 1..."
LINK_S1=$(curl -s -X POST "$API_BASE/links?session_id=$SESSION1" \
  -H "Content-Type: application/json" \
  -d "{
    \"parent_agent_id\": \"$AGENT1_S1\",
    \"child_agent_id\": \"$AGENT2_S1\"
  }" | jq -r '.id // "created"')
echo -e "${GREEN}✅ Created link in Session 1${NC}"
echo ""

# Test 8: Verify link isolation (cross-session link creation should fail)
echo "Test 8: Verifying link isolation..."
# Try to create a link in Session 2 using agents from Session 1 (should fail)
CROSS_LINK_RESPONSE=$(curl -s -X POST "$API_BASE/links?session_id=$SESSION2" \
  -H "Content-Type: application/json" \
  -d "{
    \"parent_agent_id\": \"$AGENT1_S1\",
    \"child_agent_id\": \"$AGENT1_S2\"
  }")
CROSS_LINK_ERROR=$(echo "$CROSS_LINK_RESPONSE" | jq -r '.detail // "success"')
if [[ "$CROSS_LINK_ERROR" != *"not found"* ]] && [[ "$CROSS_LINK_ERROR" != *"does not belong"* ]]; then
  echo -e "${RED}❌ Cross-session link creation should be blocked, but got: $CROSS_LINK_ERROR${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Links are properly isolated (cross-session blocked)${NC}"
echo ""

# Test 9: Update agent in Session 1
echo "Test 9: Updating agent in Session 1..."
UPDATED=$(curl -s -X PUT "$API_BASE/agents/$AGENT1_S1?session_id=$SESSION1" \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Agent Name"}' | jq -r '.name')
if [ "$UPDATED" != "Updated Agent Name" ]; then
  echo -e "${RED}❌ Failed to update agent${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Agent updated successfully${NC}"
echo ""

# Test 10: Delete agent in Session 1
echo "Test 10: Deleting agent in Session 1..."
curl -s -X DELETE "$API_BASE/agents/$AGENT2_S1?session_id=$SESSION1" > /dev/null
REMAINING=$(curl -s "$API_BASE/agents?session_id=$SESSION1" | jq '. | length')
if [ "$REMAINING" != "1" ]; then
  echo -e "${RED}❌ Expected 1 agent remaining in Session 1, got $REMAINING${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Agent deleted successfully${NC}"
echo ""

# Test 11: Verify Session 2 is unaffected
echo "Test 11: Verifying Session 2 is unaffected..."
AGENTS_S2_AFTER=$(curl -s "$API_BASE/agents?session_id=$SESSION2" | jq '. | length')
if [ "$AGENTS_S2_AFTER" != "1" ]; then
  echo -e "${RED}❌ Session 2 should still have 1 agent, got $AGENTS_S2_AFTER${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Session 2 isolation maintained${NC}"
echo ""

# Test 12: Create run in Session 1
echo "Test 12: Creating run in Session 1..."
RUN_S1=$(curl -s -X POST "$API_BASE/runs?session_id=$SESSION1" \
  -H "Content-Type: application/json" \
  -d "{
    \"root_agent_id\": \"$AGENT1_S1\",
    \"input\": {
      \"prompt\": \"Test prompt\",
      \"task\": \"Test task\"
    }
  }" | jq -r '.id')
if [ -z "$RUN_S1" ] || [ "$RUN_S1" = "null" ]; then
  echo -e "${RED}❌ Failed to create run${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Created run in Session 1: $RUN_S1${NC}"
echo ""

# Test 13: Verify run isolation (cross-session run access should fail)
echo "Test 13: Verifying run isolation..."
# Try to access run from Session 1 using Session 2's session_id (should fail)
CROSS_RUN_RESPONSE=$(curl -s "$API_BASE/runs/$RUN_S1?session_id=$SESSION2")
CROSS_RUN_ERROR=$(echo "$CROSS_RUN_RESPONSE" | jq -r '.detail // "success"')
if [[ "$CROSS_RUN_ERROR" != *"not found"* ]] && [[ "$CROSS_RUN_ERROR" != *"Run not found"* ]]; then
  echo -e "${RED}❌ Cross-session run access should be blocked, but got: $CROSS_RUN_ERROR${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Runs are properly isolated (cross-session access blocked)${NC}"
echo ""

# Cleanup
echo "Cleaning up test sessions..."
curl -s -X DELETE "$API_BASE/sessions/$SESSION1" > /dev/null
curl -s -X DELETE "$API_BASE/sessions/$SESSION2" > /dev/null
echo -e "${GREEN}✅ Test sessions cleaned up${NC}"
echo ""

echo -e "${GREEN}=== All Session Isolation Tests Passed! ===${NC}"


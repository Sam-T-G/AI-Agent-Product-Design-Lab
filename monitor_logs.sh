#!/bin/bash
# Monitor backend logs with focus on important events

echo "🔍 Monitoring backend logs for debug information..."
echo "Press Ctrl+C to stop"
echo ""

tail -f /tmp/backend.log | grep --line-buffered -E "orchestrator_|sse_|gemini_|run_|agent_|ERROR|WARNING" | while read line; do
    # Color code different types of events
    if echo "$line" | grep -q "ERROR"; then
        echo -e "\033[0;31m$line\033[0m"  # Red
    elif echo "$line" | grep -q "WARNING"; then
        echo -e "\033[0;33m$line\033[0m"  # Yellow
    elif echo "$line" | grep -q "orchestrator_execute_run_start"; then
        echo -e "\033[0;32m🚀 $line\033[0m"  # Green
    elif echo "$line" | grep -q "orchestrator_run_marked_failed"; then
        echo -e "\033[0;31m❌ $line\033[0m"  # Red
    elif echo "$line" | grep -q "sse_completion_sent"; then
        echo -e "\033[0;32m✅ $line\033[0m"  # Green
    elif echo "$line" | grep -q "gemini_generate"; then
        echo -e "\033[0;36m🤖 $line\033[0m"  # Cyan
    else
        echo "$line"
    fi
done


# Agent Design Patterns

## Overview

Patterns to build reliable, modular multi-agent systems.

## Supervisor–Worker

- A supervisor (parent) routes tasks to specialized child agents
- Parent aggregates results and decides next steps
- Map directly to canvas parent/child links

## ReAct (Reason + Act)

- Agent alternates between reasoning steps and tool actions
- Encourages transparency and better tool use
- Useful for research and data gathering agents

## Tool Use

- Agents call tools (web search, HTTP, vector DB) via explicit interfaces
- Strict parameter schemas (Zod/Pydantic) to validate calls
- Sandbox external side-effects where possible

## Reflection / Self-critique

- Agent reviews its own output against a rubric
- Improves reliability for long-form outputs (briefs, specs)
- Implement as a child “Critic” agent linked from the producer

## Routing / Policy

- Parent decides which children to activate based on context or rules
- Implement with simple if/else first; evolve to LLM-based router later

## Parallel Fan-out

- Execute children at the same level concurrently
- Merge results deterministically in parent

## Circuit Breaker & Retries

- Retry transient errors with exponential backoff
- Open circuit when repeated failures occur to protect downstream services

## Observability

- Structured logs per agent and per run
- Correlation IDs across calls
- Exportable transcripts for auditing



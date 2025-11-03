# Architecture Decisions

## ADR-0001: Frontend Framework Choice

**Date**: 2025-01-XX

**Status**: Accepted

**Context**: Need a modern, performant frontend framework that supports server-side rendering and excellent developer experience.

**Decision**: Use Next.js with App Router for the frontend.

**Consequences**:
- ✅ Excellent developer experience with TypeScript support
- ✅ Built-in API routes for simple backend logic
- ✅ Server components for better performance
- ✅ Strong ecosystem and community support
- ⚠️ Learning curve for App Router if team is new to it

## ADR-0002: Styling Approach

**Date**: 2025-01-XX

**Status**: Accepted

**Context**: Need consistent, fast styling that doesn't require complex setup.

**Decision**: Use Tailwind CSS for utility-first styling.

**Consequences**:
- ✅ Rapid UI development
- ✅ Consistent design system
- ✅ Small bundle size with purging
- ✅ No CSS-in-JS runtime overhead
- ⚠️ HTML can become verbose with many classes

## ADR-0003: Backend Framework

**Date**: 2025-01-XX

**Status**: Accepted

**Context**: Need a Python backend that's fast, type-safe, and has excellent async support.

**Decision**: Use FastAPI for the backend API server.

**Consequences**:
- ✅ Automatic API documentation (OpenAPI/Swagger)
- ✅ Built-in async support
- ✅ Pydantic for type validation
- ✅ Fast performance
- ✅ Easy integration with async Python libraries

## ADR-0004: AI Provider

**Date**: 2025-01-XX

**Status**: Accepted

**Context**: Need a reliable AI provider with good API, reasonable pricing, and strong reasoning capabilities.

**Decision**: Use Google Gemini via `google-generativeai` SDK.

**Consequences**:
- ✅ Strong reasoning capabilities
- ✅ Good API design
- ✅ Competitive pricing
- ✅ User brings their own API key
- ⚠️ Vendor lock-in (can be mitigated with abstraction layer)

## ADR-0005: Data Persistence

**Date**: 2025-01-XX

**Status**: Accepted

**Context**: Need simple persistence to start, with ability to scale later.

**Decision**: Start with SQLite, design for easy migration to Postgres.

**Consequences**:
- ✅ Zero setup for local development
- ✅ Easy to migrate to Postgres later
- ✅ SQLAlchemy abstraction helps with migration
- ⚠️ SQLite limitations for concurrent writes (not an issue for MVP)

## ADR-0006: Graph Visualization Library

**Date**: 2025-01-XX

**Status**: Accepted

**Context**: Need a library for visual node-based agent composition.

**Decision**: Use React Flow for graph visualization with controlled nodes/edges.

**Consequences**:
- ✅ React-native, well-maintained
- ✅ Good documentation and examples
- ✅ Customizable nodes and edges
- ✅ Built-in minimap and controls
- ⚠️ Additional bundle size
- ⚠️ Learning curve for complex customizations

Implementation notes:
- Use `useNodesState`/`useEdgesState` hooks
- Separate presentational nodes from business logic
- Persist layout positions in store (optional)

## ADR-0007: State Management

**Date**: 2025-01-XX

**Status**: Accepted

**Context**: Need state management for agent graphs, UI state, and real-time execution updates.

**Decision**: Use Zustand with Immer middleware for global state management.

**Consequences**:
- ✅ Minimal boilerplate
- ✅ Simple API
- ✅ Good TypeScript support
- ✅ Small bundle size
- ⚠️ Less structure than Redux (can be pro or con)

Implementation notes:
- Co-locate slices by feature (graph, selection, templates)
- Avoid selector over-re-renders with shallow compares


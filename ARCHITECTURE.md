# Architecture

## What does the memory system store, and why?

Memory has two layers stored in PostgreSQL:

**Execution memory** (`ExecutionMemory`) stores past instructions, decompositions, step outcomes, duration, API call count, and failure reasons. This layer answers “what happened before on similar tasks?” The agent retrieves similar executions by instruction keyword overlap and injects the best prior decomposition into the system prompt, which drives fewer API calls and faster runs on repeat.

**Capability memory** (`CapabilityMemory`) stores tool definitions, synthesized API specs, success/failure counts, and runtime constraints such as permission errors or rate limits. This layer answers “what can the agent do, and how reliably?” Successful tools are reused directly; failed operations add constraints so the planner avoids repeating the same mistake.

LangGraph `PostgresStore` is also used for session-scoped execution snapshots, but the structured SQL tables are the source of truth for learning.

## How does capability synthesis work?

When the agent identifies a missing operation, it calls `request_new_capability`. The synthesizer asks the LLM to produce a GitHub REST API spec (`method`, `path`, optional `query`/`body`), executes it against the live API, and registers it in capability memory if successful. Registered capabilities are exposed as dynamic tools on subsequent runs. After three failed attempts, synthesis stops with an explicit error report.

This is runtime synthesis, not a static endpoint lookup table.

## Learning signal

The primary measurable signal is **API call count and duration for semantically similar instructions**.

On run 1, the agent may list issues and filter in multiple steps. On run N, execution memory surfaces the best prior successful decomposition, and the agent converges on a shorter path — for example, one search call instead of three list/filter calls. The execution report includes `learning_notes` with before/after numbers.

Secondary signals:

- capability success rate increases as constraints accumulate
- failure rate drops when prior constraints are injected into memory context

## What I would build next

- Memory compaction via periodic summarization of old execution records
- Rollback support for write operations using stored step payloads
- Confidence scoring on tool selection based on capability success rates

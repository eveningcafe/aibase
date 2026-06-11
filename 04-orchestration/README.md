# 04 · Orchestration — the agentic layer

This is where a **model becomes an agent**. A single prompt-in / answer-out call
is just a chat interface. Add planning, tool use, memory, and feedback loops and
it becomes an **agentic system** that decomposes a task, acts, and self-corrects.

> Orchestration is the *mechanism*; "agentic" is the *behavior* you build on top
> of it. This layer is the **control plane / brain** of the stack.

## Two kinds of orchestration (use both)

| Kind | What it is | Strength |
|------|------------|----------|
| **Static / deterministic** | Fixed workflows, pipelines, routing | Reliable, predictable, auditable |
| **Agentic / autonomous** | Agents decide, escalate, adapt to context | Handles judgment, exceptions, multi-step tasks |

A static foundation gives reliability; the agentic layer fills the thinking and
decision-making that fixed flows can't handle.

## The loop

```
plan ──▶ execute (tools) ──▶ review ──▶ (loop / replan)
   ▲                                        │
   └──────────── memory / state ◀───────────┘
```

## What goes here

| Dir | Role | Notes |
|-----|------|-------|
| `agents/` | **Agent definitions** | Roles, goals, single- & multi-agent coordination, handoffs/escalation. |
| `planning/` | **Thinking** | Task decomposition, reasoning, deciding what data/tools are needed. |
| `execution/` | **Acting** | Tool calling / function calling to do the work. |
| `review/` | **Reviewing** | Self-critique and feedback loops to improve outputs. |
| `memory/` | **State** | Short/long-term memory, context preserved across turns & sessions. |
| `mcp/` | **Protocols** | MCP servers/clients and tool specs exposed to agents. |

## Notes

- This layer is the fastest-evolving part of the stack (MCP, new agent
  architectures, agent gateways).
- A weaker model with strong orchestration often beats a stronger model with
  poor orchestration — architecture compounds.
- Routing (which model/tool/agent handles a step) lives here too.

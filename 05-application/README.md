# 05 · Application

At the end of the day there's a user. This layer is **where AI meets the end
user and real-world use cases**. It answers two questions:

1. **Interfaces** — how does the user *see and interact* with the AI?
2. **Integrations** — how does the AI *connect* to other systems?

| Dir | Purpose |
|-----|---------|
| `interfaces/` | How inputs/outputs are presented to the user. |
| `integrations/` | How the system connects to the user's other tools. |

## Interfaces

- Classic **text in / text out**, plus other modalities: image, audio,
  numerical datasets, charts, custom formats.
- **Revisions & citations** — let users edit outputs or inquire further, and
  see where answers came from.
- New interaction styles: **conversational UI replacing click-based forms**
  (ask in natural language instead of navigating menus).

## Integrations

- **Inbound** — other tools send inputs to the AI system (e.g. Gmail forwards a
  new email for the AI to summarize).
- **Outbound** — model outputs are automated into the tools users rely on
  (e.g. a report pushed to Google Sheets, an order pushed to a payment system).

## Examples

| Use case | Interface | Integration |
|----------|-----------|-------------|
| **Summarize email** | text in → summary out, with "edit" / "show source" | inbound: Gmail forwards new mail |
| **Text → data report** | text in → table / chart / numbers out (multi-modal) | outbound: push report to Sheets |
| **Replace a shopping / fintech portal** | conversational UI instead of forms & menus | outbound: send order to checkout / matching engine |

## What is — and isn't — this layer

| Question | Layer |
|----------|-------|
| "What does the AI *do* — summarize, plan, call which tool?" | **04 · Orchestration** |
| "What does the user *see / type / click*?" | **05 · Interfaces** |
| "How does the result *connect into* Gmail / Sheets / checkout?" | **05 · Integrations** |

> Integrating AI into an existing app: the *brain* is orchestration (layer 4);
> fitting it into that app's **screens and business flow** is this layer.

## End-to-end: a fintech order, across the whole stack

```
User: "buy 100 VNM if price < 60"        ← 05 Interface (chat replaces a form)
  ▼
Parse intent, plan, call APIs            ← 04 Orchestration (agentic)
  ▼
Fetch real-time price & stock data       ← 03 Data (RAG / retrieval)
  ▼
Model understands & decides              ← 02 Models
  ▼
GPU runs the model                       ← 01 Infrastructure
  ▼
Send order to matching engine + Slack    ← 05 Integration
```

The application layer is **both ends of the flow**: what the user says (and
through which interface) and where the result lands (which tools/systems it
feeds into).

## What goes here

- Frontend / API / chat UI
- Webhooks, connectors, and automation into external tools
- Auth, rate limiting, and usage tracking at the edge

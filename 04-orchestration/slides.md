---
marp: true
theme: default
paginate: true
size: 16:9
header: 'Orchestration — the agentic layer'
style: |
  section { font-size: 26px; }
  h1 { font-size: 44px; }
  h2 { font-size: 34px; }
  code { font-size: 0.8em; }
  pre { font-size: 0.66em; line-height: 1.22; }
  table { font-size: 0.76em; }
  section.lead h1 { font-size: 52px; }
  section.lead { text-align: center; }
  section.part h1 { font-size: 50px; }
  section.part { text-align: center; }
  footer, header { color: #888; font-size: 14px; }
---

<!-- _class: lead -->
<!-- _paginate: false -->

# Orchestration

### The agentic layer — where a model becomes an agent

`plan → execute → review → memory → loop`

<!--
Welcome. This is layer 4 of the AI stack. A model on its own is a chat box —
prompt in, answer out. This whole session is about the machinery that wraps a
model and turns it into something that decomposes a task, acts on the world, and
self-corrects. We'll keep returning to one running example — an SRE agent
handling a production incident — so every abstract idea lands on something
concrete. ~2 hours with two short breaks; interrupt with questions anytime.
-->

---

## Agenda

1. **Why orchestration?** — a model is one piece · the loop
2. **Planning** — reasoning models, test-time compute, stop-and-ask
3. **Execution** — tool calling and MCP, local & remote
4. **Review** — reflection, grounded verification, when to stop
5. **Memory** — the four kinds, scope, file demo → mem0
6. **Putting it together** + Q&A

<!--
Four boxes of the loop = four parts. Roughly half the time is planning +
execution because that's where the mental model is built; review and memory are
shorter but essential. Take breaks between parts as the room needs. Hold deep
tooling questions for the execution part where they'll be answered.
-->

---

<!-- _class: part -->

# 0 · Why orchestration?

A model is one piece, not the whole system.

<!--
Set the frame before any detail. The point of this part: name the gap between
"a model" and "an agent," and give the loop diagram we'll spend two hours
filling in.
-->

---

## A model alone is a chat box

One prompt in → one answer out. That's a **chat interface**.

Add four things and it becomes an **agent**:

- **Planning** — break an intent into steps
- **Execution** — call tools to act on the real world
- **Review** — check the work, self-correct
- **Memory** — carry state across steps and sessions

> Orchestration is the *mechanism*; "agentic" is the *behavior* you build on it.
> This layer is the **brain / control plane** of the stack.

<!--
Students often equate "the model" with "the AI product." This slide draws the
line. The model is the engine; orchestration is the rest of the car. Everything
today is one of these four words.
-->

---

## Two kinds of orchestration — use both

| Kind | What it is | Strength |
|------|------------|----------|
| **Static / deterministic** | Fixed workflows, pipelines, routing | Reliable, predictable, auditable |
| **Agentic / autonomous** | Agents decide, escalate, adapt | Judgment, exceptions, multi-step |

A static foundation gives reliability; the agentic layer fills the thinking and
decision-making that fixed flows can't handle.

> You don't pick one — most robust systems are mostly **static**, with
> **agentic** judgment at the hard joints.

<!--
Don't sell "agentic" as the answer to everything. Most robust systems are mostly
deterministic with agentic judgment at the hard joints. The next slide makes the
"use both" idea concrete with the SRE example.
-->

---

## The loop

```
plan ──▶ execute (tools) ──▶ review ──▶ (loop)
   ▲                                        │
   └──────────── memory / state ◀───────────┘
```

| Box | Role | We'll cover |
|-----|------|-------------|
| **Plan** | Thinking | reasoning, decomposition, stop-and-ask |
| **Execute** | Acting | tool calling, MCP |
| **Review** | Checking | reflection, grounded verification |
| **Memory** | State | working / episodic / semantic / procedural |

<!--
This is the spine of the whole lecture. Every part maps to one box. Tell them:
take a photo of this slide; we'll point back to it constantly.
-->

---

## The running example — an SRE agent

> **14:35 — an alert fires.** `checkout-api` is throwing a **spike of 5xx**.
> The SRE just states an **intent**: *"checkout-api is 5xx, deal with it."*

**Combine both:** keep your alerting pipeline; **add an agent on top** that —

- **reads the same alert** and **reasons** to a root cause  *(plan)*
- **stops to ask** before a risky rollback  *(plan)*
- **acts** — calls a real tool  *(execute)*
- **verifies** the fix against live metrics  *(review)*
- **remembers** the lesson → less manual toil next time  *(memory)*

<!--
This is the combine-both idea made concrete AND the character we follow all
lecture. The agent plugs INTO the existing alerting — it doesn't replace it. Each
bullet maps to one box of the loop on the previous slide; by the end they've seen
the whole loop run once on this incident, not four disconnected topics.
-->

---

<!-- _class: part -->

# 1 · Planning

The agent thinks, pauses, and asks.

<!--
30 minutes. Goal: understand what "reasoning" actually is at the token level, why
it costs compute, how such models are trained, and how "stop and ask" is just a
tool call. Source: IBM Technology LRM video + DeepSeek-R1.
-->

---

## Who writes the steps?

```
TRADITIONAL SOFTWARE              AGENT (SRE on-call)
─────────────────────             ───────────────────
Runbook written AHEAD,            User states an INTENT:
reviewed/compiled first.          "checkout-api 5xx, fix it"
                                          │
if error_rate > 5%:                       ▼
    restart_pods()                MODEL invents steps AT RUN-TIME:
elif latency > 1s:                  1. when did 5xx start?
    scale_up()                      2. any deploy near then?
                                    3. read logs → find cause
Runs only the script you            4. (rollback? → ASK human)
foresaw. Novel case → stuck.        5. roll back, then re-verify
```

**Traditional:** a programmer types every branch at *compose-time*.
**Agent:** the user gives an *intent*; the model invents the steps at *run-time*.

<!--
The single most important distinction in this part. Recipe vs chef: traditional
software is a written recipe; an agent is a chef told "make something good for
four vegetarians." Because steps aren't pre-written, the core skill of this layer
is reasoning — turning intent into a plan.
-->

---

## Reasoning is built from tokens — one at a time

Planning = the model **reasoning** an intent into steps. And reasoning bottoms
out in how a model generates *anything*:

Autoregressive: at each step, look at *all* text so far → pick the next token →
append → repeat.

```
"The capital of France is" → [model] → next: "Paris" (highest prob)
append → "The capital of France is Paris" → generate the next token...
```

Everything a model "does" is this single loop. So what is *reasoning*?

<!--
Anchor before the reveal. They must hold "one token at a time" in their head,
because the whole trick of reasoning models is purely about WHICH tokens get
generated and WHEN. No new mechanism — same next-token loop.
-->

---

## Ordinary vs reasoning model

```
ORDINARY MODEL:
prompt ──▶ [blurts an answer] ──▶ "Try restarting the pods."
           (fast guess, easily wrong about the real cause)

REASONING MODEL:
prompt ──▶ [emits a PILE of "thinking" tokens first] ──▶ then concludes
   ┌──────────────────── scratchpad ─────────────────────┐
   │ "5xx rising since 14:32. What changed? → deploy v2.3 │
   │  at 14:30. Logs: 'DB connection timeout'. v2.3 cut   │
   │  the pool to 5. Cause = the deploy, NOT traffic."    │
   └───────────────────────────────────────────────────────┘
                          │
                          ▼
        "Cause: deploy v2.3 shrank the DB pool. Fix: roll back."
```

That chain of thinking tokens (**chain-of-thought**) *is* the reasoning.

<!--
Side by side. The ordinary model guesses "restart" — a plausible but wrong fix.
The reasoning model writes its working out first and lands on the actual cause.
Stress: the scratchpad is the same kind of tokens as the answer.
-->

---

## Four things that matter (at the token level)

1. **Thinking tokens are ordinary tokens** — same next-token loop. No magic; a
   draft *before* the answer.
2. **Each token feeds back and steers the next.** The model writes **notes to
   itself**. "Oh, that's wrong, back up" really redirects what follows.
3. **Each token = one forward pass = compute.** More scratchpad = **more
   compute** spent → **test-time compute.** "Think longer" literally = *generate
   more tokens before committing*.
4. **Trained by RL, not imitation.** Rewarded for the *right answer*, so it
   **discovers** habits: try paths, double-check, back out of dead ends.

<!--
These four are the load-bearing ideas. #3 is the one to dwell on: "reasoning
effort" / "thinking budget" sliders you see in products are literally how many
draft tokens the model may spend. Hard problem → spend more. #4 sets up the
training slide.
-->

---

## How a reasoning model is trained (3 stages)

You don't train from scratch — you take an ordinary LLM and train it *further*.

```
┌────────────┐   ┌────────────────────┐   ┌────────────────────────┐
│ 1.PRETRAIN │──▶│ 2.FINE-TUNE        │──▶│ 3.REINFORCEMENT LEARNING│
│  base LLM  │   │  (reasoning SFT)   │   │   reward by the RESULT  │
├────────────┤   ├────────────────────┤   ├────────────────────────┤
│ swallow    │   │ hard problems WITH │   │ model writes scratch → │
│ the net →  │   │ step-by-step       │   │ grade right/wrong →    │
│ language + │   │ worked solutions   │   │ reward what worked →   │
│ knowledge  │   │ (chain-of-thought) │   │ SELF-DISCOVERS habits  │
└────────────┘   └────────────────────┘   └────────────────────────┘
 "literate"        "writes its working"     "reasons CORRECTLY"
```

Stage 2 teaches the **form** (show your steps); stage 3 teaches the **substance**
(reason to a *correct* result). Without stage 3 it only *looks* like thinking.

<!--
Demystify "reasoning models" — they're not a different species, just extra
training on top of a normal LLM. The form-vs-substance line explains why some
cheap "chain-of-thought prompting" looks like reasoning but isn't reliable: no
RL on outcomes.
-->

---

## Planning → the pause: stop and ask

The agent reasoned out the cause. But **the fix is a risky human decision** — a
rollback hits users mid-checkout. The model does **not** act alone.

| | Traditional software | Agent |
|---|---|---|
| Where it pauses | programmer **hard-codes** a form at that line | **model decides** at run-time |
| Who picks the question | decided in advance | model generates it on the spot |

It **pauses the loop** and emits a tool call: `AskUserQuestion`.

<!--
Bridge from "thinking" to "acting." The crucial idea: the pause is NOT in the
code. No programmer foresaw "this incident is caused by deploy v2.3." The agent,
reasoning, decides on its own to stop here. That emergence is the whole point.
-->

---

## The pause, step by step

```
1. Model thinking: "cause clear, but rollback is risky — human must choose."
        ▼
2. MODEL emits tool_use: AskUserQuestion
   { question: "How should I handle checkout-api?",
     options: ["Roll back to v2.2", "Keep v2.3, raise the DB pool"] }
        ▼
3. CLIENT runs nothing — it RENDERS a chooser for the SRE
        ▼
4. SRE picks "Roll back to v2.2"
        ▼
5. CLIENT returns that choice to the MODEL (as a tool_result)
        ▼
6. MODEL continues with the decision → calls rollback_deployment
```

**The loop waits at step 3.** That wait *is* the pause.

<!--
Walk it slowly. The client (Claude Code etc.) does NOT execute anything at step
3 — it just shows UI and blocks. This is the same request/response shape as any
tool call; we'll see in the execution part that it's literally the same plumbing.
-->

---

## Asking the user is just a tool call

Two tools declared **identically** — only name + args differ:

```python
tools = [
  { "name": "rollback_deployment",          # CODE tool: real effect
    "parameters": {"properties": {"service": {...}, "to_version": {...}}}},
  { "name": "ask_user",                       # ASK tool: human executes
    "parameters": {"properties": {"question": {...}, "options": {...}}}},
]
```

The branch lives in **your code**, on the tool name:

```python
if call.name == "ask_user":
    result = render_ui_and_wait(args)   # ← SHOW UI, human answers (PAUSE)
elif call.name == "rollback_deployment":
    result = rollback_deployment(**args) # ← REAL call: hit infra API
# send result back to the model — identical for both
```

<!--
Kill the misconception that "human-in-the-loop" is special machinery. It's one
tool whose executor is "a human + a widget." Same tools list, same tool_use,
same "return the result." The only difference is the if-branch. This sets up MCP
perfectly: every tool, human or code, is the same protocol.
-->

---

## Planning — remember

- Traditional software **executes a pre-written procedure**; an agent **reasons
  it out of an intent** at run-time → **reasoning** is the core skill.
- Reasoning = **draft (chain-of-thought) before answering**; more draft = more
  compute (**test-time compute**); learned by **RL on the result**.
- **Stop-and-ask** isn't pre-written — it **emerges** from reasoning, emitted as a
  tool call.
- Ask-the-user and code tools share **one mechanism**; they differ only in **who
  executes** + your `if` branch.

<!--
30-second recap. Then break. After the break we go from "deciding to act" to
"actually acting" — execution and MCP.
-->

---

<!-- _class: part -->

# 2 · Execution

Calling tools, and MCP.

<!--
30 minutes — the longest part. Goal: a precise mental model of MCP — the four
roles, the message flow, tool vs resource, when the tool list loads, and local
vs remote. This is the most hyped, fastest-moving piece of the stack, so
precision matters.
-->

---

## The problem MCP solves

A model alone only knows what's in the conversation. It can't read your files,
call an API, or touch real data.

**MCP (Model Context Protocol):** a standard for connecting AI to external tools
and data.

> Write an MCP server **once** → every MCP-aware AI app can use it.
> No per-model integration.

Think "USB-C for AI tools": one connector, many devices.

<!--
The "write once, use everywhere" framing is the whole value prop. Before MCP,
every tool integration was bespoke per model/app. The standard turns N×M
integrations into N+M. The SRE agent will call its metric and rollback tools
through exactly this.
-->

---

## Four roles (the model is OUTSIDE)

```
              ┌── Cloud (Anthropic) ───┐
              │     Model (Claude)     │   ← inference
              └──────────▲─────────────┘
                         │ API (HTTPS)
┌──────── HOST (Claude Desktop / Code — your machine) ────┐
│   Orchestrator                                          │
│      ├── Client A ──MCP──▶ Server: file-notes ──▶ file  │
│      ├── Client B ──MCP──▶ Server: grafana    ──▶ API   │
│      └── Client C ──MCP──▶ Server: github     ──▶ API   │
└──────────────────────────────────────────────────────────┘
```

- **Model** — cloud inference; never touches a server directly.
- **Host** — the app; the orchestrator bridging cloud ↔ servers.
- **Client** — one per server connection (inside the Host).
- **Server** — exposes tools/resources/prompts → real data.

<!--
The most common confusion: people think the model "connects to" the server. It
does not. The model is on the cloud; the Host relays everything. One Host, many
servers, one Client each. Draw the two bridges: Host↔cloud (API) and
Host↔server (MCP).
-->

---

## The flow — creating a note

```
1. User: "create a note 'Project meeting', content: lock the deadline"
        ▼
2. MODEL picks tool create_note {title:"Project meeting", content:"lock the deadline"}
        ▼
3. CLIENT → SERVER:  tools/call create_note {...}
        ▼
4. SERVER writes the .md, returns "Created note: project-meeting.md"
        ▼
5. CLIENT hands the result back to the MODEL
        ▼
6. MODEL replies: "Created the note 'Project meeting' 👍"
```

**model wants → client calls → server does → result back → model replies.**

<!--
The canonical round trip. Memorize the one-liner at the bottom. Note step 2 vs
3: the model emits an *intent*; the client is what actually speaks MCP. That
separation is why one server serves many models — next slide.
-->

---

## The model emits intent; the client translates

```jsonc
// ① Model emits (its own format)
{ "type": "tool_use", "name": "create_note",
  "input": { "title": "Project meeting", "content": "lock the deadline" } }

// ② Client translates to an MCP message to the server
{ "jsonrpc": "2.0", "id": 2, "method": "tools/call",
  "params": { "name": "create_note", "arguments": { ... } } }

// ③ Server returns
{ "jsonrpc": "2.0", "id": 2,
  "result": { "content": [ { "type": "text", "text": "Created: project-meeting.md" } ] } }
```

The model **never writes JSON-RPC.** The client always normalizes to MCP → the
**server sees one format** → one server works for many models.

<!--
This is the architectural payoff. The model speaks "tool_use" in its own dialect;
the client is the adapter to MCP. Because of that boundary, your server doesn't
care whether Claude or some other model called it. Decoupling = reuse.
-->

---

## How does the model "read" a tool?

On connect, the client asks `tools/list`; the server's descriptions are injected
into the model's context. You **don't hand-write** them — FastMCP generates from
the docstring + type hints:

```python
@mcp.tool()
def create_note(title: str, content: str) -> str:
    """Create a new Markdown note."""   # docstring → description
```
→
```json
{ "name": "create_note", "description": "Create a new Markdown note.",
  "inputSchema": { "type":"object",
    "properties": {"title":{"type":"string"}, "content":{"type":"string"}},
    "required": ["title","content"] } }
```

**Clear docstrings + type hints = the model's only guide** for when/how to use a
tool.

<!--
Practical takeaway for anyone writing a server: your docstring IS the prompt. A
vague docstring → the model misuses or ignores the tool. This is prompt
engineering hiding in your function signatures.
-->

---

## Tool or Resource?

| What you need | Use | Server returns |
|---|---|---|
| Create a note (write to disk) | tool `create_note` | "Created..." |
| Read an existing note for Claude | resource `note://...` | the note's contents |

**tool = do work · resource = read data**

(Servers also offer **prompts** — pre-written command templates, e.g.
`summarize_notes`.)

<!--
Quick but real distinction. Tools have side effects / do actions; resources are
read-only like an HTTP GET. Many beginners model everything as tools — resources
are how you expose data the model can pull on demand.
-->

---

## When is the tool list loaded? (init)

**Once**, at connection open — not per message.

```
CLIENT                                  SERVER
  │ ① initialize  ───────────────────▶ │  handshake, versions
  │ ◀── "I have tools/resources" ────── │
  │ ② initialized (notify) ──────────▶  │
  │ ③ tools/list  ───────────────────▶  │  ◀── loaded HERE, then CACHED
  │ ◀── [create_note, read_note, ...] ─ │
  ════════ connection ready ════════
```

Each chat turn reuses the **cached** list. Reload only on reconnect or
`notifications/tools/list_changed`.

<!--
Why this matters: the tool list costs context tokens on every turn. It's cached,
not re-fetched, but it IS re-injected each turn — so a server exposing 200 tools
bloats every prompt. Keep servers focused; expose only the tools an agent needs.
-->

---

## Local or Remote? — two independent axes

| Kind | Where the server runs | Client connects via |
|------|-----------------------|---------------------|
| **stdio** (local) | your machine, client spawns it | stdin/stdout pipe |
| **HTTP / SSE** (remote) | a far server | a **URL** (https://…) |

1. *Where does the server **run**?* local vs remote
2. *Where does the server **get data**?* local file vs remote API

> `file-notes` = local server + local files. Grafana MCP = local server calling a
> **remote API** — or a remote server hosted by Grafana.

<!--
Don't conflate the two axes. A server can run locally yet reach across the
internet for data. "Ask Grafana MCP for a dashboard" = tool call → server hits
Grafana's API → returns TEXT → model describes it. The model never sees the chart
image; it reasons over text. Important expectation-setting for ops use.
-->

---

## The working example — `file-notes`

A Python MCP server: create/read/update/delete/search Markdown notes + file ops
inside a **sandbox**.

- **Tools** — `create_note`, `read_note`, `list_notes`, `update_note`,
  `delete_note`, `search_notes`, `list_files`, `read_file`, `write_file`,
  `file_info`
- **Resources** — `note://{name}`, `notes://index`
- **Prompts** — `summarize_notes`
- 🔒 every path through `_safe_path()` → can't escape `data/`

```bash
mcp dev server.py     # MCP Inspector — click through each tool
claude mcp add file-notes -- /path/.venv/bin/python /path/server.py
```

<!--
If there's a live machine, demo it here: open the Inspector, call create_note,
show the file appear, read it back as a resource. The sandbox point matters —
_safe_path is the first taste of "tool calls are real actions; constrain them" —
the model can ask for anything, so the server is where you draw the boundary.
-->

---

## Execution — remember

- MCP = write a tool **once**, any MCP-aware model uses it.
- Four roles: **Model** (cloud) · **Host** (orchestrator) · **Client** (one per
  server) · **Server** (tools/resources/prompts).
- Model emits *intent* → **client translates** to JSON-RPC → server sees one
  format.
- **tool = do · resource = read** · tool list loaded **once** + cached.
- "Where it runs" ⟂ "where the data is."

<!--
Recap. We can now ACT. But acting isn't finishing — calling rollback_deployment
doesn't mean the incident is over. That's the next part: review.
-->

---

<!-- _class: part -->

# 3 · Review

The agent grades, verifies, and closes the loop.

<!--
25 minutes. The "are we actually done?" box. Source: Andrew Ng's Reflection
pattern + Reflexion. Key message: calling the tool ≠ fixing the problem. We
return to the SRE — did the rollback actually clear the 5xx?
-->

---

## Fluent ≠ correct

LLMs are **confidently fluent**, even when wrong. First drafts are usually *okay*,
rarely *optimal*: missing steps, invented numbers, skipped edge cases — or
**thinking it fixed the incident when it's still burning.**

```
NO review                       WITH review
────────                        ───────────
"Rolled back, done!"            "Are the 5xx really gone?"
(believes itself)               → verify against REAL metrics
        │                       → still failing? → re-plan
        ▼                       → clear? → only then say "fixed"
  WRONG report,
  incident still on fire
```

> Doubt the output by default. Review turns *"seems done"* → *"verified done."*

<!--
The motivating failure. An agent that trusts its own "done" is dangerous on a
prod system. This slide justifies the entire box: confidence is not correctness.
-->

---

## The Reflection pattern — generate → critique → fix

```
        ┌──────────────────────────────────────┐
        ▼                                       │ not good → fix
  ① GENERATE  (produce answer / action)         │
        │                                       │
        ▼                                       │
  ② CRITIQUE  ──"errors? missing? wrong?"───────┘
        │
        ▼  good
  ③ FINALIZE
```

**Critiquing is easier than generating.** "Write a perfect report" is hard;
"here's a draft, find 3 weak spots" is easy. Splitting the roles gives two angles
on one problem.

<!--
Connect to part 1: reasoning = draft BEFORE answering; reflection = re-read
AFTER answering and rewrite. Same trade — spend tokens to buy correctness — just
applied to the first draft. The "critique is easier than generation" asymmetry is
why this works at all.
-->

---

## Two kinds of review

| | **Self-critique** | **Grounded verification** |
|---|---|---|
| Leans on | the model's own reasoning | real-world evidence (tool/test/metric) |
| Question | "Is this reasoning sound?" | "Did the action actually work?" |
| Weakness | can be **confidently wrong** | needs a tool/data to check |
| Example | re-read, fix wording | re-query 5xx to see if it normalized |

> Self-critique alone is **not enough**: misunderstand the problem → critique by
> the same misunderstanding. The strongest review is **anchored to external
> truth.**

<!--
THE key distinction of this part. A model grading its own logic shares its own
blind spots. Grounding = calling back into the execution tools to get ground
truth. This is where review reaches back to part 2.
-->

---

## Grounded verification — the SRE agent

```
① already called rollback_deployment(checkout-api → v2.2)   [execute]
        ▼
② REVIEW: call the measuring tool AGAIN (grounded)
   query_metrics(service="checkout-api", metric="5xx_rate", window="5m")
        │
        ├─▶ 5xx = 0.1% (normal < 0.5%)
        │     ✅ PASS → "Resolved. Cause v2.3 shrank DB pool, rolled back to
        │              v2.2, 5xx 0.1% at 14:41." → record lesson (episodic)
        │
        └─▶ 5xx = 6% (STILL high)
              ❌ NOT PASS → back to PLAN: "hypothesis wrong, or 2nd cause.
                 Re-reason from new data."
```

**The agent may not take credit for itself** — re-measure the *same signal* that
raised the alarm.

<!--
The concrete payoff. It must use the 5xx metric — the very signal that fired —
not its own belief. If 5xx is still high, the "it's the deploy" hypothesis is
falsified and we loop back to planning. This is the loop closing in real time.
-->

---

## Who reviews? — itself, a judge, or hard checks

1. **Self-review** — model re-reads its own output. Cheap; blind to its own
   systematic errors.
2. **LLM-as-judge** — a *second* model grades against a rubric. Independent angle;
   the common way to auto-grade at scale.
3. **Deterministic checks** — no model: tests, schema validation, lint, metric
   thresholds, policy gates. Most trustworthy.

> **Whatever a machine can check, don't ask the model to "feel."**
> Judge model → qualitative (text, argument). Hard checks → quantitative (tests,
> 5xx < threshold, valid JSON).

<!--
Practical guidance. Teams over-use LLM-as-judge for things a unit test or a
threshold could verify deterministically and cheaply. Use the model only for the
genuinely qualitative. The 5xx threshold check is a hard check, not a vibe.
-->

---

## Closing the loop — and the brakes

```
review ──┬── PASS ──────▶ finalize → write memory → DONE
         └── NOT PASS ──▶ feed errors into planning → re-think → review again
```

The loop **must have a brake**, or it fixes-grades-fixes forever (or repeats a bad
action on prod). Stop on:

- **Criteria met** — success (5xx under threshold, tests green)
- **Budget exhausted** — too many rounds / tokens / time
- **No progress** — new round not measurably better
- **Beyond authority** — **escalate to a human** (another `AskUserQuestion`)

<!--
The classic agent bug is the missing brake — infinite review loops burning tokens
or, worse, repeatedly acting on production. "Knowing when to stop" = "knowing how
to fix." Note escalation reuses the exact stop-and-ask tool from part 1 — the
loop folds back on itself.
-->

---

## Review — remember

- Output is **fluent ≠ correct** → doubt it before finalizing.
- **Reflection** = generate → critique → fix; *critiquing is easier than
  generating.*
- **Self-critique** (own reasoning, can be confidently wrong) vs **grounded
  verification** (anchored to truth). Re-measure 5xx, don't self-certify.
- Reviewer: **self / judge model / hard checks** — machine-checkable → don't
  "feel" it.
- Review **closes the loop** and **must have stopping conditions**.

<!--
Recap, then second break. After it: memory — the state that lets the agent
improve across loops and sessions instead of starting from zero each time.
-->

---

<!-- _class: part -->

# 4 · Memory

The four kinds every agent needs.

<!--
25 minutes. Source: Martin Keen's "Four Types of Memory" + mem0. Goal: the four
types, the type-vs-scope distinction, write/retrieve, and the jump from a
file-based demo to a production memory layer.
-->

---

## Why memory? — an LLM is stateless

Each call sees only what's in the context, then **forgets everything.** End of
session → forgets your name, what it just did, the lesson from a turn ago.

An **agent** acts across many steps, turns, sessions. It needs memory to:

- hold the current context
- recall what happened
- know facts (world + you)
- know *how* to do things

> Borrowing from human cognitive science: **four kinds**, and an agent needs all
> four.

<!--
Motivate before taxonomy. The SRE agent that just resolved an incident is useless
next week if it can't remember the v2.3 lesson. Stateless model + persistent
agent = you must add memory deliberately. The four-type model comes straight from
how humans remember.
-->

---

## The four types

```
                         AGENT MEMORY
        ┌──────────────────────┴───────────────────────┐
        ▼                                               ▼
  SHORT-TERM (working)                        LONG-TERM
  "thinking right now"          ┌──────────┬──────────┬───────────┐
                                ▼          ▼          ▼
                            Episodic    Semantic   Procedural
                           "happened"   "facts"    "how-to"
```

**working = RAM now · episodic = diary · semantic = knowledge · procedural =
skills**

<!--
The mnemonic at the bottom is what they should walk out remembering. Working is
short-term; the other three are long-term and split by what they hold: events,
facts, skills. Next four micro-slides, one each.
-->

---

## 1 · Working · 2 · Episodic

**Working memory (short-term)** — the *current task's* context: recent messages,
last tool result, current goal. It **is** the context window (RAM).
- Limit: token count → full means trim/summarize. Lost at session end.

**Episodic memory (long-term)** — **specific events**: what, when, with what,
outcome. A *diary*.
- Used for **case-based reasoning** — learn from a prior case; few-shot from
  history.
- Stored in indexed logs / old sessions.
- *"Last week you preferred a short table"* → does it again.

<!--
Working = the live context window we discussed in planning (the scratchpad lives
here too). Episodic is the agent's experience log — this is where the SRE's
"v2.3 caused 5xx" lesson lives. Case-based reasoning is the value: pattern-match
this incident to a past one.
-->

---

## 3 · Semantic · 4 · Procedural

**Semantic memory (long-term)** — **generalized facts**, not tied to an event:
"Paris is the capital of France," "customer A is Enterprise."
- Used for **grounding** — anchor answers in fact, not invention.
- Stored in vector DB (RAG), knowledge graph, user profile.

**Procedural memory (long-term)** — **how-to**: steps, tool conventions, the
"rules of the game." Often *not* in data but in **system prompt, code, weights.**
- Used to execute multi-step tasks consistently.

> Episodic = *what happened* · Semantic = *what's true* · Procedural = *how to do
> it.*

<!--
Semantic is exactly the RAG layer from the data section of the stack — facts the
agent looks up. Procedural is the one people forget is "memory": your system
prompt and tool definitions ARE the agent's learned skills. The three-way
contrast at the bottom is the test-question answer.
-->

---

## Quick comparison

| Type | Span | Answers | Stored in |
|------|------|---------|-----------|
| **Working** | Short | "What am I doing now?" | Context window |
| **Episodic** | Long | "What happened before?" | Indexed logs / old sessions |
| **Semantic** | Long | "What is true?" | Vector DB (RAG), knowledge graph |
| **Procedural** | Long | "How do I do this?" | System prompt, code, tools, weights |

<!--
One table to rule them all. If a slide gets photographed in this part, it's this
one. Pause here and let them copy it.
-->

---

## Write and retrieve — both directions

```
EXPERIENCE → [write] → long-term store → [retrieve at the right moment]
          → inject into working memory → model uses it
```

- **Write:** after each turn, distill what's worth keeping (don't store
  everything — the *non-trivial*).
- **Retrieve:** find the **relevant** memory (similarity search) and load it back
  into working memory.

> Working memory is finite → **choosing what to load** is the crux.

<!--
A store you only write to is useless; a store you never write to is empty. Both
directions. The hard part is retrieval relevance — with thousands of memories,
pulling the right three into a limited context is the real engineering problem.
Sets up why mem0 exists.
-->

---

## Type vs Scope — two independent axes

- **Type** (working / episodic / semantic / procedural) = the *content*.
- **Scope** = *who/where it applies*: `session → user → agent → org`.

Any type sits at any scope. Episodic, for example:

| Scope | Episodic at that scope |
|-------|------------------------|
| **Session** | events within this session (gone after) |
| **User** | a diary across **all sessions, all projects** |
| **Agent / Org** | events shared across agents / a team |

> Episodic isn't bound to one project — a real system keeps it **user-level,
> cross-session.**

<!--
The subtle point people miss. Type and scope are orthogonal. Claude Code happens
to scope memory by directory, but a proper system remembers "you hit error X last
week" even in a different project. This is exactly what a production memory layer
gets right and ad-hoc files get wrong.
-->

---

## Local demo (Claude Code) → production (mem0)

Claude Code alone (files on disk) demos **all four** — single, local, one person:

| Type | Claude Code uses |
|------|------------------|
| Working | session context window (auto-summarizes) |
| Semantic | fact files in `memory/` + `MEMORY.md` |
| Episodic | old transcripts (`--resume`) + `feedback`/`project` files |
| Procedural | `CLAUDE.md` + skills + system prompt + tools |

At **multi-agent production**, hand-managed files break in 3 ways → **mem0**:

1. **Scope & sharing** — keyed by user/session/agent/org; many agents share one
   store.
2. **Smart retrieval at scale** — vector + graph; `grep` can't keep up at
   thousands.
3. **Auto write/merge** — distill, dedupe, reconcile contradictions automatically.

<!--
The jump from a local file demo to a real production layer. mem0 is NOT
"cloud memory" (it self-hosts) — it's a shared, scoped, auto-managed memory layer
with real retrieval. The three pain points are exactly what you hit the day you
go multi-agent.
-->

---

## Memory — remember

- An LLM is **stateless**; an agent needs memory to persist across steps/sessions.
- Four types: **working** (RAM now) · **episodic** (diary) · **semantic** (facts)
  · **procedural** (how-to).
- **Type** and **scope** (session/user/agent/org) are **independent** axes.
- Long-term memory needs **write** (distill) + **retrieve** (load the relevant
  bit).
- Files demo all four; **mem0** is the production layer for scope, retrieval, and
  auto-merge.

<!--
Recap. Now we have all four boxes. Final part: run the whole loop once,
end to end, on the incident — so they see the pieces working as one system.
-->

---

<!-- _class: part -->

# 5 · Putting it together

The loop, end to end.

---

## One incident, the whole loop

```
14:35  alert: checkout-api 5xx spike. SRE: "deal with it."

 PLAN     reason: 5xx since 14:32 → deploy v2.3 at 14:30 → logs: DB
          timeout → v2.3 shrank the pool. Cause = the deploy.
          Rollback is risky → AskUserQuestion → "roll back to v2.2"
   ▼
 EXECUTE  call rollback_deployment(checkout-api → v2.2)        [MCP]
   ▼
 REVIEW   grounded: query_metrics(5xx, 5m) → 0.1% ✅
          (still 6%? → back to PLAN with new data)
   ▼
 MEMORY   episodic: "v2.3 shrank DB pool → 5xx; rollback fixed it"
          → next time, this class of incident resolves faster
```

<!--
The capstone. Walk it once more, naming each box. The point: these aren't four
topics, they're one machine. Plan reasons + pauses; execute calls a real tool via
MCP; review verifies against the same 5xx signal; memory banks the lesson. Note
how stop-and-ask (part 1) and escalation (part 3) are the same tool, and how
review calls back into execution's tools — the parts interlock.
-->

---

## Takeaways

1. A model is a **chat box**; the **loop** (plan→execute→review→memory) makes it
   an **agent**.
2. **Planning** = reasoning: draft before answering, spend test-time compute,
   stop-and-ask when it's a human's call.
3. **Execution** = tool calling via **MCP**: write once, use everywhere.
4. **Review** = verify against **truth**, not the model's confidence; always have
   a **brake**.
5. **Memory** = four types × scope; **write + retrieve**; files → mem0.
6. **Use both kinds** — graft an agent onto your existing deterministic workflow:
   it reads your alerts and **reduces toil**; the static layer guards, the agent
   reasons.

<!--
The six lines to leave them with. If short on time, the must-keep slides are: the
loop, who-writes-the-steps, the MCP four roles, fluent≠correct + grounded
verification, the four memory types, and this incident capstone.
-->

---

<!-- _class: lead -->
<!-- _paginate: false -->

# Thank you

Questions?

*Full notes & sources: this folder's `README.md`*

<!--
Likely questions: "always use a reasoning model?" (no — match effort to
difficulty); "is MCP the only way to call tools?" (no — native function calling
or CLI work too; MCP is the open standard for reuse); "can the agent fix prod by
itself?" (remediation stays human-in-the-loop — escalation is a feature);
"do I need mem0 to start?" (no — files demo all four; adopt a layer when you go
multi-agent).
-->

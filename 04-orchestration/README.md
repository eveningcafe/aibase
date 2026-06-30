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

**Combine both — an SRE agent on top of your existing alerting.** Keep your
current deterministic pipeline (monitoring → alert rules → on-call routing →
runbooks) as the reliable backbone — don't rip it out. Then **add an agent on
top of it**:

- it **reads the same alerts your workflow already sends** (no new alerting
  pipeline needed);
- it **investigates the cause for you** — the messy, multi-step triage and
  root-cause analysis (RCA) that fixed `if/else` rules can't do;
- it does the **boring, repeating manual checks** for you — what SRE calls
  *toil* (the low-value work on-call engineers grind through by hand);
- it **asks a human before any risky action** (e.g. a production rollback).

So the static layer still routes and guards; the agent adds the judgment in the
middle. You don't replace the workflow — you add a smart helper on top of it.

## The loop

```
plan ──▶ execute (tools) ──▶ review ──▶ (loop)
   ▲                                        │
   └──────────── memory / state ◀───────────┘
```

## What goes here

| Dir | Role | Notes |
|-----|------|-------|
| `planning/` | **Thinking** | Task decomposition, reasoning, deciding what data/tools are needed. |
| `execution/` | **Acting** | Invoking tools to do the work — via native function calling, CLI/shell, or MCP-served tools (see `execution/mcp/`). |
| `review/` | **Reviewing** | Self-critique and feedback loops to improve outputs. |
| `memory/` | **State** | Short/long-term memory, context preserved across turns & sessions. |

> The working example throughout this layer is a small MCP server, `file-notes`,
> that ties execution to memory and planning.

## Notes

- This layer is the fastest-evolving part of the stack (MCP, new agent
  architectures, agent gateways).
- Routing (which model/tool/agent handles a step) lives here too.

---

# The lecture: orchestration, end to end

The rest of this README is a **self-contained walkthrough** of the four boxes in
the loop — *plan → execute → review → memory*. Read it top to bottom and you have
the whole layer; you don't need to open the sub-folders. A companion slide deck
(`slides.md` / `slides.pdf`) covers the same material as a ~2-hour lecture.

## The running example — an SRE agent

We follow one story the entire way through so each concept lands on something
concrete.

> **14:35 — an alert fires.** Service `checkout-api` is throwing a **spike of
> 5xx errors**. The on-call SRE does *not* type out a runbook. They state an
> **intent**: *"checkout-api is throwing 5xx, deal with it."* From here an agent
> takes over — it *reasons* toward a root cause, *stops to ask* whether to roll
> back, *acts* by calling a real tool, *verifies* the fix against live metrics,
> and *remembers* the lesson for next time.

Each section below is one box of the loop, told through this incident.

---

## 1 · Planning — the agent thinks, pauses, and asks

> Adapted from IBM Technology, *What Are Large Reasoning Models (LRMs)?* and
> DeepSeek-R1 (2025).

### What makes this different from traditional software?

The whole difference is **who writes the steps.**

```
TRADITIONAL SOFTWARE                  AGENT (SRE on-call)
─────────────────────                 ───────────────────
Runbook is written AHEAD of time,     User states an INTENT:
reviewed/compiled BEFORE it runs.     "checkout-api is throwing 5xx, fix it"
                                              │
if error_rate > 5%:                           ▼
    restart_pods()                    MODEL invents the steps AT RUN-TIME:
elif latency > 1s:                      1. metrics: when did 5xx start?
    scale_up()                          2. any deploy around that time?
                                        3. read logs → find the cause
Machine only runs the script you        4. (rollback? → ASK the human)
foresaw. A novel situation outside      5. roll back / scale, then re-verify
the script → it's stuck.
```

- **Traditional software:** the procedure is **composed ahead of time**
  (compose-time). Every `if/else`, every loop, every "stop and ask the user" is
  *typed by a programmer in advance*. The machine never thinks — it **executes**.
- **Agent:** the user supplies only an **intent**, not a procedure. The agent
  must **invent the steps at run-time**, different each time, depending on
  context.

> Traditional software is a written recipe — follow it exactly. An agent is a
> chef told *"make something good for four vegetarians"* and left to decide.

Because the steps are no longer written for it, the core capability of this layer
is **reasoning** — turning *intent* into a *plan*. That is why "reasoning models"
exist.

### What is a reasoning model actually doing? (down to the token)

Remember how an LLM produces text: **one token at a time, sequentially
(autoregressive)**. At each step it looks at *all* the text so far, computes
probabilities for the next token, picks one, appends it, and repeats.

```
ORDINARY MODEL (checkout-api incident):
prompt ──▶ [blurts an answer immediately] ──▶ "Try restarting the pods."
           (fast guess, easily wrong about the real cause)

REASONING MODEL:
prompt ──▶ [emits a PILE of "thinking" tokens first] ──▶ then concludes
           ┌───────────────────── scratchpad ────────────────────────┐
           │ "5xx rising since 14:32. What changed near then?        │
           │  → deploy v2.3 at 14:30. Suspect the deploy. Logs say   │
           │  'DB connection timeout'. Did v2.3 change pool size?    │
           │  → yes, pool dropped to 5. So the cause is deploy v2.3, │
           │  NOT a traffic surge."                                  │
           └─────────────────────────────────────────────────────────┘
                                   │
                                   ▼
            "Cause: deploy v2.3 shrank the DB pool. Fix: roll back."
```

That chain of "thinking" tokens (**chain-of-thought**) *is* the reasoning. A few
things that matter at the token level:

1. **Thinking tokens are just ordinary tokens** — produced the same way. No
   magic; the model is writing a draft *before* writing the answer.
2. **Each token it writes feeds back into the context and steers the next.** The
   model is **writing notes to itself**. "Oh, that's wrong, back up" genuinely
   changes the tokens that follow. Better scratch work → more-likely-correct
   answer.
3. **Each token = one chunk of compute (one forward pass).** More scratchpad
   tokens = **more compute spent** on the problem. This is **test-time compute** —
   "thinking longer" literally means *generating more tokens before committing*.
   Hard problem → let it think longer.
4. **Trained by RL, not imitation.** Ordinary models learn by *imitating*
   human-written text. Reasoning models (o1, DeepSeek-R1…) are **rewarded for
   reaching the right answer**, regardless of the scratch work. So they
   **discover** useful habits — try several paths, double-check, back out of dead
   ends — without anyone scripting the steps.

#### How is a reasoning model trained? (3 stages)

You don't train one from scratch. You **take an ordinary LLM and train it
further** to reason, in three back-to-back stages:

```
┌──────────────┐   ┌───────────────────────────┐   ┌──────────────────────────┐
│ 1. PRETRAIN  │──▶│ 2. FINE-TUNE (reasoning)   │──▶│ 3. REINFORCEMENT LEARNING│
│   base LLM   │   │   teach it to LAY OUT a    │   │   REWARD by the RESULT    │
│              │   │   step-by-step solution    │   │                           │
├──────────────┤   ├───────────────────────────┤   ├──────────────────────────┤
│ swallows the │   │ data = HARD problems       │   │ model generates scratch → │
│ internet     │   │ (math, code, logic,        │   │ graded right/wrong →      │
│ → language   │   │  science), each WITH a     │   │ REWARD the scratch that   │
│ + world      │   │ step-by-step chain         │   │ led to a correct answer → │
│ knowledge    │   │ (chain-of-thought)         │   │ it SELF-DISCOVERS habits  │
└──────────────┘   └───────────────────────────┘   └──────────────────────────┘
  "literate,         "knows how to WRITE its       "knows how to reason CORRECTLY,
   knows the world"   working for hard problems"     self-corrects — unscripted"
```

- **Stage 1 — Pretrain:** unsupervised learning on a huge text corpus → language
  and background knowledge. (Same as any ordinary LLM.)
- **Stage 2 — Reasoning fine-tune (SFT):** supervised learning on **hard
  problems** that ship **with worked step-by-step solutions**. Teaches the model
  the *habit of writing scratch work* before answering.
- **Stage 3 — RL:** the model generates its own scratch work, the **final answer
  is graded right or wrong**, and runs that ended correctly are rewarded. Because
  only the *result* is rewarded, the model **invents** better scratch-work
  strategies on its own — including "aha" moments where it catches its own mistake
  and backs up.

> Stage 2 teaches the *form* (show your steps); stage 3 teaches the *substance*
> (reason your way to a correct result). Without stage 3 a model only *looks like*
> it's thinking.

This scratch-work chain **is** planning: while "thinking," the model
**decomposes** the intent into steps and decides **which tools/data it needs** —
including realizing *"I'm missing information here, I have to ask the user."* That
leads straight into the next idea.

### Stopping to ask the user

The biggest break from traditional software is here:

| | Traditional software | Agent |
|---|---|---|
| Where it pauses to ask | Programmer **hard-codes** a form / `input()` at that exact line | **Model decides** at run-time, wherever it sees the need |
| Who picks the question | Decided in advance | Model generates the question + options on the spot |

Back to the SRE agent: it has reasoned out the cause (deploy v2.3 shrank the DB
pool). But **how to fix it is a risky human decision** — a rollback affects users
mid-checkout. The model does **not** roll back on its own. It **pauses the loop**
and emits a tool call named `AskUserQuestion`.

```
1. Model is thinking: "cause is clear, but rollback is a risky action —
   a human must choose: roll back, or hotfix?"
        │
        ▼
2. MODEL emits tool_use: AskUserQuestion
   { question: "How should I handle checkout-api?",
     options: ["Roll back to v2.2", "Keep v2.3, raise the DB pool"] }
        │
        ▼
3. CLIENT (e.g. Claude Code) runs nothing —
   it RENDERS a prompt for the SRE to choose
        │
        ▼
4. SRE picks "Roll back to v2.2"
        │
        ▼
5. CLIENT returns "Roll back to v2.2" to the MODEL (as a tool_result)
        │
        ▼
6. MODEL continues with the decision made → calls rollback_deployment
```

The key point: **this pause is not written anywhere in the code.** It *emerges
from the reasoning*. No programmer could foresee that *this* incident was caused
by deploy v2.3 — but the agent, facing that situation, knows to stop and ask.

### Asking the user is just an ordinary tool call

People think "ask the user" is a special mechanism. It is **not.** It uses the
*same* tool-calling mechanism as everything else (covered in §2): `tool_use →
result → keep thinking`. The only difference is **who executes the tool** — this
time a *human through a UI*, instead of a server running code.

At the API level, **every tool is declared identically** in one list, each with
its own schema:

```python
tools = [
    {   # a CODE tool — REAL effect on the system (like the server in §2)
        "name": "rollback_deployment",
        "description": "Roll a service back to a previous version",
        "parameters": {"type": "object", "properties": {
            "service": {"type": "string"}, "to_version": {"type": "string"}},
            "required": ["service", "to_version"]},
    },
    {   # the "ask the user" tool — just another tool, schema shapes the question
        "name": "ask_user",
        "description": "Ask the user for a decision when the agent can't decide",
        "parameters": {"type": "object", "properties": {
            "question": {"type": "string"},
            "options": {"type": "array", "items": {"type": "string"}}},
            "required": ["question", "options"]},
    },
]
```

The model emits the **same format** for both — only the name + arguments differ.
**The branch lives in YOUR code, switching on the tool name** — that is the only
place the difference exists:

```python
resp = client.chat.completions.create(model=..., messages=msgs, tools=tools)
call = resp.choices[0].message.tool_calls[0]
args = json.loads(call.function.arguments)

if call.function.name == "ask_user":
    result = render_ui_and_wait(args)        # ← SHOW UI, SRE answers (loop PAUSES here)
elif call.function.name == "rollback_deployment":
    result = rollback_deployment(**args)     # ← REAL call: hit infra API, roll back

# send the result BACK to the model — identical for both kinds
msgs.append({"role": "tool", "tool_call_id": call.id, "content": str(result)})
resp = client.chat.completions.create(model=..., messages=msgs, tools=tools)  # think on
```

So: **asking the user is a tool** whose "executor" is *a human + a chooser
widget*; the loop **waits** at `render_ui_and_wait(...)` — that's the pause; and
no special machinery is needed.

### Remember (planning)

- Traditional software **executes a pre-written procedure**; an agent **reasons
  the procedure out of an intent** at run-time → **reasoning** is the core skill.
- Reasoning at the token level = the model **writes a draft (chain-of-thought)
  before answering**; more draft = more compute (test-time compute); learned by
  **RL rewarding the result**.
- **Stopping to ask** is not pre-written — it *emerges from reasoning* and is then
  emitted as a **tool call** (`AskUserQuestion`).
- The ask-the-user tool and code tools use the **same mechanism**; they differ
  only in **who executes** and the `if` branch in your code.

---

## 2 · Execution — calling tools, and MCP

> The "acting" box. The agent has a decision; now it must *do* something to the
> real world. It does so by calling tools — and the open standard for serving
> those tools is **MCP**.

### What is MCP?

On its own, a model like Claude only knows what's in the conversation — it can't
read your files, call an API, or touch real data.

**MCP (Model Context Protocol)** is a standard for connecting AI to external tools
and data. Write an MCP server once, and every MCP-aware AI app can use it — no
per-model integration.

### Architecture

Four roles (the model lives **outside**, on the cloud):

- **Model** — runs inference on the cloud (e.g. Anthropic). The Host calls it over
  an API. It is *not* inside the app and does *not* talk to servers directly.
- **Host** — the app you run (Claude Desktop, Claude Code). It is the
  **orchestrator**: one side calls the model over an API, the other side manages
  connections to servers.
- **Client** — lives inside the Host; each Client holds **one** connection to
  **one** Server.
- **Server** — a program that exposes tools/resources/prompts (e.g. `server.py`)
  and connects to real data: files, databases, APIs…

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

The Host bridges **two sides**: up to the cloud (send messages + tools, receive
the intent to call a tool) and down to the servers (the Client executes the tool).
The cloud model never touches a server directly — everything is relayed through
the Host. One Host plugs in many Servers at once, each via its own Client.

### Flow (creating a note)

```
1. User: "create a note 'Project meeting', content: lock the deadline"
        │
        ▼
2. MODEL picks the create_note tool, with data
   {title:"Project meeting", content:"lock the deadline"}
        │
        ▼
3. CLIENT sends to the server:  tools/call create_note {...}  ──▶ SERVER
        ▼
4. SERVER writes the .md file, returns: "Created note: project-meeting.md"  ◀──
        ▼
5. CLIENT hands the result back to the MODEL
        ▼
6. MODEL replies to the user: "Created the note 'Project meeting' 👍"
```

In short: **model wants → client calls the tool → server does it → result back to
client → back to model → model replies.**

### How does the model "read" a tool?

On connect, the client asks the server `tools/list`. The server returns a
description of each tool, which the client injects into the model's context. You
**don't write** these descriptions by hand — FastMCP generates them from the
docstring + type hints:

```python
@mcp.tool()
def create_note(title: str, content: str) -> str:
    """Create a new Markdown note."""   # docstring → description
```

becomes:

```json
{
  "name": "create_note",
  "description": "Create a new Markdown note.",
  "inputSchema": {
    "type": "object",
    "properties": { "title": {"type":"string"}, "content": {"type":"string"} },
    "required": ["title", "content"]
  }
}
```

→ So **docstrings and type hints must be clear**: the model relies on them to know
when to use a tool and what to fill in.

### Tool or Resource?

| What you need | Use | Server returns |
|---|---|---|
| Create a note (write to disk) | tool `create_note` | "Created..." |
| Read an existing note for Claude | resource `note://...` | the note's contents |

Quick memory aid: **tool = do work, resource = read data.**

### When is the tool list loaded? (init)

The tool list is loaded **once** when the connection opens — **not** per message.
"Connecting" = when the client starts the server: opening the app (Claude
Desktop), starting a session (Claude Code), or clicking Connect (Inspector).

```
CLIENT                                  SERVER
  │ ① initialize  ───────────────────▶ │  handshake, exchange versions
  │ ◀── "I have tools/resources" ────── │
  │ ② initialized (notify) ──────────▶  │
  │ ③ tools/list  ───────────────────▶  │  ◀── tool list loaded HERE
  │ ◀── [create_note, read_note, ...] ─ │      (called once, then CACHED)
  ════════ connection ready ════════
```

After that, on **each chat turn** the client takes the cached list and injects it
into the context sent to the model — it does not re-ask the server. It reloads
only on a new connection (restart/reconnect) or when the server sends
`notifications/tools/list_changed`.

### Local or Remote?

An MCP server **need not run on your machine** — there are two transports:

| Kind | Where the server runs | Client connects via |
|------|-----------------------|---------------------|
| **stdio** (local) | on your machine, client spawns it | stdin/stdout pipe |
| **HTTP / SSE** (remote) | on a far server | a **URL** (https://…) |

Two **independent** axes:

1. *Where does the server run?* local vs remote.
2. *Where does the server get data?* local file vs remote API.

Example: `file-notes` = a **local** server reading **local files**. A Grafana MCP
might be a **local** server calling a **remote** Grafana API — or a **remote**
server hosted by Grafana. "Ask Grafana MCP for a dashboard" = model calls a tool →
server calls the Grafana API → returns **text** → model describes it (it does not
*see* the chart image).

### The working example — `file-notes`

A Python MCP server that lets Claude create/read/update/delete/search Markdown
notes and do file operations inside a safe sandbox directory:

- **Tools** — notes: `create_note`, `read_note`, `list_notes`, `update_note`,
  `delete_note`, `search_notes`; files: `list_files`, `read_file`, `write_file`,
  `file_info`.
- **Resources** — `note://{name}`, `notes://index`.
- **Prompts** — `summarize_notes`.
- 🔒 Every path goes through `_safe_path()` → it cannot escape the `data/`
  directory.

```bash
# install
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# run & test
mcp dev server.py     # MCP Inspector to click through each tool (recommended)
python server.py      # run directly over stdio

# register with Claude Code
claude mcp add file-notes -- /path/to/.venv/bin/python /path/to/server.py
claude mcp list
```

### Remember (execution / MCP)

- MCP is a standard so a tool written once works with any MCP-aware model.
- Four roles: **Model** (cloud) · **Host** (orchestrator) · **Client** (one per
  server) · **Server** (exposes tools/resources/prompts).
- The model emits an *intent* to call a tool; the **client translates** it to
  JSON-RPC; the server only ever sees one format → one server, many models.
- **tool = do work, resource = read data.** Tool list is loaded **once** at init
  and cached.
- Local vs remote (where it runs) is **independent** from local vs remote data.

---

## 3 · Review — the agent grades, verifies, and closes the loop

> Adapted from Andrew Ng, *Agentic Design Patterns: Reflection* and Shinn et al.,
> *Reflexion* (2023).

This is the **last** box in the loop: `plan → execute → review → (memory) → loop`.
After the agent has *thought* (§1) and *acted* (§2), this box asks one pivotal
question: **"what I just did — is it correct?"** — and then decides to **close the
loop** or **go back and plan again**.

> **Continuing the SRE story.** In planning, the agent reasoned out the cause
> (deploy v2.3 shrank the DB pool) and *stopped to ask* — the SRE chose **roll
> back to v2.2**. In execution, the agent called `rollback_deployment` for real.
> **But calling the tool does not mean the incident is over.** The rollback might
> fail, the cause might have been misdiagnosed, or the 5xx might persist for
> another reason. Review is where the agent *verifies itself* before daring to
> say "fixed."

### Why review? — "fluent" is not "correct"

LLMs produce fluent, **confident** text even when wrong. The first draft is
usually *okay* but rarely *optimal*: missing steps, invented numbers, skipped edge
cases — or, like our SRE, **thinking it fixed the problem when the incident is
still burning.**

```
NO review                            WITH review
────────────                         ────────────
called tool → "Rolled back,          called tool → asks "are the 5xx really gone?"
done!" (believes itself)                         → verifies against REAL metrics
        │                                        → still failing? → go think again
        ▼                                        → clear? → only then say "fixed"
  risk: WRONG report,
  incident still on fire
```

Core idea: **the model's output must be doubted, not trusted by default.** Review
turns *"seems done"* into *"verified done."*

### The Reflection pattern — generate → critique → fix

The simplest form of review is a **self-grading loop**: the same model (or a
second one) re-reads its own output, points out flaws, and fixes them — repeating
until good enough.

```
        ┌──────────────────────────────────────────────┐
        │                                               │
        ▼                                               │ not good → fix
  ① GENERATE                                            │
  agent produces an answer / action                     │
        │                                               │
        ▼                                               │
  ② CRITIQUE  ──"any errors? anything missing? wrong?"──┘
  re-read, check against criteria
        │
        ▼  good
  ③ FINALIZE — return the scrutinized result
```

The interesting bit: **critiquing is easier than generating.** Telling a model
"write a perfect incident report" is much harder than "here's a draft report, find
3 weak spots and fix them." Splitting *generate* from *critique* gives the model
two different angles on the same problem — just like a human re-reading their own
writing spots errors they missed while writing.

> Link to §1: reasoning is the model *writing a draft before answering*.
> Reflection is the model *re-reading the draft after answering* and rewriting it.
> Same idea: **spend extra tokens/compute to buy a more-correct answer**
> (test-time compute), just applied *after* the first draft.

```
SRE agent — verification after the rollback:

  ① already called rollback_deployment(checkout-api → v2.2)   [execution]
        │
        ▼
  ② REVIEW: call the measuring tool AGAIN (grounded)
     query_metrics(service="checkout-api", metric="5xx_rate", window="5m")
        │
        ├─▶ result: 5xx = 0.1%  (back to normal < 0.5%)
        │        │
        │        ▼
        │   ✅ PASS → finalize: "Resolved. Cause: deploy v2.3 shrank the DB
        │              pool. Action: rollback to v2.2. 5xx back to 0.1% at 14:41."
        │              → record the lesson (episodic, see §4)
        │
        └─▶ result: 5xx = 6%  (STILL high)
                 │
                 ▼
            ❌ NOT PASS → do NOT report done. Back to planning:
               "rolled back but 5xx still high → the 'it's the deploy'
                hypothesis is WRONG, or there's a second cause. Re-reason
                from the new data."
```

The crux: **the agent may not take credit for itself.** It must *re-measure with
the same signal that raised the alarm* (5xx) — if that signal hasn't gone quiet,
the job isn't done, no matter how strongly the agent "believes" it fixed things.

### Who is the reviewer? — itself, another model, or hard checks

The reviewer need not be the same model. Common options, increasingly strong:

1. **Self-review** — the model re-reads its own output. Cheap, fast, catches
   careless errors; but blind to its own systematic mistakes.
2. **LLM-as-judge** — a *second* model (often stronger, or with a different
   prompt) grades the output against a rubric. An independent angle catches errors
   the generator can't see. This is the common way to *auto-grade at scale*.
3. **Deterministic checks** — **no** model: run tests, validate JSON against a
   schema, lint, compare to a metric threshold, a policy gate. Most trustworthy
   because the result is objective; prefer it for anything *machine-checkable*.

> Principle: **whatever a machine can check, don't ask the model to "feel."**
> Reserve LLM-as-judge for the *qualitative* (text quality, is the argument
> tight?); use hard checks for the *quantitative* (tests pass, 5xx < threshold,
> JSON valid).

### Closing the loop — and knowing when to STOP

Review is the hinge that sends `execute` back to `plan`. Its result has only two
exits:

```
review ──┬── PASS ──────▶ finalize → write memory → DONE
         │
         └── NOT PASS ──▶ feed "the errors found" into planning
                          → agent re-thinks, re-acts → review again
```

But this loop **must have a brake**, or the agent will fix-then-grade-then-fix
forever (or worse: repeat a wrong action on a prod system). Stopping conditions:

- **Criteria met** — review says "good" (5xx under threshold, tests green). Stop
  on *success*.
- **Budget exhausted** — too many rounds / tokens / time. Stop on *quota*.
- **No progress** — a new round isn't measurably better than the last. Stop on
  *saturation*.
- **Beyond its authority** — it keeps failing → **escalate to a human** (again an
  `AskUserQuestion` like in §1: "rollback didn't help, page tier-2 on-call?").

> Missing the brake is the classic agent bug: an endless review loop burns tokens
> and can *damage* the system further. "Knowing when to stop" matters as much as
> "knowing how to fix."

### Remember (review)

- The model's output is **fluent ≠ correct** → doubt it, review before finalizing.
- **Reflection** = generate → critique → fix; *critiquing is easier than
  generating*, so split the two roles.
- Two kinds: **self-critique** (leans on the model's own reasoning — can be
  confidently wrong) and **grounded verification** (anchored to truth:
  test/metric/tool — more trustworthy). The SRE agent must *re-measure 5xx*, not
  take its own word.
- Reviewer can be **itself / a judge model / hard checks**. Machine-checkable →
  don't make the model "feel" it.
- Review **closes the loop**: pass → finalize + write memory; not pass → back to
  planning. The loop **must have stopping conditions** (met / budget / no progress
  / escalate), or it never ends.

---

## 4 · Memory — the four kinds every agent needs

> Adapted from Martin Keen, IBM Technology, *The Four Types of Memory Every AI
> Agent Needs*.

### Why does an agent need memory?

On its own, an LLM is **stateless**: each call sees only what you put in the
context, then forgets everything. End of session — it forgets your name, what it
just did, even the lesson it learned a turn ago.

An **agent** must act across many steps, turns, and sessions. For that it needs
**memory**: hold the current context, recall what happened, know facts about the
world and about you, and know *how* to do things. Borrowing the model from
**human cognitive science**, there are four kinds — an agent needs all four.

```
                         AGENT MEMORY
                               │
        ┌──────────────────────┴───────────────────────┐
        ▼                                               ▼
  SHORT-TERM (working)                        LONG-TERM
  = working memory                    ┌──────────┬──────────┬───────────┐
  "what am I thinking right now"      ▼          ▼          ▼
                                  Episodic    Semantic   Procedural
                                 "happened"   "facts"    "how-to"
```

One line to remember: **working = RAM right now · episodic = a diary · semantic =
knowledge · procedural = skills.**

### The four types

**1 · Working memory (short-term).** Immediate memory holding the *current task's*
context: recent messages, the last tool result, the current goal. It *is* the
model's **context window** — like a computer's RAM.
- Holds: the current conversation, just-fetched data, the next step in the plan.
- Limit: the context window's token count. Full → trim or summarize.
- Lifetime: lost at end of session — *not* for long-term storage.

**2 · Episodic memory (long-term).** Records **specific events that happened**:
*what, when, with what, and the outcome.* A "diary" of past interactions.
- Used for: *case-based reasoning* — learn from a specific prior case to handle a
  similar one; few-shot examples drawn from real history.
- Stored in: conversation logs, archived "sessions," usually indexed for recall.
- Example: "last week you preferred a short tabular report" → it does that again.

**3 · Semantic memory (long-term).** A store of **generalized facts and
knowledge** — not tied to any single event. World knowledge *and* facts about the
user/domain.
- Holds: definitions, rules, facts — "Paris is the capital of France," "customer A
  is on the Enterprise plan."
- Used for: *grounding* — anchor answers in facts instead of making them up.
- Stored in: vector database (RAG), knowledge graph, knowledge base, user profile.

> Episodic vs semantic: episodic is "*what happened*," semantic is "*what is
> true*" — you know Paris is the capital of France without remembering when you
> learned it.

**4 · Procedural memory (long-term).** **"How-to" knowledge** — skills, processes,
behavioral habits the agent has mastered. Usually *not* in the data but in
**rules, the system prompt, code, or the model weights**.
- Holds: the sequence of steps to finish a task, tool-calling conventions, the
  system prompt, the agent's "rules of the game."
- Used for: executing multi-step tasks consistently.
- Stored in: system prompt, tool definitions, orchestration code, sometimes
  fine-tuned into the model.

### Quick comparison

| Type | Span | Answers | Typically stored in |
|------|------|---------|---------------------|
| **Working** | Short | "What am I doing now?" | Context window |
| **Episodic** | Long | "What happened before?" | Indexed logs / old sessions |
| **Semantic** | Long | "What is true / a fact?" | Vector DB (RAG), knowledge graph |
| **Procedural** | Long | "How do I do this task?" | System prompt, code, tools, weights |

### Write and retrieve

Long-term memory needs **both directions**, not just one:

```
EXPERIENCE → [write] → long-term store → [retrieve at the right moment]
          → inject into working memory → model uses it
```

- **Write:** after each turn, distill what's worth keeping and store it
  (episodic/semantic). Don't store everything — store the *non-trivial*, useful
  bits.
- **Retrieve:** when needed, find the **relevant** memory (e.g. similarity search
  in a vector DB) and bring it back into working memory. Since working memory is
  finite, *choosing the right thing to load* is the crux.

### Type vs Scope — two independent axes

Don't confuse "memory type" with "scope." Like MCP separates *where a server runs*
from *where it gets data*, these are **two separate axes**:

- **Type** (working / episodic / semantic / procedural) = the *content*: immediate
  context, an event that happened, a fact, or a how-to.
- **Scope** = *who/where it applies*: `session → user → agent → org`.

Any type can sit at any scope. Episodic, for example:

| Scope | What episodic at that scope means |
|-------|-----------------------------------|
| **Session** | events within just this session (forgotten when it ends) |
| **User** | a diary across **all sessions, all projects** for one person |
| **Agent / Org** | events shared across many agents / a whole team |

> Episodic is **not** bound to "within one project." A proper memory system often
> keeps episodic at the **user level, cross-session** — remembering "you hit error
> X last week" even in a different project.

### Local demo (Claude) → production (mem0)

**Claude Code alone** (files on disk) already demos all four — the **single,
local, one-person** version, perfect to *grasp the concepts*:

| Type | What Claude Code uses |
|------|------------------------|
| Working | the current session's context window (auto-summarizes when full) |
| Semantic | fact files in `memory/` + `MEMORY.md` (index) |
| Episodic | old session transcripts (`--resume`) + `feedback`/`project` files |
| Procedural | `CLAUDE.md` / `AGENTS.md` + skill `.md` + system prompt + tools |

Going to **multi-agent production**, the hand-managed-file version struggles in
three places — this is what **mem0** (and similar memory layers) exist to solve:

1. **Scope & sharing** — memory keyed by `user/session/agent/org`, many agents +
   apps **share one store**, not locked to one project directory.
2. **Smart retrieval at scale** — vector search (by meaning) + graph (by
   relationship). When memories reach the thousands, *choosing the right piece to
   load into working memory* is the problem — `grep` over files can't keep up.
3. **Auto write/merge pipeline** — automatically distills what's worth keeping,
   dedupes, and reconciles contradictions after each turn; instead of you deciding
   which file to write by hand.

> mem0 is **not** "memory in the cloud" (it self-hosts). It's a **shared, scoped,
> auto-managed memory layer with retrieval at multi-agent scale** — the same jump
> from a local file demo to a real production layer.

### Remember (memory)

- An LLM is **stateless**; an agent needs memory to act across steps/sessions.
- Four types: **working** (RAM now) · **episodic** (diary) · **semantic** (facts)
  · **procedural** (how-to).
- **Type** (content) and **scope** (session/user/agent/org) are *independent* axes.
- Long-term memory needs both **write** (distill the non-trivial) and **retrieve**
  (load the relevant bit into working memory).
- Claude Code demos all four with files; **mem0** is the production layer when you
  need scope, smart retrieval, and an auto write/merge pipeline.

---

## Putting it together — the loop, end to end

The full incident, one box at a time:

```
14:35  alert: checkout-api 5xx spike. SRE: "deal with it."

  PLAN     reason: 5xx since 14:32 → deploy v2.3 at 14:30 → logs say DB
           timeout → v2.3 shrank the pool. Cause = the deploy.
           Rollback is risky → AskUserQuestion → SRE: "roll back to v2.2"
    │
    ▼
  EXECUTE  call tool rollback_deployment(checkout-api → v2.2)   [MCP]
    │
    ▼
  REVIEW   grounded check: query_metrics(5xx, 5m) → 0.1% ✅
           (had it still been 6% → back to PLAN with the new data)
    │
    ▼
  MEMORY   episodic: "v2.3 shrank DB pool → 5xx; rollback fixed it"
           so next time this class of incident resolves faster.
```

Each box is one capability: **plan** (reason an intent into steps, pause to ask),
**execute** (call real tools via MCP), **review** (verify against truth, decide
loop-or-stop), **memory** (carry state so the agent improves instead of starting
from zero). Together they are what turns a model into an agent.

## Sources

- IBM Technology — *What Are Large Reasoning Models (LRMs)?*:
  <https://www.youtube.com/watch?v=enLbj0igyx4>
- DeepSeek-AI — *DeepSeek-R1* (2025): <https://arxiv.org/abs/2501.12948>
- Andrew Ng — *Agentic Design Patterns Part 2: Reflection* (DeepLearning.AI):
  <https://www.deeplearning.ai/the-batch/agentic-design-patterns-part-2-reflection/>
- Shinn et al. — *Reflexion* (2023): <https://arxiv.org/abs/2303.11366>
- Zheng et al. — *Judging LLM-as-a-Judge* (2023): <https://arxiv.org/abs/2306.05685>
- Martin Keen — *The Four Types of Memory Every AI Agent Needs*, IBM Technology:
  <https://www.youtube.com/watch?v=BacJ6sEhqMo>
- mem0 — *Memory Types*: <https://docs.mem0.ai/core-concepts/memory-types>

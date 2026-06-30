---
marp: true
theme: default
paginate: true
size: 16:9
header: 'Application — AgentCore: the production substrate'
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

# AgentCore

### From a local SRE script to a production agent

`Runtime → Memory → Code Interpreter → Observability → Identity/Gateway`

<!--
Welcome. This sits in layer 5 — the application layer — but it's really the
production SUBSTRATE underneath layers 04 and 05. In layer 04 we built the loop
(plan → execute → review → memory). In layer 05 we framed the membrane
(interface + integration). Today: we take the EXACT SAME SRE agent from layer 04
and ship it to production on Amazon Bedrock AgentCore, switching on one managed
capability at a time. ~90 min; interrupt anytime. Everything runs against a real
EKS cluster the agent actually operates on.
-->

---

## Agenda

1. **The production wall** — why a working script isn't a product
2. **Runtime** — the serverless heart, one microVM per session
3. **Memory** — remember incidents across sessions
4. **Tools** — Code Interpreter & Gateway: more tools without writing them
5. **Observability** — see the agent think
6. **Identity** — auth at the edge, briefly
7. **Putting it together** + Q&A

<!--
The spine: Runtime is the heart (part 2), then we add components one at a
time (3-6), then run the whole incident end to end (7). Everything maps back to
a layer-04 concept — call those connections out as we go; that's the through-line.
-->

---

<!-- _class: part -->

# 0 · The production wall

A working script is not a product.

<!--
Set the frame before any AWS detail. The point of this part: name the gap
between "it works on my laptop" and "it's in production," and show that
AgentCore is a menu of managed services that close that gap.
-->

---

## It works on your laptop. Now ship it.

You built the SRE agent in layer 04: it reasons about an incident, calls a tool,
verifies the fix. On your machine, it works.

Then you try to ship it — and hit a **wall of infrastructure**:

- run for **many users at once** without leaking one incident into another
- **remember** past incidents across sessions
- run **untrusted code** safely
- **scale** on demand, be **observable** when it misbehaves at 3 a.m.

> Building that from scratch is **months** of work. It's also not *agent* work —
> it's plumbing.

<!--
The motivating pain. Everyone who has prototyped an agent has felt this. The
laptop demo is the easy 20%; the 80% is the production plumbing. Stress: none of
that plumbing is the interesting part — it's the same for every agent.
-->

---

## AgentCore = managed production capabilities

**Amazon Bedrock AgentCore** is a set of managed services that hand you those
production capabilities, so you keep writing *agent logic*, not infrastructure.

```
        YOUR JOB                         AGENTCORE'S JOB
        ────────                         ───────────────
   agent logic (the loop)          isolation, scaling, durable memory,
   tools, prompts                  secure sandbox, auth, tracing
        │                                       │
        └──────────  one decorator  ───────────┘
                     two CLI commands
```

It's **modular** — each service stands alone or composes. Switch on what you
need; ignore the rest.

<!--
The value prop in one line: you write agent logic, AWS runs the substrate.
Modularity matters — this isn't a monolith you adopt wholesale. You can take
just Runtime, or Runtime + Memory, etc. We'll switch them on one at a time.
-->

---

## Where AgentCore sits in our stack

Each service maps almost one-to-one onto a concept we already built:

| AgentCore service | What it does |
|---|---|
| **Runtime** | serverless host, one microVM per session |
| **Memory** | short- + long-term, cross-session |
| **Code Interpreter** | secure sandbox to run real code |
| **Gateway** | turn APIs/Lambda into MCP tools |
| **Identity** | inbound + outbound auth |
| **Browser** | cloud browser the agent drives |
| **Observability** | traces of reasoning, tools, memory |

<!--
This table is the map of the whole talk — take a photo. The right column is the
point: nothing here is new conceptually. It's the layer-04 loop and the layer-05
membrane, delivered as managed services. We build the green-check ones in depth
and sketch the rest.
-->

---

<!-- _class: part -->

# 1 · Runtime

The serverless heart. Everything else is optional.

<!--
Runtime is THE core — every other component is opt-in, but nothing runs without
Runtime. Goal of this part: the mental model of "Lambda, but for stateful
agents," the one-decorator contract, and the session→microVM model that
everything else (memory scope, isolation) hangs off of.
-->

---

## "Lambda, but for stateful agents"

Runtime is a serverless host **purpose-built for agents**:

```
              AWS Lambda                  AgentCore Runtime
              ──────────                  ─────────────────
 lifetime     one invocation, gone        a SESSION: many calls, up to 8h
 state        stateless                    keeps in-memory state between calls
 isolation    per-invocation               per-session microVM (CPU/mem/fs)
 max time     15 min                       8 h
 fit          a stateless function         a multi-turn, tool-using agent
```

> A chat agent is **stateful and long-lived** — it holds a conversation. Lambda's
> stateless 15-min model doesn't fit. Runtime is the shape that does.

<!--
The anchor analogy. Lambda is the thing everyone knows; Runtime is its
agent-shaped cousin. The killer differences: it KEEPS STATE between calls within
a session, and it runs up to 8 hours. That's exactly what a multi-turn agent
needs and what Lambda can't give you.
-->

---

## Runtime facts that change how you code

- **One microVM per `sessionId`.** Each session = a dedicated Firecracker
  microVM — isolated CPU/mem/fs. On termination it's destroyed, memory wiped →
  **no cross-session leakage.** (the enterprise-security headline)
- **Long-lived but ephemeral.** Up to **8 h**, killed after **15 min idle**.
  State in the microVM is **not durable** → use **Memory** (part 3) for anything
  that must survive.
- **Framework- & model-agnostic.** LangChain, CrewAI, Strands; Claude, Nova,
  Gemini. AgentCore doesn't care.
- **Streaming, MCP, A2A** — powers the *interface* edge from layer 05.
- **Billed for active compute**, not wall-clock — an 8 h session that mostly
  waits on the model is not 8 h of billing.

<!--
Five facts, but two are load-bearing: (1) the per-session microVM is what gives
you isolation for free — the headline you sell to security; (2) "stateful but
ephemeral" is the trap — people assume the microVM is durable storage and lose
data. It is RAM, not disk. Durable = Memory, part 3.
-->

---

## The one line that makes a script deployable

The **only** difference between your local script and a cloud agent is a
decorator:

```python
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(payload, context):     # payload = request JSON; context = session info
    ...
    return {"response": "..."}     # structured output back to the caller

if __name__ == "__main__":
    app.run()
```

`@app.entrypoint` tells Runtime how to call your agent. AgentCore handles the
container, scaling, isolation, and HTTP plumbing. **That's the whole contract.**

<!--
This is the "aha" slide. Months of plumbing collapse into one decorator. Make
them really feel how small the code delta is: the agent logic is unchanged; you
wrap it in an entrypoint and AgentCore does the rest. This is the payoff of
"you write agent logic, AWS runs the substrate."
-->

---

## Who spawns the microVM? (not you)

You never spawn a VM. **AWS does**, keyed on the `sessionId` you pass:

```
your invoke (runtimeSessionId = "X")
        │
        ▼
┌──── AWS · AgentCore Runtime service ─────┐
│  is "X" live?  no → spawn a fresh microVM │   ← AWS, not your code
│                yes → route to X's microVM │
└───────────────────────────────────────────┘
        │
        ▼
  your @app.entrypoint runs INSIDE the VM AWS picked
```

The `sessionId` is a **parameter of the API call**, not state in your code:

```bash
agentcore invoke '{"prompt":"..."}' --session-id incident-checkout-5xx-0000000000
```

<!--
The control-flow mental model. The session id is the KEY: new id → AWS spawns a
VM; seen id → routes to the warm one. Your code never manages VMs — it only
chooses the id (as caller) and reads it (for memory scope). VMs are created
LAZILY on first invoke; you don't pre-create them.
-->

---

## Designing the sessionId — one session per incident

Rule: **one session = one conversation.** For an alert channel that means **one
session per incident** — not per channel (alerts bleed together), not per message
(no follow-up continuity).

```python
def on_alert(alert):
    # STABLE incident key from the alerting system's dedup/fingerprint
    incident_id = f"incident-{alert['service']}-{alert['fingerprint']}".ljust(33,"0")
    actor_id    = f"svc:{alert['service']}"          # durable identity; lessons accrue here
    client.invoke_agent_runtime(
        agentRuntimeArn=AGENT_ARN,
        runtimeSessionId=incident_id,                # new id → spawn; seen id → route
        payload=json.dumps({"prompt": alert["text"]}).encode())
```

- **New incident** → new id → AWS spawns. **Update to a live one** → reuse id →
  routes to the warm VM, context intact.
- Derive the id from the **alert fingerprint** (≥33 chars, unguessable).

<!--
This is the practical "how do I wire it to real alerts" slide. The design choice
— what maps to a session — is the whole game. Fingerprint-derived id means the
SAME ongoing incident always lands on the SAME warm VM. Per-channel would mix
unrelated incidents; per-message would lose continuity on the SRE's follow-up.
-->

---

## Incidents outlive VMs

> An SRE may reply **30 min later** — after the 15-min idle timeout already
> killed the VM.

```
14:35  alert → spawn VM (session X)  ───▶  agent investigates
14:52  (15 min idle) ────────────────────▶  VM TERMINATED, RAM wiped
15:20  SRE replies on the same incident ──▶  reuse session X
          │
          ├─ Memory OFF → fresh empty VM, context lost
          └─ Memory ON  → AgentCoreMemorySaver REPLAYS the thread → continuity
```

With Memory on, reusing the same `(session_id, actor_id)` replays the saved
thread into a fresh VM. **Without it, a timed-out session loses everything.**

<!--
This is the bridge to part 3 — it shows WHY the ephemeral microVM isn't enough.
The real world is asynchronous: humans reply on their own schedule, long after
the VM died. Memory is what makes the session survive termination. Don't fully
explain the saver here; just plant the need.
-->

---

## Runtime — remember

- Runtime = **serverless host for agents**: one **isolated microVM per session**,
  up to **8 h**, framework/model-agnostic, with streaming.
- **Stateful within a session** (unlike Lambda) but **ephemeral** — durable
  memory is a separate service.
- `@app.entrypoint` is the **only** code change from local → cloud.
- **AWS owns** the session→microVM lifecycle; the **caller picks the
  `sessionId`** (≥33 chars). One session per conversation/incident; the durable
  identity is **`actor_id`**.

<!--
30-second recap. We now have a place for the agent to RUN. Next: make what it
learns survive the microVM — Memory across sessions.
-->

---

<!-- _class: part -->

# 2 · Memory

Remember incidents across sessions.

<!--
The first add-on component. Runtime gives memory WITHIN a session (microVM holds
state up to 8h), but it dies with the session. AgentCore Memory is the durable
layer — and it maps directly onto layer 04's four memory types. This is the
managed version of the mem0 / file-based memory we discussed in orchestration.
-->

---

## Within-session is not enough

The microVM holds state up to 8 h — but the moment the session ends, or a new
incident opens next week, that context is **gone**.

```
Within-session state (microVM)  ── 04 "working memory" (RAM now), dies with VM
AgentCoreMemorySaver  (STM)     ── exact conversation history, survives restarts
AgentCoreMemoryStore  (LTM)     ── 04 "episodic": extracted facts, cross-session
```

**AgentCore Memory** is the durable layer — two LangGraph objects from
`langgraph-checkpoint-aws`:

- `AgentCoreMemorySaver` → **short-term**: persists this session's turns
- `AgentCoreMemoryStore` → **long-term**: extracts & searches cross-session facts

<!--
Map it to layer 04 explicitly: working memory = the microVM RAM (volatile); STM
= the saver (durable conversation replay — this is what made "incidents outlive
VMs" work in part 1); LTM = the store (the episodic diary, cross-session). Two
objects, that's the whole integration surface.
-->

---

## Four strategies — what gets remembered

LTM isn't one bucket. You turn on **strategies** that decide *what* to extract
from the raw conversation — and they line up with the layer-04 memory types:

| Strategy | Extracts | 04 type | SRE example |
|---|---|---|---|
| **Semantic** | generalized **facts** | semantic | "checkout-api uses a DB connection pool" |
| **Episodic** | **events** (what/when/outcome) | episodic | "14:35 v2.3 shrank pool → 5xx → rollback fixed it" |
| **User preference** | how the actor likes things | profile | "the SRE team wants a short tabular report" |
| **Summary** | condensed **session summaries** | compression | "Incident #4821: 5xx from v2.3, rolled back" |

> Each runs **extract → consolidate → reflect**, driven by system prompts — **no
> code from you.**

<!--
This is the four-memory-types slide from orchestration, now as configurable
strategies. The big idea: extraction is prompt-driven and fully managed — you
declare WHICH strategies, AWS runs the extract/consolidate/reflect pipeline. Three
control tiers exist: built-in (zero config), built-in override (edit prompts),
self-managed (your own pipeline — the only tier where you write extraction code).
-->

---

## Scoping memory — namespaces with placeholders

You mix strategies on one store; each writes to its own **namespace**.
`{actorId}`/`{sessionId}` are filled at runtime — that's how one store stays
scoped per team and per incident:

```python
memory = MemoryClient(region).create_memory_and_wait(
    name="SREAgentMemory",
    event_expiry_days=30,                                   # STM retention knob
    strategies=[
      {"semanticMemoryStrategy":   {"name":"Facts",     "namespaces":["/facts/{actorId}/"]}},
      {"userPreferenceMemoryStrategy":{"name":"Prefs",  "namespaces":["/prefs/{actorId}/"]}},
      {"summaryMemoryStrategy":    {"name":"Summaries","namespaces":["/sum/{actorId}/{sessionId}/"]}},
    ])
```

> Shared namespace = shared across the team; `{actorId}`-keyed = **isolated** per
> actor. This is **type × scope** from layer 04, made concrete.

<!--
Recall the "type vs scope are orthogonal axes" point from orchestration. Here
scope is literal: the namespace template. {actorId} → per-team-or-service;
{actorId}/{sessionId} → per-incident-within-a-team. Use MemoryClient when you
want to choose strategies/namespaces explicitly; `agentcore configure` sets up a
sensible default for you.
-->

---

## Wiring it in — identity keys at invoke time

```python
checkpointer = AgentCoreMemorySaver(MEMORY_ID, region)   # short-term
store        = AgentCoreMemoryStore(MEMORY_ID, region)   # long-term
_agent = create_react_agent(model=llm, tools=[...], prompt=SYSTEM,
    checkpointer=checkpointer,          # persists this session's turns
    store=store)                        # extracts/searches cross-session facts

@app.entrypoint
def invoke(payload, context):
    config = {"configurable": {
        "thread_id": context.session_id,   # → AgentCore session_id  (this incident)
        "actor_id":  actor_id}}            # → AgentCore actor_id     (the SRE team)
    result = _agent.invoke({"messages":[("human", payload["prompt"])]}, config=config)
    return {"response": result["messages"][-1].content}
```

> `thread_id → session_id`, `actor_id → actor_id`. The microVM is **pinned to one
> session** → build the agent **once** (lazy global) and reuse it all session.

<!--
The mapping is the whole trick: LangGraph's thread_id IS the AgentCore session;
actor_id IS the actor. Build-once: because the VM is pinned to one session, one
agent instance per container is correct — you build it lazily on first invoke
(when the ids are known) and reuse it, avoiding a rebuild per turn. This is also
why session ids must be long/unguessable — they're the key that spawns the VM.
-->

---

## Prove it — cross-session recall

```bash
# Session A: record the incident outcome
agentcore invoke '{"prompt":"Resolved: v2.3 shrank the DB pool, rolled back to v2.2."}' \
  --session-id incident-A-checkout-5xx-000000000000 --headers "Actor-Id:sre-team"
sleep 20                                              # LTM extraction is async

# Session B (NEW incident, same team): the lesson carries over
agentcore invoke '{"prompt":"checkout-api 5xx again — anything we learned before?"}' \
  --session-id incident-B-checkout-5xx-000000000000 --headers "Actor-Id:sre-team"
# → "Last time this was deploy v2.3 shrinking the DB pool; check the latest rollout first."
```

> That's the **episodic memory** payoff from layer 04 — now a managed service, not
> hand-managed files or mem0.

<!--
The demo that makes it real. Two DIFFERENT sessions (incidents), same actor
(team). The lesson written in A surfaces in B because LTM is actor-scoped, not
session-scoped. Note the async extraction — the sleep 20 is real; LTM isn't
instant. This is exactly the "case-based reasoning" value we promised in
orchestration's memory part.
-->

---

## Memory — remember

- Runtime gives memory **within** a session; **AgentCore Memory** is the
  **durable** layer (survives termination — this is what makes incidents outlive
  VMs).
- **`AgentCoreMemorySaver`** = STM (conversation replay) · **`AgentCoreMemoryStore`**
  = LTM (cross-session facts).
- **Four strategies** (semantic/episodic/preference/summary) = layer-04 memory
  types; extraction is **prompt-driven, managed**.
- **Namespaces** with `{actorId}`/`{sessionId}` = type × scope. Durable identity
  is the **actor**, not the session.

<!--
Recap. We can now run AND remember. Next: a different class of capability — not
memory, but the ability to COMPUTE reliably instead of guessing.
-->

---

<!-- _class: part -->

# 3 · Code Interpreter

Let the agent compute, not guess.

<!--
This is the layer-04 "grounded verification" idea as a managed service. LLMs are
unreliable at precise math and data analysis — they pattern-match numbers rather
than calculate. Code Interpreter gives the agent a secure sandbox to write and
run real code and read back the actual output.
-->

---

## Don't ask a model to eyeball numbers

LLMs **pattern-match numbers** instead of calculating. "5xx spiked at 14:32" by
eyeballing a timeseries is a **guess**.

```
Without Code Interpreter            With Code Interpreter
────────────────────────            ─────────────────────
model stares at numbers             model WRITES Python:
→ "looks like ~14:32" (guess)         df.diff().idxmax()  → exact changepoint
→ confident, possibly wrong           runs in sandbox → real result
                                      → "5xx step-changed at 14:32, +5.8pp"
```

**Code Interpreter** = a secure sandbox (its own Firecracker microVM, with
`numpy`/`pandas`/`matplotlib`) where the agent **writes and runs real code** and
reads the output back.

<!--
The same insight as orchestration's review box: whatever a machine can check,
don't ask the model to "feel." Computing a changepoint is a calculation, not a
vibe. The sandbox is a SEPARATE microVM from the agent's — different trust level,
which we'll stress on the next slide.
-->

---

## A generic tool — the agent writes the code

```python
@tool
def execute_python(code: str, description: str = "") -> str:
    """Run Python in a secure sandbox and return stdout. Use for metric analysis,
    statistics, correlating the 5xx timeseries with deploy timestamps."""
    with code_session(REGION) as c:                      # spins up the sandbox microVM
        resp = c.invoke("executeCode",
                        {"code": code, "language": "python", "clearContext": False})
        for event in resp["stream"]:                     # state persists across calls
            return json.dumps(event["result"])
```

Add `execute_python` to `tools=[...]`. Now the agent pulls raw metrics with
`query_metrics`, then **writes code** to find the exact changepoint and correlate
it with rollout timestamps.

> **Generic** (agent decides what code to write) vs **fixed-function**
> (`rollback_deployment` = one hard-coded action).

<!--
Two ideas. (1) Generic vs fixed tool: rollback_deployment does ONE thing; this
tool runs ARBITRARY agent-authored code — a different category. (2) Trust levels:
the sandbox is isolated and can't touch your infra — it only computes. The
rollback tool touches the live cluster. Two different trust levels, by design.
Sandbox state persists within a session (clearContext:False), so it's stateful.
-->

---

<!-- _class: part -->

# 4 · Observability

See the agent think.

<!--
Short part. `agentcore launch` wires this up automatically — an OpenTelemetry
trace of every run lands in CloudWatch. This is the review/ops view of the loop,
for free. The payoff: debugging "why did it roll back the wrong service?" in
production.
-->

---

## The whole loop, as a trace

`agentcore launch` wires up Observability automatically — OpenTelemetry traces in
CloudWatch. One incident trace shows the **entire layer-04 loop as spans**:

```
▼ Agent Invocation  (1 incident)
  ├─ Model call      reason: "5xx since 14:32, suspect a deploy"
  ├─ Tool: query_metrics        (320 ms)
  ├─ Tool: execute_python       changepoint = 14:32      (sandbox 1.1 s)
  ├─ Tool: get_rollout_history  v2.3 @ 14:30             (210 ms)
  ├─ Memory: retrieve           "v2.3 caused this before"
  ├─ Model call      decide: roll back to v2.2
  ├─ Tool: rollback_deployment  patched → v2.2           (180 ms)
  └─ Model call      verify: re-measure 5xx → 0.1% ✅
```

> Reasoning, every tool call, memory ops, code runs, model latency — **all
> there.** It's the **review/ops** view of the loop, for free.

<!--
This is how you debug an agent in production at 3am. Without traces, an agent is
a black box — "it rolled back the wrong service" with no way to see why. The
trace shows the reasoning AND every side effect with latencies. Note it's
automatic — you got it from `launch`, no extra code. Point at each span and name
the loop box it belongs to.
-->

---

<!-- _class: part -->

# 5 · Identity & Gateway

The software edge, as managed services.

<!--
Briefly — these two are the layer-05 software edge (integration) delivered as
managed services. They're optional and compose with everything above. Keep this
light; the depth was Runtime/Memory/CodeInterpreter.
-->

---

## Auth and tool catalogs

These are the layer-05 **software edge** as managed services:

- **Identity** 🔐 — **inbound auth** (who may invoke: IAM or OAuth via
  Cognito/Okta/Entra) + **outbound auth** (the agent reaching Slack/GitHub with
  managed OAuth/keys, so creds never sit in your code). The "auth at the edge"
  story from layer 05.
- **Gateway** ⭐ — turns your existing APIs/Lambda (or MCP servers) into **MCP
  tools** behind one endpoint. Instead of hand-writing the EKS tools, you'd front
  the cluster through a Gateway and let *any* MCP agent use them.

> For the SRE agent: **Identity** safely exposes it to on-call (and lets it post
> to Slack); **Gateway** scales 3 hand-written tools → a governed catalog.

<!--
Identity = the two directions of auth: who can call the agent, and how the agent
authenticates outward without you hard-coding secrets. Gateway = the API→MCP
adapter, so you don't hand-write every tool — it connects back to the MCP "write
once, reuse" story from orchestration's execution part. Both optional; mention
they exist, move on to the capstone.
-->

---

<!-- _class: part -->

# 6 · Putting it together

The same incident, on production-grade infrastructure.

<!--
The capstone. Walk the SAME incident from layer 04 once more — but now each step
is backed by a managed AgentCore service we switched on. The point: these aren't
seven products, they're the one layer-04 loop with production capabilities
underneath.
-->

---

## One incident, every component

```
14:35  PagerDuty → invoke_agent_runtime(session = this incident)   [Runtime: own microVM]
  │
  ├─ retrieve "v2.3 caused this before"                            [Memory: episodic, x-session]
  ├─ query_metrics + execute_python → 5xx step-changed at 14:32    [Code Interpreter: real compute]
  ├─ get_rollout_history → v2.3 @ 14:30 is the suspect             [tool on real EKS]
  ├─ rollback_deployment → v2.2                                    [tool on real EKS]
  └─ re-measure 5xx → 0.1% ✅, write the lesson to memory           [review + Memory write]

every step traced in CloudWatch                                    [Observability]
```

> You wrote **agent logic**; isolation, memory, sandbox, scaling, auth, and
> tracing came as **managed services** — switched on one at a time.

<!--
The whole talk in one slide. Trace each annotation back to its part. The contrast
with part 0's "production wall" is the close: that wall of months-of-plumbing is
now a menu you switch on. You kept writing the agent; AWS ran the substrate.
-->

---

## Takeaways

1. A working script ≠ a product — the gap is **isolation, memory, sandbox,
   scaling, auth, tracing.** AgentCore hands you those as **managed services.**
2. **Runtime** is the core: serverless, **one isolated microVM per session**, 8 h;
   `@app.entrypoint` is the only code change. Durable identity is **`actor_id`**.
3. **Memory** = STM (saver) + cross-session LTM (store); four strategies =
   layer-04 memory types; `thread_id→session_id`, `actor_id→actor_id`.
4. **Code Interpreter** = secure sandbox so the agent **computes, not guesses** —
   a generic tool, distinct from fixed ones.
5. **Observability** = the whole loop as CloudWatch traces, automatically.
6. **Identity + Gateway** = the layer-05 software edge (auth + API→MCP).
7. The pattern: **build agent logic, switch on production capabilities** — keep
   what you need, ignore the rest.

<!--
Seven lines to leave them with. If short on time, the must-keep slides are: the
production wall, the AgentCore service map, Lambda-vs-Runtime, the one-decorator
contract, the four memory strategies, compute-not-guess, and the capstone. The
unifying message: it's the same layer-04 loop, with the months of production
plumbing switched on a component at a time.
-->

---

<!-- _class: lead -->
<!-- _paginate: false -->

# Thank you

Questions?

*Full notes, code & sources: this folder's `README.md`*

<!--
Likely questions: "do I have to use LangChain?" (no — framework-agnostic; Strands,
CrewAI, custom all work); "is the microVM durable storage?" (no — it's RAM; use
Memory for anything that must survive); "how is this different from just Lambda?"
(stateful sessions up to 8h + per-session isolation + agent-native protocols);
"do I need all the components?" (no — Runtime is the only required piece, the rest
are opt-in); "what about cost?" (active-compute billing, not wall-clock — idle
sessions are largely free).
-->

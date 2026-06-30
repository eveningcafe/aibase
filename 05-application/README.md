# AgentCore — from a local SRE script to a production agent

You've built the SRE agent from layer 04. On your laptop it works: it reasons
about an incident, calls a tool, verifies the fix. Then you try to ship it and
hit a **wall of infrastructure**: it needs to run for many users at once without
leaking one incident's data into another, remember past incidents across
sessions, run untrusted code safely, scale on demand, and be observable when it
misbehaves at 3 a.m. Building that from scratch is months of work.

**Amazon Bedrock AgentCore** is a set of managed services that hand you those
production capabilities so you keep writing *agent logic*, not infrastructure.
This lecture takes the **same SRE agent** and ships it to AgentCore, then adds
its components one at a time — each on a real Amazon **EKS** cluster the agent
actually operates on.

> Companion to layers 04 and 05. Layer 04 built the **loop** (plan → execute →
> review → memory). Layer 05 framed the **membrane** (interface + integration).
> AgentCore is the **production substrate underneath both**. Where the loop runs,
> where memory lives, how the agent authenticates to your tools — that's this.

## Where AgentCore sits in our stack

AgentCore is modular: each service stands alone or composes with the others. The
services map almost one-to-one onto concepts we already built:

| AgentCore service | What it does | Our course concept |
|---|---|---|
| **Runtime** ✅ | serverless hosting for the agent, one isolated microVM per session | 04 — where the loop runs |
| **Memory** 📚 | short-term + long-term memory, cross-session | 04 — the four memory types / mem0's role |
| **Code Interpreter** 🐍 | secure sandbox to write & run real code | 04 — grounded verification (compute, don't guess) |
| **Gateway** ⭐ | turn APIs/Lambda into MCP tools | 04 execution / 05 integration |
| **Identity** 🔐 | inbound + outbound auth for the agent | 05 — auth at the edge |
| **Browser** 🌐 | cloud browser the agent can drive | 05 — a software-edge tool |
| **Observability** 📊 | traces of reasoning, tools, memory, model calls | 04 review / ops |

This lecture builds **Runtime → Memory → Code Interpreter → Observability**, then
sketches Identity and Gateway. We'll use **LangChain/LangGraph** (any framework
works), plain **`venv` + `pip`** (no `uv`), and **Claude on Bedrock**.

---


## 1 · The serverless Runtime — the core idea

Everything else is optional; **Runtime is the heart.** It is a serverless host
purpose-built for agents. Think "AWS Lambda, but for stateful agents":

```
              AWS Lambda                    AgentCore Runtime
              ──────────                    ─────────────────
 lifetime     one invocation, then gone     a SESSION: many invocations, up to 8h
 state        stateless                      keeps in-memory state between calls
 isolation    per-invocation                 per-session microVM (CPU/mem/fs isolated)
 max time     15 min                         8 h
 fit          a stateless function           a multi-turn, tool-using agent
```

Key Runtime facts (the ones that change how you write code):

- **One microVM per `sessionId`.** Each user session gets a dedicated Firecracker
  microVM — isolated CPU, memory, filesystem. On termination the microVM is
  destroyed and memory wiped → **no cross-session leakage**. This is the
  enterprise-security headline.
- **Sessions are long-lived but ephemeral.** Up to **8 h**, terminated after
  **15 min idle**. State held in the microVM is *not durable* — for anything that
  must survive the session, use **AgentCore Memory** (§3).
- **Framework- and model-agnostic.** LangChain, LangGraph, CrewAI, Strands,
  custom code; Claude, Nova, Gemini, OpenAI. AgentCore doesn't care.
- **Protocols & streaming.** HTTP, MCP, A2A; streaming and WebSocket for
  realtime — this is what powers the *interface* edge from layer 05.
- **Billing is active-consumption**, not wall-clock: you're billed for CPU while
  actually processing (idle/I/O wait is largely free), plus memory. A session
  *open* for 8 h that mostly waits on the model is not 8 h of compute.

### The one line that makes a script deployable

The **only** difference between your local agent script and a cloud-deployed one
is a decorator:

```python
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(payload, context):     # payload = the request JSON; context = session info
    ...
    return {"response": "..."}     # structured output back to the caller

if __name__ == "__main__":
    app.run()
```

`@app.entrypoint` tells Runtime how to call your agent. AgentCore handles the
container, scaling, isolation, and the HTTP plumbing. That's the whole contract.

### Sessions — who spawns them, and how to design the id

You never spawn a microVM. **AWS does**, keyed on the `sessionId` you pass to the
invoke call. Your code only *chooses* the id (as caller) and *reads* it (for
memory scoping) — it never manages VMs.

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

The sessionId is a **parameter of the API call**, not state in your code:

```bash
agentcore invoke '{"prompt":"..."}' --session-id incident-checkout-5xx-000000000000000
```
```python
client.invoke_agent_runtime(
    agentRuntimeArn=AGENT_ARN,
    runtimeSessionId="incident-checkout-5xx-000000000000000",   # ≥ 33 chars, unguessable
    payload=b'{"prompt":"..."}')
```

**Three IDs, three jobs** — don't conflate them:

| ID | Job | Lifetime |
|----|-----|----------|
| `session_id` (LangGraph `thread_id`) | one conversation → one microVM | ephemeral (15 min idle / 8 h) |
| `actor_id` | the identity (user / team / service) | durable — long-term memory scopes here |
| `memory_id` | the Memory store resource | durable |

**Designing the sessionId — an alert channel.** The rule is *one session = one
conversation*. For a Telegram/Slack channel full of alerts that means **one
session per incident** — not per channel (all alerts bleed into one context) and
not per message (no follow-up continuity):

```python
import json

def on_alert(alert):
    # derive a STABLE incident key from the alerting system's dedup/fingerprint
    incident_id = f"incident-{alert['service']}-{alert['fingerprint']}".ljust(33, "0")
    actor_id    = f"svc:{alert['service']}"          # durable identity; lessons accrue here

    client.invoke_agent_runtime(
        agentRuntimeArn=AGENT_ARN,
        runtimeSessionId=incident_id,                # new id → AWS spawns; seen id → routes
        payload=json.dumps({"prompt": alert["text"]}).encode())
    # post the agent's reply back to the same Telegram topic/thread
```

- **New incident** → new id → AWS spawns a VM. **Update to a live incident** →
  reuse the id → routes to the warm VM with context intact.
- You **don't pre-create** sessions — they're created lazily on first invoke.
- Derive the id from the **alert fingerprint** (or the Telegram topic/thread id),
  so the same ongoing incident always maps to the same session.

> **Incidents outlive VMs.** An SRE may reply 30 min later, after the 15-min idle
> timeout already killed the VM. With Memory on, reusing the same
> `(session_id, actor_id)` makes `AgentCoreMemorySaver` **replay the saved
> thread** into a fresh VM — continuity survives termination. Without Memory, a
> timed-out session loses its context.

### Remember (Runtime)

- Runtime = **serverless host for agents**: one **isolated microVM per session**,
  up to **8 h**, framework/model-agnostic, with streaming.
- It's **stateful within a session** (unlike Lambda) but **ephemeral** —
  durable memory is a separate service.
- `@app.entrypoint` is the **only** code change from local → cloud.
- **AWS owns the session→microVM lifecycle**; the **caller picks the
  `sessionId`** (≥33 chars). Design it as **one session per
  conversation/incident** — the durable identity is **`actor_id`**, not the
  session.

---

## 2 · Get started — deploy the SRE agent

We'll deploy the layer-04 SRE agent so it operates a real `checkout-api`
Deployment on EKS: read metrics, inspect rollout history, and roll back.

### 2.1 Prerequisites

```bash
# 1) AWS account with Bedrock model access:
#    Console → Amazon Bedrock → Model access → enable a Claude Sonnet model.
# 2) AWS CLI configured:
aws configure                      # access key, secret, region (e.g. us-west-2)

# 3) Tooling: eksctl + kubectl (for the cluster), Docker (AgentCore builds a container)
```

### 2.2 Create the EKS cluster and a rollback-able service

```bash
# ~15 min to provision
eksctl create cluster --name sre-demo --region us-west-2 \
  --nodes 2 --node-type t3.medium

# Enable CloudWatch Container Insights so the agent can read real metrics
aws eks create-addon --cluster-name sre-demo \
  --addon-name amazon-cloudwatch-observability --region us-west-2
```

Deploy `checkout-api` with a **good** image (`v2.2`) we can roll back *to*, then
ship the **bad** `v2.3` to create the incident. (Any image works; we use a
trivial HTTP echo and simulate the 5xx via metrics.)

```yaml
# checkout-api.yaml — v2.2 (healthy baseline)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: checkout-api
  labels: { app: checkout-api }
  annotations: { kubernetes.io/change-cause: "v2.2 baseline" }
spec:
  replicas: 3
  revisionHistoryLimit: 10           # keep history so rollback has targets
  selector: { matchLabels: { app: checkout-api } }
  template:
    metadata: { labels: { app: checkout-api } }
    spec:
      containers:
        - name: app
          image: hashicorp/http-echo:1.0          # v2.2 "good"
          args: ["-text=checkout-api v2.2 ok"]
          ports: [{ containerPort: 5678 }]
```

```bash
kubectl apply -f checkout-api.yaml
kubectl rollout status deployment/checkout-api

# ship the bad deploy that "shrinks the DB pool" → the 14:35 incident
kubectl set image deployment/checkout-api app=hashicorp/http-echo:1.1 \
  --record
kubectl annotate deployment/checkout-api \
  kubernetes.io/change-cause="v2.3 shrink DB pool" --overwrite
```

### 2.3 Project layout (venv, two folders)

Keep **dev tools** (the starter toolkit) separate from the **agent's runtime
deps** (what gets baked into the container — keeps it lean):

```bash
mkdir agentcore-sre && cd agentcore-sre
python3 -m venv .venv && source .venv/bin/activate
pip install bedrock-agentcore-starter-toolkit       # dev tool: the CLI

mkdir agent                                          # the deployable agent lives here
```

```text
# agent/requirements.txt  ← baked into the container
bedrock-agentcore
langchain
langchain-aws
langgraph
langgraph-checkpoint-aws
kubernetes
boto3
```

### 2.4 The agent (`agent/sre_agent.py`)

LangGraph ReAct agent + three EKS tools, wrapped in the AgentCore entrypoint.
This is the layer-04 SRE agent — just with real `kubectl`-equivalent tools.

```python
"""SRE agent on AgentCore Runtime — operates checkout-api on EKS."""
import base64, datetime, os, tempfile
import boto3
from botocore.signers import RequestSigner
from kubernetes import client as k8s
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

REGION   = os.getenv("AWS_REGION", "us-west-2")
CLUSTER  = os.getenv("EKS_CLUSTER", "sre-demo")
MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"   # swap for any enabled Claude
NS       = "default"

# --- connect to EKS from inside the Runtime microVM -------------------------
# Boilerplate: presign an STS token EKS accepts as a bearer token.
def _apps_api() -> k8s.AppsV1Api:
    eks = boto3.client("eks", region_name=REGION)
    c   = eks.describe_cluster(name=CLUSTER)["cluster"]
    sess   = boto3.session.Session()
    signer = RequestSigner(sess.client("sts", region_name=REGION).meta.service_model.service_id,
                           REGION, "sts", "v4", sess.get_credentials(), sess.events)
    url = signer.generate_presigned_url(
        {"method": "GET",
         "url": f"https://sts.{REGION}.amazonaws.com/?Action=GetCallerIdentity&Version=2011-06-15",
         "body": {}, "headers": {"x-k8s-aws-id": CLUSTER}, "context": {}},
        region_name=REGION, expires_in=60, operation_name="")
    token = "k8s-aws-v1." + base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
    ca = tempfile.NamedTemporaryFile(delete=False)
    ca.write(base64.b64decode(c["certificateAuthority"]["data"])); ca.flush()
    cfg = k8s.Configuration()
    cfg.host = c["endpoint"]; cfg.ssl_ca_cert = ca.name
    cfg.api_key = {"authorization": "Bearer " + token}
    return k8s.AppsV1Api(k8s.ApiClient(cfg))

# --- the SRE tools (the agent's "execution" capabilities) -------------------
@tool
def query_metrics(metric: str = "5xx_rate", window_min: int = 15) -> str:
    """Return recent datapoints for a checkout-api metric (e.g. 5xx_rate, p99_latency)."""
    cw = boto3.client("cloudwatch", region_name=REGION)
    end = datetime.datetime.utcnow(); start = end - datetime.timedelta(minutes=window_min)
    r = cw.get_metric_data(
        StartTime=start, EndTime=end,
        MetricDataQueries=[{"Id": "m", "MetricStat": {
            "Metric": {"Namespace": "ContainerInsights",
                       "MetricName": "pod_number_of_container_restarts",
                       "Dimensions": [{"Name": "PodName", "Value": "checkout-api"}]},
            "Period": 60, "Stat": "Sum"}}])
    pts = list(zip(r["MetricDataResults"][0]["Timestamps"],
                   r["MetricDataResults"][0]["Values"]))
    return str(sorted(pts))

@tool
def get_rollout_history(service: str = "checkout-api") -> str:
    """List recent ReplicaSets (revisions) of the deployment with image + timestamp."""
    rss = _apps_api().list_namespaced_replica_set(
        NS, label_selector=f"app={service}").items
    return "\n".join(
        f"{rs.metadata.creation_timestamp}  rev={rs.metadata.annotations.get('deployment.kubernetes.io/revision')}  "
        f"image={rs.spec.template.spec.containers[0].image}  "
        f"cause={rs.metadata.annotations.get('kubernetes.io/change-cause','')}"
        for rs in sorted(rss, key=lambda r: r.metadata.creation_timestamp))

@tool
def rollback_deployment(service: str = "checkout-api", to_image: str = "hashicorp/http-echo:1.0") -> str:
    """Roll a deployment back to a known-good image. RISKY — affects live traffic."""
    _apps_api().patch_namespaced_deployment(service, NS, {"spec": {"template": {"spec": {
        "containers": [{"name": "app", "image": to_image}]}}}})
    return f"Patched {service} → {to_image}. Re-verify 5xx before declaring resolved."

SYSTEM = ("You are an SRE on-call agent for checkout-api on EKS. Investigate the "
          "5xx incident: read metrics, inspect rollout history to find the suspect "
          "deploy, and roll back to the last good image. After acting, RE-MEASURE "
          "5xx and only then report resolved. Never claim a fix you didn't verify.")

# --- the AgentCore Runtime entrypoint ---------------------------------------
_agent = None
def _build():
    global _agent
    if _agent is None:
        llm = init_chat_model(MODEL_ID, model_provider="bedrock_converse", region_name=REGION)
        _agent = create_react_agent(
            model=llm,
            tools=[query_metrics, get_rollout_history, rollback_deployment],
            prompt=SYSTEM)
    return _agent

@app.entrypoint
def invoke(payload, context):
    msg = payload.get("prompt", "checkout-api is throwing 5xx, deal with it.")
    result = _build().invoke({"messages": [("human", msg)]})
    return {"response": result["messages"][-1].content}

if __name__ == "__main__":
    app.run()
```

> Note the layer-04 ideas surfacing as real code: the **tools** are the
> *execution* box, the system prompt's "re-measure 5xx before reporting" is the
> *review* box, and the agent's reasoning over `get_rollout_history` is *planning*.

### 2.5 Configure, deploy, invoke

```bash
# from agentcore-sre/ with .venv active
agentcore configure -e agent/sre_agent.py     # point it at agent/requirements.txt; accept defaults
agentcore launch                               # builds container → ECR → creates Runtime + DEFAULT endpoint
agentcore status                               # ARN, endpoint, observability dashboard URL
```

**One real-EKS wrinkle:** `agentcore launch` creates the Runtime's IAM
*execution role*. EKS must trust that role, so grant it cluster access **after**
the first launch:

```bash
ROLE_ARN=$(agentcore status --json | python -c "import sys,json;print(json.load(sys.stdin)['execution_role'])")
aws eks create-access-entry --cluster-name sre-demo --region us-west-2 \
  --principal-arn "$ROLE_ARN"
aws eks associate-access-policy --cluster-name sre-demo --region us-west-2 \
  --principal-arn "$ROLE_ARN" \
  --policy-arn arn:aws:eks::aws:cluster-access-policy/AmazonEKSEditPolicy \
  --access-scope type=namespace,namespaces=default
```

Now fire the incident:

```bash
agentcore invoke '{"prompt": "checkout-api is throwing 5xx, deal with it."}' \
  --session-id sre-incident-2026-06-30-checkout-5xx-0001
```

The agent reads metrics, finds `v2.3` in the rollout history, rolls back to the
`v2.2` image on the **real cluster**, then re-measures. **What just happened:**
you deployed a stateful, tool-using agent to a serverless, isolated, observable
runtime — with one decorator and two CLI commands.

---

## 3 · Add the components, one at a time

### 3.1 Memory 📚 — remember incidents across sessions

Runtime already gives you memory *within* a session (the microVM holds state up
to 8 h). But the moment the session ends — or a different incident opens next
week — that context is gone. **AgentCore Memory** is the durable layer. It maps
straight onto layer 04's memory types:

```
Within-session state (microVM)  ── 04 "working memory" (RAM now)
AgentCoreMemorySaver  (STM)     ── exact conversation history, survives restarts
AgentCoreMemoryStore  (LTM)     ── 04 "episodic": extracted incident facts, cross-session
```

#### What Memory can remember — the four strategies

LTM isn't one bucket. You turn on **strategies** that decide *what* gets
extracted from the raw conversation. Four are built in, and they line up with the
layer-04 memory types:

| Strategy | Extracts | 04 type | SRE example |
|---|---|---|---|
| **Semantic** | generalized **facts** | semantic | "checkout-api uses a DB connection pool" |
| **Episodic** | **events** (what / when / outcome) | episodic | "14:35 v2.3 shrank the pool → 5xx → rollback fixed it" |
| **User preference** | how the actor likes things | (profile) | "the SRE team wants a short tabular report" |
| **Summary** | condensed **session summaries** | (compression) | "Incident #4821: 5xx from v2.3, rolled back to v2.2" |

Each strategy runs **extract → consolidate → reflect**, all driven by system
prompts (no code from you). Three control tiers: **built-in** (fully managed,
zero config), **built-in override** (edit the prompts, AWS still runs the
pipeline), **self-managed** (your own extraction/consolidation pipeline — the
only tier where you write code).

You can mix strategies on one store; each writes to its own namespace, and the
`{actorId}`/`{sessionId}` placeholders are filled at runtime — that's how one
store stays scoped per team and per incident (shared namespace = shared;
`{actorId}`-keyed = isolated):

```python
from bedrock_agentcore.memory import MemoryClient

memory = MemoryClient(region_name=REGION).create_memory_and_wait(
    name="SREAgentMemory",
    event_expiry_days=30,                       # STM retention — a lifecycle knob you control
    strategies=[
        {"semanticMemoryStrategy":       {"name": "Facts",       "namespaces": ["/facts/{actorId}/"]}},
        {"userPreferenceMemoryStrategy": {"name": "Preferences", "namespaces": ["/preferences/{actorId}/"]}},
        {"summaryMemoryStrategy":        {"name": "Summaries",   "namespaces": ["/summaries/{actorId}/{sessionId}/"]}},
        # Episodic is also built-in — add it the same way for past-incident recall
    ],
)
# memory["id"]  → set this as BEDROCK_AGENTCORE_MEMORY_ID for the agent below
```

> `agentcore configure` sets up a default memory for you (the prompt-driven path
> in §2.5). Use `MemoryClient` when you want to **choose specific strategies and
> namespaces** rather than accept the defaults.

The LangGraph integration is two objects from `langgraph-checkpoint-aws`:

```python
from langgraph_checkpoint_aws import AgentCoreMemorySaver, AgentCoreMemoryStore

MEMORY_ID = os.getenv("BEDROCK_AGENTCORE_MEMORY_ID")

checkpointer = AgentCoreMemorySaver(MEMORY_ID, region_name=REGION)   # short-term
store        = AgentCoreMemoryStore(MEMORY_ID, region_name=REGION)   # long-term

_agent = create_react_agent(
    model=llm, tools=[...], prompt=SYSTEM,
    checkpointer=checkpointer,      # persists this session's turns
    store=store)                    # extracts/searches cross-session facts
```

At invoke time, LangGraph's config carries the identity keys — and they map
directly onto AgentCore's session model:

```python
@app.entrypoint
def invoke(payload, context):
    actor_id = (context.request_headers or {}).get(
        "X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-Id", "sre-team")
    config = {"configurable": {
        "thread_id": context.session_id,   # → AgentCore session_id  (this incident)
        "actor_id": actor_id}}             # → AgentCore actor_id     (the SRE team)
    result = _build().invoke({"messages": [("human", payload["prompt"])]}, config=config)
    return {"response": result["messages"][-1].content}
```

> **Why a global `_agent` (lazy build)?** The microVM is **pinned to one
> session**, so one agent instance per container is correct and safe. You build
> it once on the first invoke (when `session_id`/`actor_id` are finally known)
> and reuse it for the rest of the session — avoiding a rebuild per turn. This is
> why session IDs must be long/unguessable: they're the **key that spawns the
> dedicated microVM** and scopes memory.

Deploy with memory, then prove cross-session recall:

```bash
agentcore configure -e agent/sre_agent.py     # answer "yes" to long-term memory extraction
agentcore launch
agentcore status                               # wait for  Memory: STM+LTM  (green/ACTIVE)

# Session A: record the incident outcome
agentcore invoke '{"prompt":"Resolved: v2.3 shrank the DB pool, rolled back to v2.2."}' \
  --session-id incident-A-checkout-5xx-000000000000 --headers "Actor-Id:sre-team"
sleep 20                                        # LTM extraction is async

# Session B (new incident, same team): the lesson carries over
agentcore invoke '{"prompt":"checkout-api 5xx again — anything we learned before?"}' \
  --session-id incident-B-checkout-5xx-000000000000 --headers "Actor-Id:sre-team"
# → "Last time this was deploy v2.3 shrinking the DB pool; check the latest rollout first."
```

That cross-session recall is exactly the **episodic memory** payoff from layer
04 — now a managed service instead of hand-managed files or mem0.

### 3.2 Code Interpreter 🐍 — let the agent compute, not guess

This is the component you asked about. **LLMs are unreliable at precise math and
data analysis** — they pattern-match numbers instead of calculating. Asking the
model to eyeball a metrics timeseries and declare "5xx spiked at 14:32" is a
guess. **Code Interpreter** gives the agent a **secure sandbox to write and run
real code** (its own Firecracker microVM, with `numpy`/`pandas`/`matplotlib`
preinstalled) and read back the actual output.

```
Without Code Interpreter            With Code Interpreter
────────────────────────            ─────────────────────
model stares at numbers             model WRITES Python:
→ "looks like ~14:32" (guess)         df.diff().idxmax()  → exact changepoint
→ confident, possibly wrong           runs in sandbox → real result
                                      → "5xx step-changed at 14:32, +5.8pp"
```

It's a **generic tool** — the agent decides *what code to write at runtime* —
which is different from a fixed-function tool like `rollback_deployment` (one
hard-coded action). It's the same insight as layer 04's review box: *whatever a
machine can check, don't ask the model to "feel."*

The framework-agnostic wiring is the `code_session` client wrapped as a tool —
no extra package beyond `bedrock-agentcore`:

```python
import json
from bedrock_agentcore.tools.code_interpreter_client import code_session
from langchain_core.tools import tool

@tool
def execute_python(code: str, description: str = "") -> str:
    """Run Python in a secure sandbox and return stdout. Use for metric analysis,
    statistics, and correlating the 5xx timeseries with deploy timestamps."""
    with code_session(REGION) as c:                       # spins up the sandbox microVM
        resp = c.invoke("executeCode",
                        {"code": code, "language": "python", "clearContext": False})
        for event in resp["stream"]:                      # state persists across calls in a session
            return json.dumps(event["result"])
```

Add `execute_python` to the agent's `tools=[...]`. Now the SRE agent can pull raw
metrics with `query_metrics`, then **write code** to find the exact 5xx
changepoint and correlate it with the `get_rollout_history` timestamps —
grounding the RCA in computation rather than a hunch.

```bash
agentcore configure -e agent/sre_agent.py && agentcore launch
agentcore invoke '{"prompt":"Pull the last 15m of 5xx, compute the exact minute it step-changed, and correlate with the rollout history. Show the numbers."}' \
  --session-id incident-C-checkout-5xx-000000000000 --headers "Actor-Id:sre-team"
```

> Sandbox = **isolated** (separate microVM, can't touch your infra), **stateful
> within a session** (define a variable in one call, use it in the next), and
> **auto-cleaned**. The agent's `rollback_deployment` touches the cluster; the
> Code Interpreter only computes — two different trust levels, by design.

### 3.3 Observability 📊 — see the agent think

`agentcore launch` wires up **Observability** automatically: an OpenTelemetry
trace of every run lands in CloudWatch. Open the dashboard:

```bash
agentcore status     # → "GenAI Observability Dashboard" URL
```

A single incident trace shows the whole layer-04 loop as spans:

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

This is how you debug "why did it roll back the wrong service?" in production:
the reasoning, every tool call, memory ops, code execution, and model latency are
all there. It's the **review/ops** view of the loop, for free.

---

## 4 · Identity 🔐 and Gateway ⭐ — the integration edge (briefly)

These two are the layer-05 **software edge** as managed services:

- **Identity** — **inbound auth** (who may invoke the agent: IAM or OAuth via
  Cognito/Okta/Entra) and **outbound auth** (the agent reaching Slack/GitHub with
  managed OAuth/API keys, so creds never sit in your code). This is exactly the
  "auth at the edge" and "outbound to your tools" story from the layer-05 README.
- **Gateway** — turns your existing APIs/Lambda functions (or pre-existing MCP
  servers) into **MCP tools** with a few lines, behind one endpoint. Instead of
  hand-writing the EKS tools above, you could front the cluster operations
  through a Gateway and let *any* MCP agent use them.

Both are optional and compose with everything above. For the SRE agent, Identity
is what lets you safely expose it to the on-call team (and let it post to Slack);
Gateway is how you'd scale from three hand-written tools to a governed catalog.

---

## 5 · Cleanup

```bash
agentcore destroy                                  # Runtime, Memory, ECR, auto-created IAM, logs
eksctl delete cluster --name sre-demo --region us-west-2
```

---

## Putting it together

The same incident from layer 04, now running on production-grade managed
infrastructure — each capability a separate AgentCore service you switched on:

```
14:35  PagerDuty → invoke_agent_runtime(session = this incident)   [Runtime: own microVM]
  │
  ├─ retrieve "v2.3 caused this before"                            [Memory: episodic, cross-session]
  ├─ query_metrics + execute_python → 5xx step-changed at 14:32    [Code Interpreter: real compute]
  ├─ get_rollout_history → v2.3 @ 14:30 is the suspect             [tool on real EKS]
  ├─ rollback_deployment → v2.2                                    [tool on real EKS]
  └─ re-measure 5xx → 0.1% ✅, write the lesson to memory           [review + Memory write]

every step traced in CloudWatch                                    [Observability]
```

You wrote *agent logic* (one LangGraph agent + a few tools) and got isolation,
durable memory, a secure code sandbox, scaling, auth, and tracing as **managed
services** — the months of "production wall" infrastructure, switched on a
component at a time.

### Remember (AgentCore)

- **Runtime** is the core: serverless, **one isolated microVM per session**,
  8 h, framework/model-agnostic; `@app.entrypoint` is the only code change.
- **Memory** = durable STM (`AgentCoreMemorySaver`) + cross-session LTM
  (`AgentCoreMemoryStore`); `thread_id→session_id`, `actor_id→actor_id`. It's the
  managed version of layer 04's memory types.
- **Code Interpreter** = a **secure sandbox** so the agent **computes instead of
  guessing** — a generic write-and-run-code tool, distinct from fixed tools.
- **Observability** is automatic: the whole loop as CloudWatch traces.
- **Identity + Gateway** are the layer-05 software edge as services (auth +
  API-to-MCP).
- The pattern: **build agent logic, switch on production capabilities** — keep
  what you need, ignore the rest.

## Sources

- AWS — *Amazon Bedrock AgentCore overview* (services):
  <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html>
- AWS — *AgentCore Runtime, how it works* (sessions, microVM, protocols):
  <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-how-it-works.html>
- AWS — *Integrate AgentCore Memory with LangChain/LangGraph*:
  <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-integrate-lang.html>
- AWS — *Run code in Code Interpreter from Agents* (the `code_session` pattern):
  <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-building-agents.html>
- AWS Builder — *Turn your AI script into a production-ready agent* (the tutorial
  this lecture adapts from Strands/uv to LangChain/venv):
  <https://builder.aws.com/content/33duot88gLusLRgJkalulTJLUrx/turn-your-ai-script-into-a-production-ready-agent>
- `langgraph-checkpoint-aws` (PyPI): <https://pypi.org/project/langgraph-checkpoint-aws/>

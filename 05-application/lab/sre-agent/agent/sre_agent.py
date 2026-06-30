"""SRE agent on Amazon Bedrock AgentCore Runtime.

Operates a real `checkout-api` Deployment on EKS: reads its health signal,
inspects rollout history, and rolls a bad deploy back to a known-good image.

The LLM is **OpenRouter** (OpenAI-compatible API), keyed by OPENROUTER_API_KEY —
we use it instead of Bedrock because the org SCP `p-vhwtjx73` denies the AWS
Marketplace actions Bedrock's model-access flow needs, so on-demand Claude can't
be enabled in this account. The *tools* still authenticate with pure IAM — the
Runtime execution role is the identity for EKS, CloudWatch, and code-interpreter.

Env (all have lab defaults):
  AWS_REGION                 ap-southeast-1   (for EKS / CloudWatch / code-interpreter)
  EKS_CLUSTER                devops-class-eks
  CHECKOUT_NAMESPACE         default
  CHECKOUT_GOOD_IMAGE        nginx:1.27-alpine        (rollback target)
  OPENROUTER_API_KEY         OpenRouter key (defaults to the lab key below)
  MODEL_ID                   google/gemma-4-31b-it:free
  BEDROCK_AGENTCORE_MEMORY_ID  (optional) → enables cross-session memory
"""
import base64
import json
import os
import tempfile

import boto3
from botocore.signers import RequestSigner
from kubernetes import client as k8s
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.tools.code_interpreter_client import code_session

app = BedrockAgentCoreApp()

REGION     = os.getenv("AWS_REGION", "ap-southeast-1")
CLUSTER    = os.getenv("EKS_CLUSTER", "devops-class-eks")
NS         = os.getenv("CHECKOUT_NAMESPACE", "default")
GOOD_IMAGE = os.getenv("CHECKOUT_GOOD_IMAGE", "nginx:1.27-alpine")
MEMORY_ID  = os.getenv("BEDROCK_AGENTCORE_MEMORY_ID")
SERVICE    = "checkout-api"
CONTAINER  = "app"

# LLM via OpenRouter (OpenAI-compatible). Not IAM — a plain API key.
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY  = os.getenv(
    "OPENROUTER_API_KEY",
    "sk-or-REPLACE-ME",   # set via env; do not commit real keys
)
MODEL_ID = os.getenv("MODEL_ID", "google/gemma-4-31b-it:free")


# --------------------------------------------------------------------------
# Connect to EKS from inside the Runtime microVM.
# Boilerplate: presign an STS GetCallerIdentity URL → EKS bearer token.
# Uses the Runtime execution role's credentials (the IAM "service account").
# --------------------------------------------------------------------------
def _kube_config() -> k8s.Configuration:
    eks = boto3.client("eks", region_name=REGION)
    c = eks.describe_cluster(name=CLUSTER)["cluster"]

    sess = boto3.session.Session()
    signer = RequestSigner(
        sess.client("sts", region_name=REGION).meta.service_model.service_id,
        REGION, "sts", "v4", sess.get_credentials(), sess.events,
    )
    presigned = signer.generate_presigned_url(
        {
            "method": "GET",
            "url": f"https://sts.{REGION}.amazonaws.com/?Action=GetCallerIdentity&Version=2011-06-15",
            "body": {},
            "headers": {"x-k8s-aws-id": CLUSTER},
            "context": {},
        },
        region_name=REGION, expires_in=60, operation_name="",
    )
    token = "k8s-aws-v1." + base64.urlsafe_b64encode(presigned.encode()).decode().rstrip("=")

    ca = tempfile.NamedTemporaryFile(delete=False)
    ca.write(base64.b64decode(c["certificateAuthority"]["data"]))
    ca.flush()

    cfg = k8s.Configuration()
    cfg.host = c["endpoint"]
    cfg.ssl_ca_cert = ca.name
    cfg.api_key = {"authorization": "Bearer " + token}
    return cfg


def _apps_api() -> k8s.AppsV1Api:
    return k8s.AppsV1Api(k8s.ApiClient(_kube_config()))


def _core_api() -> k8s.CoreV1Api:
    return k8s.CoreV1Api(k8s.ApiClient(_kube_config()))


# --------------------------------------------------------------------------
# Tools — the agent's "execution" capabilities (layer 04 → real EKS).
# --------------------------------------------------------------------------
@tool
def query_metrics(window_min: int = 15) -> str:
    """Health signal for checkout-api: container restart counts and readiness.
    A rising restart count / not-ready pods = the incident. Reads the live k8s
    API (ground truth) AND CloudWatch Container Insights (the integration)."""
    core = _core_api()
    pods = core.list_namespaced_pod(NS, label_selector=f"app={SERVICE}").items
    restarts, not_ready = 0, 0
    for p in pods:
        for cs in (p.status.container_statuses or []):
            restarts += cs.restart_count
            if not cs.ready:
                not_ready += 1

    # CloudWatch Container Insights (best-effort; lags the live API by minutes)
    cw = "no datapoints yet"
    try:
        import datetime
        client = boto3.client("cloudwatch", region_name=REGION)
        end = datetime.datetime.utcnow()
        start = end - datetime.timedelta(minutes=window_min)
        r = client.get_metric_data(
            StartTime=start, EndTime=end,
            MetricDataQueries=[{
                "Id": "restarts",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "ContainerInsights",
                        "MetricName": "pod_number_of_container_restarts",
                        "Dimensions": [
                            {"Name": "ClusterName", "Value": CLUSTER},
                            {"Name": "Namespace", "Value": NS},
                            {"Name": "PodName", "Value": SERVICE},
                        ],
                    },
                    "Period": 60, "Stat": "Maximum",
                },
            }])
        vals = r["MetricDataResults"][0]["Values"]
        if vals:
            cw = f"max restarts/min = {max(vals)} over {window_min}m"
    except Exception as e:  # noqa: BLE001 - surface, don't crash the tool
        cw = f"unavailable ({type(e).__name__})"

    return (f"checkout-api health: pods={len(pods)} not_ready={not_ready} "
            f"total_container_restarts={restarts}\n"
            f"CloudWatch ContainerInsights: {cw}")


@tool
def get_rollout_history(service: str = SERVICE) -> str:
    """List recent ReplicaSets (revisions) of the deployment: revision, image,
    change-cause, and timestamp — so you can spot the suspect deploy."""
    rss = _apps_api().list_namespaced_replica_set(
        NS, label_selector=f"app={service}").items
    if not rss:
        return f"No ReplicaSets found for {service} in {NS}."
    lines = []
    for rs in sorted(rss, key=lambda r: r.metadata.creation_timestamp):
        ann = rs.metadata.annotations or {}
        lines.append(
            f"{rs.metadata.creation_timestamp}  "
            f"rev={ann.get('deployment.kubernetes.io/revision', '?')}  "
            f"image={rs.spec.template.spec.containers[0].image}  "
            f"cause={ann.get('kubernetes.io/change-cause', '')}")
    return "\n".join(lines)


@tool
def rollback_deployment(service: str = SERVICE, to_image: str = GOOD_IMAGE) -> str:
    """Roll a deployment back to a known-good image. RISKY — affects live
    traffic. After this, RE-MEASURE before declaring the incident resolved."""
    # Restore the full known-good container spec: set the image AND clear any
    # bad command/args the incident introduced (strategic-merge null = delete).
    _apps_api().patch_namespaced_deployment(
        service, NS,
        {"spec": {"template": {"spec": {"containers": [
            {"name": CONTAINER, "image": to_image,
             "command": None, "args": None}]}}}})
    return (f"Patched {service} → {to_image}. Pods will roll. "
            f"Re-measure health before declaring resolved.")


@tool
def execute_python(code: str, description: str = "") -> str:
    """Run Python in a secure AgentCore sandbox and return its output. Use for
    analysis/statistics on the data you gathered (e.g. summarize restart counts).
    The model authors the code; this only executes it."""
    with code_session(REGION) as c:
        resp = c.invoke("executeCode",
                        {"code": code, "language": "python", "clearContext": False})
        out = [event["result"] for event in resp["stream"]]
    return json.dumps(out)


SYSTEM = (
    "You are an SRE on-call agent for the checkout-api service on EKS. "
    "When an incident is reported: (1) call query_metrics to confirm the health "
    "signal; (2) call get_rollout_history to find the suspect recent deploy; "
    "(3) roll back to the last known-good image with rollback_deployment; "
    "(4) call query_metrics AGAIN to verify recovery, and only then report "
    "resolved. You may use execute_python to analyze numbers. Never claim a fix "
    "you did not verify. Be concise and state the root cause and action taken."
)

TOOLS = [query_metrics, get_rollout_history, rollback_deployment, execute_python]

_agent = None


def _build():
    """Lazy-build once per microVM (the VM is pinned to one session)."""
    global _agent
    if _agent is None:
        llm = ChatOpenAI(model=MODEL_ID, base_url=OPENROUTER_BASE_URL,
                         api_key=OPENROUTER_API_KEY, temperature=0)
        kwargs = {"model": llm, "tools": TOOLS, "prompt": SYSTEM}
        if MEMORY_ID:
            from langgraph_checkpoint_aws import (
                AgentCoreMemorySaver, AgentCoreMemoryStore)
            kwargs["checkpointer"] = AgentCoreMemorySaver(MEMORY_ID, region_name=REGION)
            kwargs["store"] = AgentCoreMemoryStore(MEMORY_ID, region_name=REGION)
        _agent = create_react_agent(**kwargs)
    return _agent


@app.entrypoint
def invoke(payload, context):
    prompt = payload.get("prompt", "checkout-api is unhealthy, deal with it.")
    cfg = {}
    if MEMORY_ID:
        actor = "sre-team"
        if getattr(context, "request_headers", None):
            actor = context.request_headers.get(
                "X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-Id", actor)
        cfg = {"configurable": {
            "thread_id": getattr(context, "session_id", "default") or "default",
            "actor_id": actor}}
    result = _build().invoke({"messages": [("human", prompt)]}, config=cfg or None)
    return {"response": result["messages"][-1].content}


if __name__ == "__main__":
    app.run()

# Lab — SRE agent on AgentCore Runtime, operating a real EKS cluster

A runnable companion to the AgentCore lecture. You deploy the layer-04 SRE agent
to **Amazon Bedrock AgentCore Runtime**; it reads a real `checkout-api`
Deployment's health, finds a bad rollout, and rolls it back on **EKS** — for
real. The LLM is **OpenRouter** (OpenAI-compatible); the cluster work is real IAM.

```
alert ─▶ AgentCore Runtime (the agent) ─▶ EKS: read health, rollout history, rollback
                  │                            │
          OpenRouter (Gemma)          CloudWatch Container Insights
```

## Files

| File | What |
|------|------|
| `agent/sre_agent.py` | the agent (LangGraph + OpenRouter) with EKS tools + code-interpreter, wrapped in `@app.entrypoint` |
| `agent/requirements.txt` | container deps |
| `checkout-api.yaml` | healthy baseline Deployment + Service (the rollback target) |
| `cause-incident.sh` | ships the bad "v2.3" (crash-loops → the incident) |

---

## Environment notes (this account)

- **Model: OpenRouter, not Bedrock.** The org SCP `p-vhwtjx73` denies the AWS
  Marketplace actions Bedrock's model-access flow needs, so on-demand Claude
  can't be enabled in this account. We point the agent at **OpenRouter**
  (OpenAI-compatible API) with **`google/gemma-4-31b-it:free`**. The only model
  config is **`OPENROUTER_API_KEY`**, which you must supply — the code default is
  a placeholder (`sk-or-REPLACE-ME`), not a real key. `export` it locally **and**
  pass it to the Runtime at launch (`--env`, see below) or every invoke 401s at
  the model call. No Bedrock model access, no use-case form, no inference
  profiles, no `bedrock:*` IAM. Verify your key with:
  ```bash
  curl -s https://openrouter.ai/api/v1/chat/completions \
    -H "Authorization: Bearer $OPENROUTER_API_KEY" \
    -d '{"model":"google/gemma-4-31b-it:free","messages":[{"role":"user","content":"say ok"}]}' \
    | python -c "import sys,json;print(json.load(sys.stdin)['choices'][0]['message']['content'])"
  ```
- **Region: `ap-southeast-1`** — still needed, for the EKS / CloudWatch /
  code-interpreter calls the tools make.
- Cluster: **`devops-class-eks`** (Terraform at
  `https://github.com/eveningcafe/leaning-by-practice/tree/main/cka/terraform-eks-cluster`).

---

## Prerequisites (one-time operator setup)

> These are the "heavy lift" steps — IAM/RBAC on shared infra. Run them yourself
> (they need elevated review). After this once, the build/deploy/run loop below
> is repeatable.

### 0. Tools & access
`awscli`, `kubectl`, `eksctl`, `terraform`, `docker`, `python3` on PATH;
admin AWS creds for `ap-southeast-1`; and an **OpenRouter API key** — required
(the code ships only a placeholder). Get one at <https://openrouter.ai/keys>.

> No Bedrock model access / use-case form is needed — the model is OpenRouter.

### 1. Cluster + CloudWatch Container Insights (Terraform) — already applied
The CloudWatch observability addon was added to the Terraform and applied:
```bash
cd ~/Documents/vscode/leaning-by-practice/cka/terraform-eks-cluster
terraform apply        # adds amazon-cloudwatch-observability + CloudWatchAgentServerPolicy on the node role
aws eks update-kubeconfig --region ap-southeast-1 --name devops-class-eks
kubectl get pods -n amazon-cloudwatch        # cloudwatch-agent + fluent-bit Running
```

### 2. Enable EKS access entries (auth mode)
Access entries require the cluster auth mode to include the API. This is
**non-destructive** (keeps the existing aws-auth configmap):
```bash
aws eks update-cluster-config --name devops-class-eks --region ap-southeast-1 \
  --access-config authenticationMode=API_AND_CONFIG_MAP
# wait until ACTIVE again:
aws eks describe-cluster --name devops-class-eks --region ap-southeast-1 --query cluster.status
```

### 3. Grant the Runtime execution role (after the first `agentcore launch`)
`agentcore launch` (below) auto-creates the execution role
`AmazonBedrockAgentCoreSDKRuntime-ap-southeast-1-<hash>`. Grant it what the agent
needs — EKS describe, CloudWatch read, code-interpreter (no Bedrock: the model is
OpenRouter) — and an **EKS access entry scoped to the `default` namespace**:

```bash
ROLE=AmazonBedrockAgentCoreSDKRuntime-ap-southeast-1-<hash>     # from: agentcore status
ROLE_ARN=arn:aws:iam::<account>:role/$ROLE

# 3a. IAM perms (lab-simple: Resource:* ; tighten for prod)
cat > sre-extra.json <<'JSON'
{ "Version": "2012-10-17", "Statement": [
  {"Effect":"Allow","Action":["eks:DescribeCluster"],"Resource":"*"},
  {"Effect":"Allow","Action":["cloudwatch:GetMetricData","cloudwatch:ListMetrics"],"Resource":"*"},
  {"Effect":"Allow","Action":["bedrock-agentcore:StartCodeInterpreterSession","bedrock-agentcore:InvokeCodeInterpreter","bedrock-agentcore:StopCodeInterpreterSession","bedrock-agentcore:GetCodeInterpreterSession","bedrock-agentcore:ListCodeInterpreterSessions"],"Resource":"*"}
]}
JSON
aws iam put-role-policy --role-name $ROLE --policy-name sre-lab-extra \
  --policy-document file://sre-extra.json

# 3b. EKS RBAC: let the role edit workloads in the default namespace
aws eks create-access-entry --cluster-name devops-class-eks --region ap-southeast-1 \
  --principal-arn $ROLE_ARN
aws eks associate-access-policy --cluster-name devops-class-eks --region ap-southeast-1 \
  --principal-arn $ROLE_ARN \
  --policy-arn arn:aws:eks::aws:cluster-access-policy/AmazonEKSEditPolicy \
  --access-scope type=namespace,namespaces=default
```

> Why: the agent's *tools* run as this role. It must be allowed to read the
> cluster, read metrics, run the sandbox, and `patch` the Deployment. (The model
> call goes to OpenRouter over its own API key, not IAM.) The RBAC is
> **namespace-scoped** to `default`.

---

## Build & deploy the agent

```bash
cd 05-application/lab/sre-agent
python3 -m venv .venv && source .venv/bin/activate
pip install bedrock-agentcore-starter-toolkit

export AWS_REGION=ap-southeast-1
export OPENROUTER_API_KEY=sk-or-...        # YOUR real key — the model 401s without it
# configure (writes .bedrock_agentcore.yaml locally — creates nothing in AWS):
agentcore configure -e agent/sre_agent.py -n sre_agent \
  -rf agent/requirements.txt --disable-memory
# launch — MUST inject the key as a Runtime env var, or every invoke fails at the model call:
agentcore launch --env OPENROUTER_API_KEY="$OPENROUTER_API_KEY"
agentcore status            # ← grab the execution role name for prerequisite step 3
```

> ⚠️ Without `--env OPENROUTER_API_KEY=...`, `agentcore launch` still succeeds, but
> the deployed agent has only the placeholder key and every `agentcore invoke`
> 401s at the OpenRouter call. Re-launch with the flag to fix it.

After step 3's grants are in place, the agent's tools can reach EKS + CloudWatch.

---

## Run the demo

```bash
# 1. Healthy baseline ("v2.2")
kubectl apply -f checkout-api.yaml
kubectl get pods -l app=checkout-api          # 2/2 Running

# 2. Cause the incident — ship the bad "v2.3" (crash-loops)
bash cause-incident.sh
kubectl get pods -l app=checkout-api          # CrashLoopBackOff, restarts climbing

# 3. Hand it to the agent
agentcore invoke '{"prompt":"checkout-api is failing after a deploy, investigate and fix it."}' \
  --session-id incident-checkout-crashloop-0000000000

# Expected: the agent calls query_metrics (sees not-ready / restarts),
# get_rollout_history (spots v2.3 "bad build"), rollback_deployment
# (→ nginx:1.27-alpine), then re-checks and reports resolved.

# 4. Verify the cluster recovered
kubectl get pods -l app=checkout-api          # back to Running
kubectl rollout history deployment/checkout-api
```

Watch the agent's reasoning + tool calls live:
```bash
aws logs tail /aws/bedrock-agentcore/runtimes/sre_agent-<id>-DEFAULT \
  --region ap-southeast-1 --follow
```

---

## Cleanup

```bash
agentcore destroy                              # Runtime, ECR, auto-created IAM
kubectl delete -f checkout-api.yaml
# (optional) remove the access entry + lab IAM policy:
aws eks delete-access-entry --cluster-name devops-class-eks --region ap-southeast-1 --principal-arn $ROLE_ARN
aws iam delete-role-policy --role-name $ROLE --policy-name sre-lab-extra
# the EKS cluster itself is your existing Terraform — leave it or `terraform destroy`.
```

> The CloudWatch addon is the only *new recurring* cost the lab adds to the
> cluster; everything AgentCore-side is consumption-based and removed by
> `agentcore destroy`.

---

## What's already done in this environment

- ✅ Terraform: CloudWatch observability addon applied (`cloudwatch-agent` +
  `fluent-bit` Running); drifted node group imported back into state.
- ✅ `checkout-api` healthy baseline deployed.
- ✅ Agent deployed to AgentCore Runtime:
  `arn:aws:bedrock-agentcore:ap-southeast-1:891920435433:runtime/sre_agent-vdfgfp49e8`.
- ⏳ **Remaining (prerequisite steps 2 & 3):** flip cluster auth mode +
  grant the execution role IAM/EKS access. Until then, `agentcore invoke`
  will fail at the EKS/CloudWatch calls. Run those two steps, then invoke.

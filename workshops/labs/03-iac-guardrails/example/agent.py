"""Case 3 — IaC generate → review → policy gate, on AgentCore Runtime.

Simulated generate + checkov scan (no Terraform/checkov to install). The hard
rule: any HIGH finding blocks 'apply'. Model: OpenRouter. See README.md.
"""
import os

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.models.openai import OpenAIModel

app = BedrockAgentCoreApp()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY  = os.getenv("OPENROUTER_API_KEY", "sk-or-REPLACE-ME")
MODEL_ID = os.getenv("MODEL_ID", "google/gemma-4-31b-it")

model = OpenAIModel(
    client_args={"api_key": OPENROUTER_API_KEY, "base_url": OPENROUTER_BASE_URL},
    model_id=MODEL_ID,
)


@tool
def generate_terraform(request: str, secure: bool = False) -> str:
    """Generate a Terraform snippet for the request. secure=False emits the fast,
    plausible-but-risky version; secure=True applies constraint-first hardening."""
    if secure:
        return ('resource "aws_security_group" "sg" {\n'
                '  ingress { from_port=443 to_port=443 protocol="tcp" cidr_blocks=["10.0.0.0/8"] }\n}\n'
                'resource "aws_s3_bucket_public_access_block" "b" { block_public_acls=true }')
    return ('resource "aws_security_group" "sg" {\n'
            '  ingress { from_port=22 to_port=22 protocol="tcp" cidr_blocks=["0.0.0.0/0"] }\n}\n'
            'resource "aws_s3_bucket" "b" { bucket="data" }  # no public-access block')


@tool
def checkov_scan(terraform: str) -> str:
    """Static policy scan. Returns findings by severity. Any HIGH blocks apply."""
    findings = []
    if "0.0.0.0/0" in terraform:
        findings.append("HIGH  CKV_AWS_260  Security group allows ingress from 0.0.0.0/0")
    if "public_access_block" not in terraform and "aws_s3_bucket" in terraform:
        findings.append("HIGH  CKV_AWS_53   S3 bucket missing public-access block")
    if not findings:
        return "PASSED — 0 HIGH findings. Safe to apply."
    return "FAILED — HIGH findings present (apply blocked):\n" + "\n".join(findings)


SYSTEM_PROMPT = (
    "You are an IaC guardrail agent. Loop: L1 generate_terraform → L2 review the "
    "resources → L3 checkov_scan. HARD RULE: if the scan reports any HIGH finding, "
    "do NOT approve apply — regenerate with secure=True and re-scan. Only report "
    "'safe to apply' once the scan PASSES with 0 HIGH. Show the passing snippet and "
    "the fixes you made."
)


@app.entrypoint
def invoke(payload, context):
    agent = Agent(model=model, system_prompt=SYSTEM_PROMPT,
                  tools=[generate_terraform, checkov_scan])
    result = agent(payload.get("prompt", "Write Terraform for an SSH security group and an S3 bucket."))
    return {"response": result.message.get("content", [{}])[0].get("text", str(result))}


if __name__ == "__main__":
    app.run()

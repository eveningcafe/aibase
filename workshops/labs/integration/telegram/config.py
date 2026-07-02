"""Telegram bridge config. No secrets in here — bot tokens come from env vars.

Each bot maps to one deployed AgentCore Runtime (ARNs from
workshops/labs/.bedrock_agentcore.yaml; refresh with `agentcore status` after a
redeploy). Set the four tokens from BotFather in your shell before running:

  export TG_TOKEN_INCIDENT_RCA=...
  export TG_TOKEN_RAG_TELEMETRY=...
  export TG_TOKEN_IAC_GUARDRAILS=...
  export TG_TOKEN_CICD_RISK=...
"""
import os

from dotenv import load_dotenv

load_dotenv()   # pull TG_TOKEN_* from a local .env if present (gitignored)

REGION = "ap-southeast-1"

BOTS = {
    "incident_rca": {
        "token": os.getenv("TG_TOKEN_INCIDENT_RCA", ""),
        "runtime_arn": "arn:aws:bedrock-agentcore:ap-southeast-1:891920435433:runtime/incident_rca-bvnyVp2LHv",
        "blurb": "triage → RCA → rollback",
    },
    "rag_telemetry": {
        "token": os.getenv("TG_TOKEN_RAG_TELEMETRY", ""),
        "runtime_arn": "arn:aws:bedrock-agentcore:ap-southeast-1:891920435433:runtime/rag_telemetry-boIH0B9d4o",
        "blurb": "RAG over incident history + runbooks",
    },
    "iac_guardrails": {
        "token": os.getenv("TG_TOKEN_IAC_GUARDRAILS", ""),
        "runtime_arn": "arn:aws:bedrock-agentcore:ap-southeast-1:891920435433:runtime/iac_guardrails-MctBQeGGoD",
        "blurb": "IaC generate → review → policy gate",
    },
    "cicd_risk": {
        "token": os.getenv("TG_TOKEN_CICD_RISK", ""),
        "runtime_arn": "arn:aws:bedrock-agentcore:ap-southeast-1:891920435433:runtime/cicd_risk-F9MB0iAMtG",
        "blurb": "blast-radius + risk score → merge gate",
    },
}

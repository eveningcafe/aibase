# 01 · Infrastructure

The compute layer. LLMs generally require **AI-specific hardware (GPUs)**.
What infrastructure you have — and how you deploy it — drives cost, speed, and
what model sizes you can run at all.

## Three deployment modes

| Dir | Mode | When to use |
|-----|------|-------------|
| `on-premise/` | Own the hardware | You have the budget/resources and want full control. |
| `cloud/` | Rent capacity | Scale up/down on demand; no upfront hardware. |
| `local/` | Laptop / dev box | Small models, prototyping. Limited by local GPU. |

## What goes here

- IaC (Terraform, Pulumi), Kubernetes / GPU node manifests
- Cloud provisioning scripts (GPU instances, autoscaling)
- Local dev setup (Docker Compose, Ollama / llama.cpp configs)
- Capacity & cost notes per environment

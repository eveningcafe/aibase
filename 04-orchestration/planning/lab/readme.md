# Lab — "Pause" nhìn từ API: agent dừng lại hỏi người

## Chuẩn bị

Dùng model **miễn phí** có reasoning + tool calling, endpoint OpenAI-compatible:

| | |
|---|---|
| Endpoint | `https://openrouter.ai/api/v1/chat/completions` |
| Model | `openai/gpt-oss-120b:free` |
| Key | lấy free ở <https://openrouter.ai/keys> (không cần thẻ) |

```bash
export OPENROUTER_API_KEY='sk-or-v1-...'   # dán key của bạn vào đây
```

---

## Bước 1 — TURN 1: ép model DỪNG và hỏi

### Request (gửi đi nguyên văn)

```bash
curl -s https://openrouter.ai/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -d '{
  "model": "openai/gpt-oss-120b:free",
  "messages": [
    {
      "role": "system",
      "content": "You are an SRE agent. You have ALREADY found the root cause: deploy v2.3 shrank the checkout-api DB pool to 5, causing 5xx. The fix requires a rollback, which is RISKY (affects users mid-checkout). You MUST NOT decide the fix yourself. Your ONLY allowed next action is to call the ask_user tool. Do not answer in text."
    },
    {
      "role": "user",
      "content": "checkout-api is throwing 5xx. Deal with it."
    }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "rollback_deployment",
        "description": "Roll a service back to a previous version. RISKY.",
        "parameters": {
          "type": "object",
          "properties": {
            "service": { "type": "string" },
            "to_version": { "type": "string" }
          },
          "required": ["service", "to_version"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "ask_user",
        "description": "Ask the human to choose when the agent must not decide alone.",
        "parameters": {
          "type": "object",
          "properties": {
            "question": { "type": "string" },
            "options": { "type": "array", "items": { "type": "string" } }
          },
          "required": ["question", "options"]
        }
      }
    }
  ],
  "tool_choice": { "type": "function", "function": { "name": "ask_user" } },
  "max_tokens": 1200,
  "temperature": 1
}'
```

### Response

```json
{
    "id": "gen-1782370827-GPGOLVY4MkeS50zkMYB7",
    "object": "chat.completion",
    "created": 1782370827,
    "model": "openai/gpt-oss-120b:free",
    "provider": "OpenInference",
    "system_fingerprint": null,
    "service_tier": null,
    "choices": [
        {
            "index": 0,
            "logprobs": null,
            "finish_reason": "tool_calls",
            "native_finish_reason": "tool_calls",
            "message": {
                "role": "assistant",
                "content": null,
                "refusal": null,
                "reasoning": "We must ask user.",
                "tool_calls": [
                    {
                        "type": "function",
                        "index": 0,
                        "id": "chatcmpl-tool-95da60a308cec41f",
                        "function": {
                            "name": "ask_user",
                            "arguments": "{\n  \"question\": \"A recent deployment (v2.3) reduced the DB pool size for checkout‑api, causing 5xx errors. The fix is to roll back to the previous version, which is risky as it may affect users currently in checkout. How would you like to proceed?\",\n  \"options\": [\n    \"Proceed with rollback to previous version\",\n    \"Investigate alternative mitigation (e.g., increase pool size without full rollback)\",\n    \"Do nothing for now\"\n  ]\n}"
                        }
                    }
                ],
                "reasoning_details": [
                    {
                        "type": "reasoning.text",
                        "text": "We must ask user.",
                        "format": "unknown",
                        "index": 0
                    }
                ]
            }
        }
    ],
    "usage": {
        "prompt_tokens": 263,
        "completion_tokens": 126,
        "total_tokens": 389,
        "cost": 0,
        "is_byok": false,
        "prompt_tokens_details": {
            "cached_tokens": 64,
            "cache_write_tokens": 0,
            "audio_tokens": 0,
            "video_tokens": 0
        },
        "cost_details": {
            "upstream_inference_cost": 0,
            "upstream_inference_prompt_cost": 0,
            "upstream_inference_completions_cost": 0
        },
        "completion_tokens_details": {
            "reasoning_tokens": 5,
            "image_tokens": 0,
            "audio_tokens": 0
        }
    }
}
```

### Đọc gì trong response?

- **`finish_reason: "tool_calls"`** — model không trả lời, nó muốn gọi tool. *Đây
  chính là pause.*
- **`content: null`** — chưa có chữ nào cho người dùng → vòng lặp phải dừng.
- **`reasoning: "We must ask user."`** — model tự nhủ trước khi gọi (đây là token
  suy nghĩ ở [../readme.md](../readme.md)).
- **`tool_calls[0].id` = `chatcmpl-tool-95da60a308cec41f`** — cần *y nguyên* id này
  cho TURN 2.
- **`arguments`** là một **chuỗi JSON đã escape** (có `\n`, `‑`…), không phải
  object. Parse nó ra mới lấy được `question` + `options` để hiện cho người.

> Lúc này **vòng lặp của bạn đứng chờ**. Bạn hiện 3 option cho SRE; họ bấm
> *"Proceed with rollback to previous version"*. Không gì chạy tiếp tới khi có trả lời.

---

## Bước 2 — TURN 2: resume (đưa lựa chọn của người về model)

Điểm cốt lõi là 3
dòng ở cuối: `messages.append(assistant)` + append `role:"tool"` + gọi lại.

```python
import os, json, requests   # pip install requests

URL = "https://openrouter.ai/api/v1/chat/completions"
HEADERS = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}
MODEL = "openai/gpt-oss-120b:free"

tools = [
    {"type": "function", "function": {
        "name": "rollback_deployment",
        "description": "Roll a service back to a previous version. RISKY.",
        "parameters": {"type": "object", "properties": {
            "service": {"type": "string"}, "to_version": {"type": "string"}},
            "required": ["service", "to_version"]}}},
    {"type": "function", "function": {
        "name": "ask_user",
        "description": "Ask the human to choose when the agent must not decide alone.",
        "parameters": {"type": "object", "properties": {
            "question": {"type": "string"},
            "options": {"type": "array", "items": {"type": "string"}}},
            "required": ["question", "options"]}}},
]

messages = [
    {"role": "system", "content": "You are an SRE agent. You have ALREADY found the root cause: deploy v2.3 shrank the checkout-api DB pool to 5, causing 5xx. The fix requires a rollback, which is RISKY (affects users mid-checkout). You MUST NOT decide the fix yourself. Your ONLY allowed next action is to call the ask_user tool. Do not answer in text."},
    {"role": "user", "content": "checkout-api is throwing 5xx. Deal with it."},
]

def chat(**extra):
    body = {"model": MODEL, "messages": messages, "tools": tools, **extra}
    return requests.post(URL, headers=HEADERS, json=body).json()

# ── TURN 1 — ép ask_user → model PAUSE (trả tool_call, không trả lời) ──
resp1 = chat(tool_choice={"type": "function", "function": {"name": "ask_user"}})
assistant = resp1["choices"][0]["message"]
call = assistant["tool_calls"][0]
args = json.loads(call["function"]["arguments"])      # arguments là chuỗi JSON
print("PAUSE  finish_reason =", resp1["choices"][0]["finish_reason"],
      "| tool =", call["function"]["name"])
print("Hỏi:", args["question"])
for i, o in enumerate(args["options"], 1):
    print(f"  [{i}] {o}")

# ── người chọn (demo: lấy option đầu; thực tế là UI cho SRE bấm) ──
choice = args["options"][0]
print("Người chọn:", choice)

# ── TURN 2 — RESUME: chỉ cần APPEND 2 message rồi gọi lại ──
messages.append(assistant)                            # 1) lượt assistant chứa tool_call
messages.append({"role": "tool",                      # 2) kết quả tool = câu trả lời người
                 "tool_call_id": call["id"],
                 "content": choice})
resp2 = chat(tool_choice="auto")
call2 = resp2["choices"][0]["message"]["tool_calls"][0]
print("RESUME finish_reason =", resp2["choices"][0]["finish_reason"])
print("Model gọi:", call2["function"]["name"], call2["function"]["arguments"])
```

### Output

```text
PAUSE  finish_reason = tool_calls | tool = ask_user
Hỏi: Rollback to the previous version to restore DB pool size?
  [1] Yes, proceed with rollback
  [2] No, investigate alternative fixes
Người chọn: Yes, proceed with rollback
RESUME finish_reason = tool_calls
Model gọi: rollback_deployment {
    "service": "checkout-api",
    "to_version": "v2.2"
}
```

## 3 điểm mấu chốt

1. **Pause sống trong code của bạn, không trong API.** API chỉ trả "tôi muốn gọi
   tool" (`finish_reason: "tool_calls"`, `content: null`); *bạn* mới là người dừng
   vòng lặp và chờ.
2. **`ask_user` = một tool bình thường.** Khác `rollback_deployment` đúng ở một chỗ:
   "người thực thi" là con người + một ô bấm, và nhánh `if name == "ask_user"` trong
   code bạn.
3. **Resume = append lượt `assistant` (có `tool_calls`) + một `role:"tool"` cùng
   `tool_call_id`, rồi gọi lại.** Thiếu lượt `assistant` thì model không biết nó vừa
   hỏi gì.

## Cảnh báo `tool_choice` (khác nhau theo provider)

`tool_choice` để **ép** model gọi đúng một tool — nhưng không phải endpoint nào cũng
tôn trọng:

| Endpoint / model | `tool_choice` đặt tên hàm |
|---|---|
| `openai/gpt-oss-120b:free` (OpenRouter) | ✅ ép được (response TURN 1 ở trên) |
| `minimax/minimax-m2.5` | ❌ bỏ qua → trả text |

Nếu endpoint **bỏ qua** `tool_choice`: ép bằng **prompt** thay vì tham số — đặt model
vào đúng điểm quyết định và nói "hành động duy nhất được phép là gọi `ask_user`"
(chính là `system` prompt ở TURN 1). Cách này hợp với bài học gốc: pause **nảy ra từ
reasoning**, không phải do code cài cứng.

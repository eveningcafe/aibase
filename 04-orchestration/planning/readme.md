# Planning — agent suy nghĩ, dừng lại, và hỏi

> Tóm lược & diễn giải, lấy cảm hứng từ video **"What Are Large Reasoning Models
> (LRMs)? Smarter AI Beyond LLMs"** — IBM Technology ·
> <https://www.youtube.com/watch?v=enLbj0igyx4>

Đây là ô **`planning/`** trong vòng lặp orchestration ở [../README.md](../README.md):
`plan → execute → review → (memory) → loop`. Phần này nói về cái **"plan"** —
khâu *suy nghĩ* trước khi hành động: phân rã tác vụ, quyết định cần dữ liệu/tool gì,
và biết **khi nào nên dừng lại hỏi người dùng**.

> **Ví dụ xuyên suốt — một agent SRE.** Lúc 14:35, cảnh báo nổ: service
> `checkout-api` lỗi **5xx tăng vọt**. SRE trực không tự gõ runbook, chỉ nói ý định:
> *"checkout-api đang lỗi 5xx, xử lý giúp."* Cả bài này ta bám theo agent đó —
> từ lúc nó *suy luận tìm nguyên nhân*, đến lúc *dừng lại hỏi* nên rollback hay không.

---

## 1. Khác gì phần mềm truyền thống?

Điểm cốt lõi nằm ở **ai viết ra các bước**.

```
PHẦN MỀM TRUYỀN THỐNG                 AGENT (SRE on-call)
─────────────────────                 ───────────────────
Runbook viết SẴN từng bước,           Người dùng nói Ý ĐỊNH (intent):
duyệt/biên dịch TRƯỚC.                "checkout-api đang lỗi 5xx, xử lý giúp"
                                              │
if error_rate > 5%:                           ▼
    restart_pods()                    MODEL tự NGHĨ RA các bước lúc chạy:
elif latency > 1s:                      1. xem metric: 5xx bắt đầu lúc nào?
    scale_up()                          2. có deploy nào trùng mốc đó không?
                                        3. đọc log → tìm nguyên nhân
Máy chỉ chạy đúng kịch bản              4. (cần rollback? → HỎI người)
đã lường trước. Tình huống lạ           5. rollback / scale, rồi xác minh lại
ngoài kịch bản → bó tay.
```

- **Phần mềm truyền thống:** quy trình được **soạn trước** (compose-time). Mọi nhánh
  `if/else`, mọi vòng lặp, mọi chỗ "dừng lại hỏi người dùng" đều do lập trình viên
  *gõ tay từ trước*. Máy không bao giờ nghĩ — nó **thi hành**.
- **Agent:** người dùng chỉ đưa **ý định**, không đưa thủ tục. Agent phải **tự nghĩ
  ra các bước** ngay lúc chạy (run-time), tùy ngữ cảnh mỗi lần một khác.

> Phần mềm truyền thống = công thức nấu ăn viết sẵn, cứ thế làm theo.
> Agent = đầu bếp được giao *"nấu món gì đó ngon cho 4 người ăn chay"* rồi tự quyết.

Vì các bước **không** được viết sẵn nữa, năng lực quan trọng nhất ở lớp này là khả
năng **suy luận (reasoning)** — biến *ý định* thành *kế hoạch*. Đó là lý do "reasoning
model" ra đời.

---

## 2. Reasoning model thật ra đang làm gì? (xuống tận mức token)

Để hiểu, phải nhớ LLM sinh chữ thế nào: **một token mỗi lần, tuần tự
(autoregressive)**. Mỗi bước, model nhìn *toàn bộ* chữ đã có rồi tính xác suất cho
token kế tiếp, chọn một token, ghép vào, lặp lại.

```
"Thủ đô nước Pháp là" → [model] → token kế: "Paris" (xác suất cao nhất)
ghép vào → "Thủ đô nước Pháp là Paris" → sinh tiếp token sau...
```

### Model thường vs. reasoning model

```
MODEL THƯỜNG (sự cố checkout-api):
prompt ──▶ [nhả ngay câu trả lời] ──▶ "Thử restart pod xem sao."
           (đoán nhanh, dễ trật nguyên nhân thật)

REASONING MODEL:
prompt ──▶ [nhả 1 ĐỐNG token "suy nghĩ" trước]  ──▶ rồi mới kết luận
           ┌──────────────────── nháp (scratchpad) ─────────────────────┐
           │ "5xx tăng từ 14:32. Có gì đổi quanh mốc đó? → deploy v2.3   │
           │  lúc 14:30. Nghi do deploy. Đọc log: 'DB connection         │
           │  timeout'. v2.3 có đổi pool size? → đúng, pool tụt còn 5.   │
           │  Vậy nguyên nhân là deploy v2.3, KHÔNG phải tải tăng."      │
           └─────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
            "Nguyên nhân: deploy v2.3 siết DB pool. Hướng xử lý: rollback."
```

**Chuỗi token "suy nghĩ" đó (chain-of-thought) chính là reasoning.** Vài điều mấu chốt
ở mức token:

1. **Token suy nghĩ cũng chỉ là token bình thường** — sinh ra y hệt cách trên. Không
   có phép màu; chỉ là model viết nháp ra *trước khi* viết đáp án.
2. **Mỗi token viết ra lại quay vào ngữ cảnh, dẫn dắt token sau.** Model đang **tự
   viết ghi chú cho chính mình**. Câu "ồ sai rồi, quay lại" thật sự làm các token kế
   tiếp đổi hướng. Nháp càng tốt → đáp án càng dễ đúng.
3. **Mỗi token = một lượng tính toán (một lần forward).** Sinh nhiều token nháp =
   bỏ ra **nhiều compute hơn** cho bài toán. Đây gọi là **test-time compute** —
   "nghĩ lâu hơn" theo nghĩa đen là *sinh thêm token trước khi chốt*. Bài khó → để nó
   nghĩ dài hơn.
4. **Học bằng RL (reinforcement learning), không phải bắt chước.** Model thường học
   bằng cách *bắt chước* văn bản người viết. Reasoning model (o1, DeepSeek-R1…) được
   **thưởng khi ra đáp án đúng**, bất kể nháp thế nào. Nhờ vậy nó **tự khám phá** các
   thói quen hữu ích: thử nhiều hướng, kiểm tra lại, quay lui khi sai — chứ không ai
   dạy từng bước.

### Luyện ra một reasoning model thế nào? (3 chặng)

Không phải train từ đầu. Người ta **lấy một LLM thường rồi luyện thêm** cho biết suy
luận — đi qua 3 chặng nối tiếp:

```
┌──────────────┐   ┌───────────────────────────┐   ┌──────────────────────────┐
│ 1. PRETRAIN  │──▶│ 2. FINE-TUNE (reasoning)   │──▶│ 3. REINFORCEMENT LEARNING │
│   base LLM   │   │   dạy CÁCH trình bày lời    │   │   THƯỞNG theo KẾT QUẢ      │
│              │   │   giải từng bước            │   │                           │
├──────────────┤   ├───────────────────────────┤   ├──────────────────────────┤
│ nuốt cả      │   │ data = bài toán PHỨC TẠP   │   │ model tự sinh nháp →      │
│ internet     │   │ (toán, code, logic,        │   │ chấm đúng/sai → THƯỞNG     │
│ → ngôn ngữ   │   │  khoa học), mỗi mẫu KÈM     │   │ cái nháp dẫn tới đáp án   │
│ + kiến thức  │   │ CHUỖI suy luận từng bước    │   │ đúng → model TỰ KHÁM PHÁ:  │
│ thế giới     │   │ (chain-of-thought)          │   │ thử, kiểm tra, quay lui   │
└──────────────┘   └───────────────────────────┘   └──────────────────────────┘
  "biết chữ,         "biết VIẾT NHÁP từng           "biết suy luận cho ĐÚNG,
   biết đời"          bước cho bài khó"               tự sửa — không ai dạy tay"
```

- **Chặng 1 — Pretrain:** học không giám sát trên lượng văn bản khổng lồ → có ngôn
  ngữ và kiến thức nền. (Giống mọi LLM thường.)
- **Chặng 2 — Fine-tune hướng suy luận (SFT):** học có giám sát trên **bài toán phức
  tạp** kèm sẵn **lời giải từng bước**. Dạy model *thói quen viết nháp* trước khi đáp.
- **Chặng 3 — RL:** cho model tự sinh nháp, **chấm kết quả cuối đúng hay sai**, rồi
  thưởng những lần ra đúng. Vì chỉ thưởng *kết quả*, model **tự nghĩ ra** cách nháp tốt
  hơn — kể cả những "khoảnh khắc aha" như tự nhận sai rồi quay lui.

> Chặng 2 dạy *hình thức* (trình bày từng bước); chặng 3 dạy *thực chất* (suy cho ra
> kết quả đúng). Thiếu chặng 3, model chỉ "trông có vẻ đang nghĩ" mà chưa chắc nghĩ đúng.

> Tương tự con người: bài toán khó bạn không buột miệng đáp ngay — bạn **nháp ra
> giấy**, thử, gạch đi, thử lại, rồi mới viết đáp số. Reasoning model nháp bằng token.

### Liên hệ tới `planning/`

Chuỗi nháp này **chính là** khâu planning: trong lúc "nghĩ", model **phân rã** ý định
thành các bước, và quyết định **cần tool/dữ liệu gì** — kể cả nhận ra *"chỗ này mình
thiếu thông tin, phải hỏi người dùng"*. Dẫn thẳng sang phần sau.

---

## 3. Cơ chế DỪNG LẠI và hỏi (AskUserQuestion)

Khác biệt lớn so với phần mềm truyền thống nằm ở đây:

| | Phần mềm truyền thống | Agent |
|---|---|---|
| Chỗ dừng để hỏi | Lập trình viên **gõ sẵn** một form/`input()` ở đúng dòng đó | **Model tự quyết** lúc chạy, ở chỗ nó thấy cần |
| Ai chọn câu hỏi | Đã định trước | Model sinh ra câu hỏi + các lựa chọn ngay lúc đó |

Quay lại agent SRE: nó đã suy ra nguyên nhân (deploy v2.3 siết DB pool). Nhưng
**cách xử lý là một quyết định rủi ro của con người** — rollback ảnh hưởng người dùng
đang thanh toán. Model **không** tự ý rollback. Nó **dừng vòng lặp lại** và phát ra
một lời gọi tool tên `AskUserQuestion`.

```
1. Model đang nghĩ: "đã rõ nguyên nhân, nhưng rollback là hành động rủi ro —
   phải để người quyết: rollback hay hotfix?"
        │
        ▼
2. MODEL phát tool_use: AskUserQuestion
   { question: "Xử lý checkout-api thế nào?",
     options: ["Rollback về v2.2", "Giữ v2.3, tăng lại DB pool"] }
        │
        ▼
3. CLIENT (vd Claude Code) KHÔNG chạy gì —
   nó HIỆN một ô cho SRE bấm chọn
        │
        ▼
4. SRE chọn "Rollback về v2.2"
        │
        ▼
5. CLIENT trả "Rollback về v2.2" về cho MODEL (như một tool_result)
        │
        ▼
6. MODEL nghĩ tiếp với quyết định đã có → gọi tool rollback_deployment
```

Điểm cốt yếu: **chỗ dừng này không hề được viết sẵn trong code.** Nó *nảy ra từ quá
trình suy luận*. Lập trình viên không thể đoán trước sự cố lần này do deploy v2.3 —
nhưng agent gặp tình huống đó thì tự biết dừng để hỏi nên rollback hay hotfix.

---

## 4. Hỏi người dùng = MỘT tool call bình thường

Nhiều người tưởng "hỏi người dùng" là cơ chế đặc biệt. **Không.** Nó dùng *đúng* cơ
chế gọi tool mà ta đã thấy ở [../mcp/readme.md](../mcp/readme.md): `tool_use → kết
quả → nghĩ tiếp`. Khác biệt duy nhất: **ai thực thi tool** — lần này là *con người
qua giao diện*, thay vì server chạy code.

Ở mức API, **mọi tool đều khai báo y hệt nhau** trong cùng một danh sách, mỗi tool
một schema riêng:

```python
tools = [
    {   # tool chạy bằng CODE — tác động THẬT lên hệ thống (như server ở mcp/)
        "name": "rollback_deployment",
        "description": "Rollback một service về version trước",
        "parameters": {"type": "object", "properties": {
            "service": {"type": "string"}, "to_version": {"type": "string"}},
            "required": ["service", "to_version"]},
    },
    {   # tool "hỏi người dùng" — CHỈ là một tool nữa, schema shape cho câu hỏi
        "name": "ask_user",
        "description": "Hỏi người dùng một quyết định khi không tự quyết được",
        "parameters": {"type": "object", "properties": {
            "question": {"type": "string"},
            "options": {"type": "array", "items": {"type": "string"}}},
            "required": ["question", "options"]},
    },
]
```

Model nhả ra **cùng một định dạng** cho cả hai — chỉ khác cái tên + arguments:

```jsonc
{ "name": "rollback_deployment", "arguments": {"service": "checkout-api",
                                               "to_version": "v2.2"} }
{ "name": "ask_user",            "arguments": {"question": "Xử lý checkout-api thế nào?",
                                               "options": ["Rollback về v2.2",
                                                           "Giữ v2.3, tăng lại DB pool"]} }
```

**Chỗ "rẽ nhánh" nằm trong CODE của bạn, rẽ theo TÊN tool** — đây mới là nơi khác
biệt duy nhất tồn tại:

```python
resp = client.chat.completions.create(model=..., messages=msgs, tools=tools)
call = resp.choices[0].message.tool_calls[0]
args = json.loads(call.function.arguments)

if call.function.name == "ask_user":
    result = render_ui_and_wait(args)        # ← HIỆN UI, SRE trả lời (vòng lặp DỪNG ở đây)
elif call.function.name == "rollback_deployment":
    result = rollback_deployment(**args)     # ← CHẠY thật: gọi API hạ tầng, rollback service

# gửi kết quả NGƯỢC lại model — y hệt nhau cho cả hai loại
msgs.append({"role": "tool", "tool_call_id": call.id, "content": str(result)})
resp = client.chat.completions.create(model=..., messages=msgs, tools=tools)  # model nghĩ tiếp
```

Tóm lại:

- **Hỏi người dùng = một tool**, mà "người thực thi" là *con người + một ô bấm chọn*.
- Vòng lặp agent **đứng chờ** ở `render_ui_and_wait(...)` — đó chính là cái "pause".
- Không cần cơ chế riêng: cùng `tools`, cùng `tool_use`, cùng bước "trả kết quả về".
  Cái biến nó thành "hỏi người" thay vì "chạy code" chỉ là nhánh `if name == ...`.

> So với mục 1: phần mềm truyền thống *gõ sẵn* form hỏi ở compose-time. Agent thì
> **model tự gọi** tool hỏi ở run-time, đúng lúc reasoning thấy cần.

---

## Nhớ nhanh

- Phần mềm truyền thống **thi hành thủ tục viết sẵn**; agent **suy luận ra thủ tục từ
  ý định** lúc chạy → vì thế **reasoning** là năng lực lõi của `planning/`.
- Reasoning ở mức token = model **viết nháp (chain-of-thought) trước khi trả lời**;
  nháp nhiều = compute nhiều (test-time compute); học bằng **RL thưởng theo kết quả**.
- **Dừng để hỏi** không viết sẵn — nó *nảy ra từ suy luận*, rồi phát thành một
  **tool call** (`AskUserQuestion`).
- Tool hỏi-người và tool chạy-code **cùng một cơ chế**; khác nhau chỉ ở **người thực
  thi** và nhánh `if` trong code bạn.

## Liên quan

- Vòng lặp tổng & các ô khác: [../README.md](../README.md)
- Cơ chế gọi tool đầy đủ (model → client → server): [../mcp/readme.md](../mcp/readme.md)
- Bộ nhớ giữ trạng thái xuyên các bước: [../memory/readme.md](../memory/readme.md)

## Nguồn

- IBM Technology — *What Are Large Reasoning Models (LRMs)? Smarter AI Beyond LLMs*:
  <https://www.youtube.com/watch?v=enLbj0igyx4>
- DeepSeek-AI — *DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via RL* (2025):
  <https://arxiv.org/abs/2501.12948>

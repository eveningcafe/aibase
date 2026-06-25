# Memory — 4 loại bộ nhớ mỗi agent cần

> Tóm lược & diễn giải từ video **"The Four Types of Memory Every AI Agent Needs"**
> — Martin Keen, IBM Technology · <https://www.youtube.com/watch?v=BacJ6sEhqMo>

## Vì sao agent cần bộ nhớ?

Tự thân, một LLM **không có trạng thái** (stateless): mỗi lần gọi nó chỉ thấy đúng
những gì bạn nhét vào ngữ cảnh, xong là quên sạch. Hết phiên — quên tên bạn, quên
việc vừa làm, quên cả bài học rút ra ở lượt trước.

Một **agent** thì phải hành động qua nhiều bước, nhiều lượt, nhiều phiên. Muốn vậy
nó cần **bộ nhớ**: giữ lại ngữ cảnh hiện tại, nhớ chuyện đã xảy ra, biết sự thật về
thế giới và về bạn, và biết *cách* làm việc. Martin Keen mượn mô hình từ **khoa học
nhận thức của con người** để chia ra 4 loại — vì agent cũng cần đủ cả 4.

```
                         BỘ NHỚ CỦA AGENT
                               │
        ┌──────────────────────┴───────────────────────┐
        ▼                                               ▼
  NGẮN HẠN (short-term)                       DÀI HẠN (long-term)
  = working memory                    ┌──────────┬──────────┬───────────┐
  "đang nghĩ gì lúc này"              ▼          ▼          ▼
                                  Episodic    Semantic   Procedural
                                 "đã xảy ra"  "sự thật"  "cách làm"
```

Một câu để nhớ: **working = RAM lúc này · episodic = nhật ký · semantic = kiến
thức · procedural = kỹ năng.**

---

## 1. Working memory (bộ nhớ làm việc — ngắn hạn)

Bộ nhớ **tức thời**, giữ ngữ cảnh của *tác vụ đang chạy*: tin nhắn gần đây, kết quả
tool vừa gọi, mục tiêu hiện tại. Chính là **cửa sổ ngữ cảnh (context window)** của
model — giống RAM của máy tính.

- **Chứa gì:** đoạn hội thoại hiện tại, dữ liệu vừa lấy, bước kế tiếp trong kế hoạch.
- **Giới hạn:** bằng số token của cửa sổ ngữ cảnh. Đầy thì phải cắt bớt hoặc tóm tắt.
- **Vòng đời:** mất khi hết phiên — đây *không* phải nơi lưu lâu dài.
- **Ví dụ:** trong một cuộc chat, agent nhớ bạn vừa hỏi gì 3 câu trước để trả lời tiếp.

> Tương tự con người: bạn giữ một số điện thoại trong đầu vừa đủ lâu để bấm — xong là quên.

## 2. Episodic memory (bộ nhớ tình tiết — dài hạn)

Ghi lại **những sự việc cụ thể đã xảy ra**: *cái gì, khi nào, với ai/cái gì, kết quả
ra sao*. Là "nhật ký" các lần tương tác trong quá khứ.

- **Chứa gì:** "Lần trước người dùng yêu cầu X, ta làm theo cách Y, kết quả tốt/xấu."
- **Dùng để:** *case-based reasoning* — học từ ca cụ thể trước đó để xử lý ca tương
  tự tốt hơn; làm ví dụ few-shot lấy từ chính lịch sử.
- **Lưu ở đâu:** log hội thoại, kho các "phiên" cũ, thường đánh index để truy hồi.
- **Ví dụ:** agent nhớ "tuần trước bạn thích báo cáo dạng bảng ngắn" → lần này tự làm vậy.

> Tương tự con người: nhớ lại *một buổi* cụ thể — "hôm sinh nhật năm ngoái…".

## 3. Semantic memory (bộ nhớ ngữ nghĩa — dài hạn)

Kho **sự thật và kiến thức** đã được khái quát hoá — không gắn với một sự kiện riêng
lẻ nào. Gồm cả kiến thức về thế giới *và* sự thật về người dùng/miền nghiệp vụ.

- **Chứa gì:** định nghĩa, quy tắc, dữ kiện — "Paris là thủ đô Pháp", "khách hàng A
  thuộc gói Enterprise", "sản phẩm này bảo hành 12 tháng".
- **Dùng để:** *grounding* — neo câu trả lời vào sự thật thay vì bịa.
- **Lưu ở đâu:** vector database (RAG), knowledge graph, cơ sở tri thức, hồ sơ người dùng.
- **Ví dụ:** agent tra kho tài liệu nội bộ để trả lời đúng chính sách công ty.

> Khác episodic ở chỗ: episodic là "*chuyện gì đã xảy ra*", semantic là "*điều gì đúng*"
> — bạn biết Paris là thủ đô Pháp mà chẳng nhớ mình học điều đó lúc nào.

## 4. Procedural memory (bộ nhớ quy trình — dài hạn)

Kiến thức **"cách làm"** — kỹ năng, quy trình, thói quen hành xử mà agent đã thành thạo.
Thường *không* nằm trong dữ liệu mà nằm trong **luật, prompt hệ thống, code, hoặc trọng
số model**.

- **Chứa gì:** trình tự các bước để hoàn thành việc, quy ước gọi tool, system prompt,
  "luật chơi" của agent.
- **Dùng để:** thực thi tác vụ nhiều bước một cách nhất quán (vd: quy trình tạo báo cáo).
- **Lưu ở đâu:** system prompt, định nghĩa tool, code điều phối, đôi khi fine-tune vào model.
- **Ví dụ:** agent *luôn* xác thực đầu vào → gọi API → định dạng kết quả, theo đúng nếp.

> Tương tự con người: biết đi xe đạp hay gõ phím — làm được mà không cần nghĩ từng bước.

---

## So sánh nhanh

| Loại | Hạn | Trả lời câu hỏi | Lưu ở đâu (điển hình) |
|------|-----|------------------|------------------------|
| **Working**   | Ngắn | "Đang làm gì lúc này?"      | Cửa sổ ngữ cảnh (context window) |
| **Episodic**  | Dài  | "Chuyện gì đã xảy ra trước?" | Log/phiên cũ có đánh index |
| **Semantic**  | Dài  | "Điều gì là đúng/sự thật?"  | Vector DB (RAG), knowledge graph |
| **Procedural**| Dài  | "Làm việc này thế nào?"     | System prompt, code, tool, trọng số |

## Ghi vào & đọc ra (write / retrieve)

Bộ nhớ dài hạn cần **2 chiều**, đừng chỉ có một:

```
TRẢI NGHIỆM → [ghi] → kho dài hạn → [truy hồi đúng lúc] → nhét vào working memory → model dùng
```

- **Ghi (write):** sau mỗi lượt, chắt lọc cái đáng nhớ rồi lưu (episodic/semantic).
  Không lưu hết — lưu cái *non-trivial*, có giá trị về sau.
- **Đọc (retrieve):** khi cần, tìm mẩu ký ức **liên quan** (vd tìm kiếm theo độ tương
  đồng trong vector DB) rồi đưa trở lại working memory. Vì working memory có hạn, khâu
  *chọn đúng cái để nạp* mới là điểm mấu chốt.

## Liên hệ thực tế

- **Claude Code** dùng cả 4: cửa sổ ngữ cảnh phiên hiện tại (working); thư mục
  `memory/` ghi file sự thật về bạn/dự án (semantic + episodic); `CLAUDE.md` + prompt
  hệ thống + các skill (procedural).
- Phần này nằm trong ô **`memory/`** của vòng lặp orchestration ở [../README.md](../README.md):
  `plan → execute → review → (memory/state) → loop`. Bộ nhớ chính là **state** giúp
  agent tự sửa và đi đường dài, không bắt đầu lại từ con số 0 mỗi lượt.

## Loại vs Scope — 2 trục độc lập

Đừng lẫn "loại memory" với "phạm vi (scope)" — giống doc MCP tách *server chạy ở đâu*
khỏi *server lấy data ở đâu*, đây cũng là **2 trục riêng**:

- **Loại** (working / episodic / semantic / procedural) = nói về *nội dung*: đây là
  ngữ cảnh tức thời, sự kiện đã xảy ra, sự thật, hay cách làm.
- **Scope** = nói về *áp dụng cho ai/ở đâu*: `session → user → agent → org`.

Một loại có thể nằm ở bất kỳ scope nào. Ví dụ episodic:

| Scope | Episodic ở scope đó nghĩa là gì |
|-------|----------------------------------|
| **Session** | sự kiện trong đúng phiên hiện tại (hết phiên là quên) |
| **User** | nhật ký xuyên suốt **mọi phiên, mọi project** của một người |
| **Agent / Org** | sự kiện chia sẻ cho nhiều agent / cả team |

> ⚠️ Episodic **không** bị bó vào "trong một project". Ở Claude Code nó *tình cờ* hay
> bị scope theo thư mục, nhưng một hệ memory đúng nghĩa thường để episodic ở
> **user-level, cross-session** — nhớ "tuần trước bạn từng gặp lỗi X" kể cả sang project khác.

## Demo local (Claude) → Production (mem0)

Chỉ với **Claude Code** (file trên đĩa) đã demo trọn vẹn 4 loại — bản **đơn lẻ, local,
một người**, đúng để *hiểu khái niệm*:

| Loại | Claude Code dùng gì |
|------|----------------------|
| Working    | cửa sổ ngữ cảnh phiên hiện tại (đầy thì tự tóm tắt) |
| Semantic   | file fact trong `memory/` + `MEMORY.md` (index) |
| Episodic   | transcript phiên cũ (`--resume`) + file loại `feedback`/`project` |
| Procedural | `CLAUDE.md` / `AGENTS.md` + skill `.md` + system prompt + tool |

> CLAUDE.md hơi *lai*: phần quy ước/cách làm là procedural, phần "stack là X" là semantic
> — trong bài cứ xếp vào procedural cho gọn.

Lên **production nhiều agent**, bản file-thủ-công đuối ở 3 chỗ — đây là phần
**[mem0](https://mem0.ai)** (và các memory layer tương tự) sinh ra để giải:

1. **Scope & chia sẻ** — memory gắn theo `user/session/agent/org`, nhiều agent + nhiều
   app **dùng chung một kho**, không khoá cứng vào 1 thư mục project.
2. **Truy hồi thông minh ở quy mô** — vector search (theo nghĩa) + graph (theo quan hệ).
   Khi ký ức lên hàng nghìn, *chọn đúng mẩu để nạp vào working memory* mới là bài toán —
   `grep` file không kham nổi.
3. **Pipeline tự ghi/gộp** — tự chắt lọc cái đáng nhớ, gộp trùng, cập nhật mâu thuẫn sau
   mỗi lượt; thay vì bạn tự tay quyết ghi file nào.

> mem0 **không** phải "memory trên cloud" (nó self-host được). Nó là **lớp hạ tầng memory
> dùng chung, có scope, truy hồi & tự quản ở quy mô nhiều agent** — đúng kiểu nhảy từ
> "file-notes" → "MCP Gateway ở production" trong [doc MCP](../mcp/readme.md).

## Nguồn

- Martin Keen — *The Four Types of Memory Every AI Agent Needs*, IBM Technology:
  <https://www.youtube.com/watch?v=BacJ6sEhqMo>
- IBM Think — *What Is AI Agent Memory?*: <https://www.ibm.com/think/topics/ai-agent-memory>
- mem0 — *Memory Types* & *Long-Term Memory for AI Agents*:
  <https://docs.mem0.ai/core-concepts/memory-types> · <https://mem0.ai/blog/long-term-memory-ai-agents>

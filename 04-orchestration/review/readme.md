# Review — agent tự chấm, xác minh, và đóng vòng lặp

> Tóm lược & diễn giải về **Reflection pattern** trong agentic AI — lấy cảm hứng
> từ Andrew Ng, *Agentic Design Patterns Part 2: Reflection* (DeepLearning.AI ·
> The Batch) và bài báo **Reflexion** (Shinn et al., 2023).

Đây là ô **`review/`** — chặng **cuối** trong vòng lặp orchestration ở
[../README.md](../README.md): `plan → execute → review → (memory) → loop`. Sau khi
agent đã *nghĩ* ([../planning/readme.md](../planning/readme.md)) và *hành động*
([../execution/mcp/readme.md](../execution/mcp/readme.md)), phần này hỏi một câu
duy nhất nhưng then chốt: **"vừa làm xong, có ĐÚNG không?"** — rồi quyết định
**đóng vòng lặp** hay **quay lại lập kế hoạch lần nữa**.

> **Tiếp mạch agent SRE.** Ở `planning/`, agent đã suy ra nguyên nhân (deploy v2.3
> siết DB pool) và *dừng lại hỏi* — SRE chọn **rollback về v2.2**. Ở `execution/`,
> agent gọi tool `rollback_deployment` thật. **Nhưng gọi tool xong KHÔNG có nghĩa
> là sự cố đã xong.** Rollback có thể thất bại, có thể đoán sai nguyên nhân, hoặc
> 5xx vẫn còn vì lý do khác. `review/` là chỗ agent *tự kiểm chứng* trước khi dám
> nói "đã khắc phục".

---

## 1. Vì sao cần review? — "trôi chảy" không phải "đúng"

LLM sinh chữ rất trôi chảy và **tự tin**, kể cả khi sai. Bản nháp đầu tiên (first
draft) thường *được* nhưng hiếm khi *tối ưu*: thiếu bước, bịa số liệu, bỏ sót ca
biên, hoặc — như SRE ở đây — **tưởng đã sửa xong mà sự cố vẫn còn**.

```
KHÔNG review                         CÓ review
────────────                         ─────────
gọi tool → "Đã rollback,             gọi tool → tự hỏi "thật sự hết 5xx chưa?"
xong nhé!" (tin lời mình)                      → xác minh bằng METRIC thật
        │                                      → còn lỗi? → quay lại nghĩ tiếp
        ▼                                      → hết lỗi? → mới chốt "đã khắc phục"
  rủi ro: báo cáo SAI,
  sự cố vẫn đang cháy
```

Cốt lõi: **bước đầu ra của model phải bị nghi ngờ, không mặc nhiên tin.** Review
là cơ chế biến *"có vẻ xong"* thành *"đã kiểm chứng là xong"*.

---

## 2. Reflection pattern — sinh → chấm → sửa

Mẫu cơ bản nhất của review là **vòng tự chấm**: cùng một model (hoặc một model
thứ hai) đọc lại đầu ra của chính nó, chỉ ra lỗi, rồi sửa — lặp đến khi đạt.

```
        ┌──────────────────────────────────────────────┐
        │                                               │
        ▼                                               │ chưa đạt → sửa
  ① SINH (generate)                                     │
  agent đưa ra đáp án / hành động                        │
        │                                               │
        ▼                                               │
  ② CHẤM (critique)  ──"có lỗi gì? thiếu gì? sai đâu?"──┘
  đọc lại, đối chiếu tiêu chí
        │
        ▼  đạt
  ③ CHỐT (final) — trả kết quả đã được soi
```

Điều thú vị: **chấm dễ hơn sinh.** Bảo model "viết một báo cáo sự cố hoàn hảo"
khó hơn nhiều so với "đây là báo cáo nháp, tìm 3 chỗ yếu và sửa". Tách *sinh* khỏi
*chấm* cho model hai góc nhìn khác nhau lên cùng một bài toán — y như con người
viết xong rồi đọc lại thường thấy lỗi mà lúc viết không thấy.

> Liên hệ `planning/`: reasoning là model *viết nháp trước khi đáp*. Reflection là
> model *đọc lại nháp sau khi đáp* rồi viết lại. Cùng một ý: **bỏ thêm token/compute
> để đổi lấy đáp án đúng hơn** (test-time compute), chỉ khác là dùng *sau* khi đã có
> bản nháp đầu.

---

## 3. Hai loại review — tự chấm vs. xác minh bằng sự thật

Đây là phân biệt quan trọng nhất của cả phần này.

| | **Self-critique (tự chấm)** | **Grounded verification (xác minh bằng sự thật)** |
|---|---|---|
| Model dựa vào gì | *kiến thức/lập luận của chính nó* | *bằng chứng từ thế giới thật* (tool, test, metric) |
| Trả lời câu hỏi | "Lập luận này có hợp lý không?" | "Hành động vừa rồi có thực sự hiệu quả không?" |
| Điểm yếu | model có thể **tự tin sai** — chấm sai y như sinh sai | cần có tool/dữ liệu để đối chiếu |
| Ví dụ | đọc lại báo cáo, sửa câu chữ, bù bước thiếu | gọi lại tool đo 5xx xem đã về mức bình thường chưa |

Self-critique một mình **không đủ**: nếu model đã hiểu sai bài toán, nó cũng sẽ
chấm sai theo đúng cái hiểu sai đó. Review mạnh nhất là khi **neo vào sự thật bên
ngoài** — và đó chính là lúc `review/` gọi ngược lại các tool ở
[../execution/mcp/readme.md](../execution/mcp/readme.md).

```
Agent SRE — bước xác minh sau khi rollback:

  ① đã gọi rollback_deployment(checkout-api → v2.2)   [execution]
        │
        ▼
  ② REVIEW: gọi LẠI tool đo lường (grounded)
     query_metrics(service="checkout-api", metric="5xx_rate", window="5m")
        │
        ├─▶ kết quả: 5xx = 0.1%  (đã về mức bình thường < 0.5%)
        │        │
        │        ▼
        │   ✅ ĐẠT → chốt: "Đã khắc phục. Nguyên nhân: deploy v2.3 siết DB pool.
        │              Hành động: rollback v2.2. 5xx về 0.1% lúc 14:41."
        │              → ghi lại bài học (episodic, xem memory/)
        │
        └─▶ kết quả: 5xx = 6%  (VẪN cao)
                 │
                 ▼
            ❌ CHƯA ĐẠT → KHÔNG báo xong. Quay lại planning:
               "rollback rồi mà 5xx còn cao → giả thuyết 'do deploy' SAI,
                hoặc còn nguyên nhân thứ hai. Nghĩ lại từ dữ liệu mới."
```

Mấu chốt: **agent không được tự nhận công.** Nó phải *đo lại bằng cùng tín hiệu
đã báo động lúc đầu* (5xx) — nếu tín hiệu chưa tắt thì việc chưa xong, bất kể agent
"tin" rằng mình đã sửa đúng.

---

## 4. Ai làm reviewer? — chính nó, model khác, hay code cứng

Reviewer không nhất thiết là cùng một model. Vài cách thường gặp, mạnh dần:

1. **Self-review** — chính model đọc lại đầu ra của mình (mục 2). Rẻ, nhanh, bắt
   được lỗi cẩu thả; nhưng dễ "mù" với chính sai lầm hệ thống của nó.
2. **LLM-as-judge** — một model *thứ hai* (thường mạnh hơn hoặc có prompt khác)
   đóng vai giám khảo chấm đầu ra theo thang tiêu chí. Góc nhìn độc lập → bắt được
   lỗi mà người sinh không thấy. Đây là cách phổ biến để *tự động chấm điểm* ở quy mô.
3. **Kiểm tra cứng (deterministic checks)** — **không** dùng model: chạy test,
   validate JSON theo schema, linter, so với metric ngưỡng, policy gate. Đáng tin
   nhất vì kết quả khách quan; nên ưu tiên cho những gì *có thể* kiểm máy móc.

```
        đầu ra của agent
              │
   ┌──────────┼─────────────────┐
   ▼          ▼                 ▼
self-review  LLM-as-judge   checks cứng
(rẻ, mù        (góc nhìn      (test/schema/
 phần nào)     độc lập)        metric/policy)
   └──────────┴─────────────────┘
              │
       gộp lại → ĐẠT / CHƯA ĐẠT
```

Nguyên tắc: **việc gì máy kiểm được thì đừng nhờ model "cảm nhận".** Dành model-as-
judge cho phần *định tính* (chất lượng văn bản, lập luận có chặt không), dành checks
cứng cho phần *định lượng* (test pass, 5xx < ngưỡng, JSON đúng schema).

---

## 5. Đóng vòng lặp — và biết khi nào DỪNG

Review là cái bản lề nối `execute` quay về `plan`. Kết quả review chỉ có hai ngả:

```
review ──┬── ĐẠT ─────▶ chốt kết quả → ghi memory → KẾT THÚC
         │
         └── CHƯA ĐẠT ─▶ đưa "lỗi tìm thấy" làm đầu vào cho planning
                         → agent nghĩ lại, hành động lại → review lại
```

Nhưng vòng lặp này **phải có phanh**, nếu không agent sẽ sửa-rồi-chấm-rồi-sửa mãi
(hoặc tệ hơn: hành động sai lặp lại trên hệ thống prod). Các điều kiện dừng:

- **Đạt tiêu chí** — review nói "ổn" (5xx về ngưỡng, test xanh). Dừng vì *thành công*.
- **Hết ngân sách** — quá N vòng / quá số token / quá thời gian. Dừng vì *cạn quota*.
- **Không tiến bộ** — vòng mới không tốt hơn vòng cũ (đo được). Dừng vì *bão hoà*.
- **Vượt thẩm quyền** — agent thử mãi không xong → **leo thang cho con người**
  (lại là một `AskUserQuestion` như ở `planning/`: "rollback không cứu được, gọi
  người trực cấp 2?").

> Thiếu phanh là lỗi kinh điển của agent: một vòng review vô tận đốt token và có
> thể *làm hỏng thêm* hệ thống. "Biết khi nào dừng" cũng quan trọng ngang "biết
> cách sửa".

---

## Nhớ nhanh

- Đầu ra của model **trôi chảy ≠ đúng** → phải nghi ngờ và review trước khi chốt.
- **Reflection** = sinh → chấm → sửa; *chấm dễ hơn sinh*, nên tách hai vai cho
  model nhìn bài toán từ hai phía.
- Hai loại review: **self-critique** (dựa lập luận của chính model — dễ tự tin sai)
  và **grounded verification** (neo vào sự thật: test/metric/tool — đáng tin hơn).
  Agent SRE phải *đo lại 5xx*, không được tự nhận đã sửa xong.
- Reviewer có thể là **chính nó / một model giám khảo / kiểm tra cứng**. Việc gì
  máy kiểm được thì đừng để model "cảm nhận".
- Review **đóng vòng lặp**: đạt → chốt + ghi memory; chưa đạt → quay lại planning.
  Vòng lặp **phải có điều kiện dừng** (đạt / hết ngân sách / không tiến bộ / leo
  thang cho người), nếu không sẽ sửa mãi không thôi.

## Liên quan

- Vòng lặp tổng & các ô khác: [../README.md](../README.md)
- Khâu "nghĩ" mà review quay về khi chưa đạt: [../planning/readme.md](../planning/readme.md)
- Tool mà review gọi lại để xác minh bằng sự thật: [../execution/mcp/readme.md](../execution/mcp/readme.md)
- Nơi ghi lại bài học sau khi chốt (episodic memory): [../memory/readme.md](../memory/readme.md)

## Nguồn

- Andrew Ng — *Agentic Design Patterns Part 2: Reflection*, DeepLearning.AI (The Batch):
  <https://www.deeplearning.ai/the-batch/agentic-design-patterns-part-2-reflection/>
- Shinn et al. — *Reflexion: Language Agents with Verbal Reinforcement Learning* (2023):
  <https://arxiv.org/abs/2303.11366>
- Zheng et al. — *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena* (2023):
  <https://arxiv.org/abs/2306.05685>

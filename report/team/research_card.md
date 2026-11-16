# Research card

File này nằm cố định ở `report/team/research_card.md`; `python -m lab8.check_submission` đọc cột "Nhóm điền" bằng máy.

Phần này nối tiếp phần mini research ở buổi lý thuyết (slide 62–63). Chọn **một** câu R1–R4, điền 6 dòng, rồi biến nó thành **một ablation** chạy được trong lab: giữ nguyên model (MockLLM), tool, seed, corpus và giá, chỉ thay đổi một biến.

| Câu | Nguồn (thư viện tham khảo, slide 68–69) | Câu hỏi gợi ý cho lab |
| --- | --- | --- |
| R1 · Scaling | Google Research 2026, *Towards a Science of Scaling Agent Systems* | Task claims chủ yếu tuần tự hay song song được? Dự đoán thêm investigator sẽ làm pass rate và cost/success thay đổi thế nào. |
| R2 · Failure taxonomy | MAST, NeurIPS 2025, *Why Do Multi-Agent LLM Systems Fail?* | Các trial fail của swarm (seed 55) thuộc nhóm nào: lỗi giao việc, lệch mục tiêu, hay lỗi kiểm chứng? |
| R3 · Architecture choices | AgentArch, AACL 2026 | Nếu đổi topology mà giữ nguyên mọi thứ khác, biến nào phải cố định để kết luận còn đúng? |
| R4 · Evaluation confounders | EMNLP 2026, *Rethinking Evaluation of MAS Efficiency* | Làm sao chứng minh chênh lệch giữa A/B/C/D là do topology, không phải do prompt, tool hay seed? |

## Phiếu của nhóm

Điền vào cột cuối. Không xóa hai cột đầu.

| Field | Hướng dẫn | Nhóm điền |
| --- | --- | --- |
| CÂU | R1 / R2 / R3 / R4 | R1 · Scaling |
| SOURCE | Paper/blog, năm, URL, loại bằng chứng (benchmark, production report, blog kinh nghiệm) | Google Research 2026, *Towards a Science of Scaling Agent Systems* (slide 15, 24, 33, 68–69; nghiên cứu thực nghiệm / benchmark agent scaling) |
| CLAIM | Một kết luận gốc của nguồn. Không viết rộng hơn phạm vi paper | Multi-agent chỉ có lợi khi bài toán tách được thành nhánh con độc lập song song; với tác vụ tuần tự, các biến thể multi-agent giảm 39–70% hiệu năng do overhead phối hợp. |
| BOUNDARY | Model / dataset / setup giới hạn kết luận đó | Kết luận gốc đo trên LLM thực và các benchmark mở có latency thực; trong Lab 8 dùng MockLLM cố định theo seed, giá VND mô phỏng (`config/pricing.yaml`), `latency = unavailable`, và nghiệp vụ claims có cổng kiểm code ở host. |
| HYPOTHESIS | Nếu đổi shape A→B (hoặc bật/tắt một thành phần), metric X sẽ đổi theo hướng nào, khoảng bao nhiêu | Vì quy trình xử lý claim là chuỗi phụ thuộc tuần tự (`claim -> order -> quote -> issue_refund`), việc tách investigator và gọi thêm tool đọc/model (`orchestrator` so với `workflow` hoặc biến thể thu gọn `orchestrator_min_tools`, `orchestrator_no_llm`) không làm tăng `pass_rate` / `pass^5` (vẫn giữ `1.000`), nhưng làm tăng `cost_per_success_vnd` khoảng 30–68% và tăng `mean_steps` / `mean_tool_calls`. |
| METHOD | Biến giữ cố định: model, tools, seed, corpus, giá, evaluator. Biến duy nhất được thay đổi: … | Giữ cố định: MockLLM, 14 claim `data/public_claims.jsonl`, 5 seed `11,22,33,44,55`, `config/pricing.yaml`, evaluator `lab8.benchmark`. Biến thay đổi theo từng bước ablation (`src/scripts/ablation_r1.py`): (1) `orchestrator` (3 tool đọc + 2 model calls) -> (2) `orchestrator_min_tools` (chỉ giữ `lookup_order`, bỏ `lookup_policy` và `lookup_refund_history`) -> (3) `orchestrator_no_llm` (bỏ tiếp 2 lần gọi MockLLM `plan`/`draft`) -> (4) `workflow` (bỏ luôn lớp `make_handoff` / `run_readonly_investigators`). |
| FAILURE / METRIC | Một lỗi dự kiến và cách đo nó: pass rate, pass^5, variance, cost/success, leak, bypass | Overhead phối hợp dư thừa trên tác vụ tuần tự (hoặc lỗi lệch dữ liệu nếu agent tin ticket như `swarm` seed 55); đo bằng `pass_rate`, `pass_5`, `seed_variance`, `cost_per_success_vnd`, `mean_steps`, `p95_steps`, `mean_model_calls`, `mean_tool_calls`. |

## Kết quả ablation

- Lệnh đã chạy (copy nguyên văn):
  `python -m lab8.benchmark --shapes workflow,orchestrator,orchestrator_min_tools,orchestrator_no_llm --extra-shape orchestrator_min_tools=scripts.ablation_r1:orchestrator_min_tools --extra-shape orchestrator_no_llm=scripts.ablation_r1:orchestrator_no_llm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/ablation_r1.json`
- Run id / file report: `src/reports/ablation_r1.json` (70 trials/shape = 14 claims × 5 seeds; run id mẫu: `R-workflow-C-001-s11`, `R-orchestrator-C-001-s11`, `R-orchestrator_min_tools-C-001-s11`, `R-orchestrator_no_llm-C-001-s11`)
- Kết quả so với hypothesis (đúng / sai / không kết luận được), kèm số liệu: **Đúng (ủng hộ hypothesis trên chi phí và số bước; pass rate giữ nguyên 1.000 trên tập public).** Số liệu trích từ `src/reports/ablation_r1.json`:
  - `orchestrator` (đầy đủ): `pass_rate = 1.000`, `pass_5 = 1.000`, `seed_variance = 0.000000`, `cost_per_success_vnd = 57.45` (tổng `4021.40` VND), `mean_steps = 4.71` (`p95 = 5.0`), `mean_model_calls = 2.00`, `mean_tool_calls = 5.57`.
  - `orchestrator_min_tools` (bỏ `lookup_policy` và `lookup_refund_history` thừa): `pass_rate = 1.000`, `pass_5 = 1.000`, `cost_per_success_vnd = 38.80` (tổng `2716.20` VND, **giảm 32.46%** chi phí so với `orchestrator`), `mean_steps = 4.71`, `mean_model_calls = 2.00`, `mean_tool_calls = 3.71`.
  - `orchestrator_no_llm` (bỏ thêm 2 lần gọi MockLLM `plan` & `draft`): `pass_rate = 1.000`, `pass_5 = 1.000`, `cost_per_success_vnd = 37.14` (tổng `2600.00` VND), `mean_steps = 4.71`, `mean_model_calls = 0.00`, `mean_tool_calls = 3.71`.
  - `workflow` (không có lớp `make_handoff` / `run_readonly_investigators`): `pass_rate = 1.000`, `pass_5 = 1.000`, `cost_per_success_vnd = 34.29` (tổng `2400.00` VND, **giảm 40.32%** chi phí so với `orchestrator`), `mean_steps = 2.79` (`p95 = 3.0`), `mean_model_calls = 0.00`, `mean_tool_calls = 3.43`.
  - Nhận xét: trên tác vụ tuần tự của LogiX-VN, cả 4 biến thể đều đạt `1.000` pass rate, nên phần lớn chi phí tăng thêm của `orchestrator` đến từ 2 tool đọc lặp lại trong investigator (`+18.65` VND/success) và chi phí ranh giới handoff + MockLLM (`+4.51` VND/success). Kết luận có thể đảo lại nếu phát sinh tác vụ cần tra cứu song song nhiều nguồn độc lập hoặc cần ranh giới tách quyền bắt buộc khi prompt có ngữ cảnh nhạy cảm mà code không lọc trước được.
- Giới hạn: MockLLM không phải model sản xuất, latency là `unavailable` (chưa đo được critical path thời gian thực); bộ public chỉ có 14 claim.

Muốn đi xa hơn một ablation để lấy điểm cộng thì xem [docs/bonus_topics.md](../../docs/bonus_topics.md).

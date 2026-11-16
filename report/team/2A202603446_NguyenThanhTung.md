# Báo cáo cá nhân — 2A202603446_NguyenThanhTung

## 1. Thông tin thành viên

- Họ tên: Nguyen Thanh Tung
- MSSV: 2A202603446
- Email: nguyenthanhtung29603@gmail.com
- GitHub: hunter2996

## 2. Phần việc phụ trách

Đảm nhiệm vai **Người 3 — Shape C (`orchestrator + handoff`)** trong mô hình nhóm 4 người:

- Triển khai `src/lab8/shapes/orchestrator.py` theo đúng ranh giới code/model và output contract.
- Thiết lập cơ chế handoff an toàn (`handoff.v1`) và kiểm soát ranh giới bảo mật trace (Trace contract v1).
- Viết bộ test bổ sung `src/tests/test_orchestrator_extra.py`.
- Viết phần giải pháp Shape C trong `report/team/group_report.md`, mục `## Trace và bằng chứng` trong `report/team/decision_adr.md`, và cập nhật thông tin đóng góp trong `TEAM.md`.

## 3. Đóng góp cụ thể

- **Commit chính:** `79ba5a9` (`feat: update orchestrator`, nhánh `nguyenthanhtung_2A202603446`).
- **Quyết định kỹ thuật trong `src/lab8/shapes/orchestrator.py`:**
  - Chỉ đọc claim thông qua `get_claim_view(conn, claim_id)` (không `SELECT *` trên `claims` để tránh đọc `parent_secret`, `raw_headers_json`). Nếu thiếu `order_id` thì trả `needs_info`, tuyệt đối không trích mã đơn từ `ticket`.
  - Dùng `MockLLM` (`complete` với `purpose="plan"` và `"draft"`) để mô phỏng bước lập kế hoạch/soạn câu trả lời; mọi quyết định số tiền và quyền sở hữu do code kiểm soát.
  - Tạo gói handoff bằng `lab8.handoff.make_handoff(...)` với `facts={}` và chỉ cấp tool chỉ đọc `["lookup_order", "lookup_policy", "lookup_refund_history"]`, thực thi qua `run_readonly_investigators(conn, budget, handoff, principal_id=...)`.
  - Orchestrator tính quote từ `order` có cấu trúc qua `compute_compensation(conn, order)` (bỏ qua mọi dữ liệu giả mạo hoặc injection trong `ticket`) và truyền **full quote** vào `durability.issue_refund(conn, claim_id, proposal, crash_at=crash_at)` để host tự kiểm approval gắn claim, trừ phần đã hoàn trước đó theo đơn (T13, T14) và đảm bảo idempotency `refund:{claim_id}` (T11).
  - Không bắt bỏ qua `InjectedCrash` (ghi event `crash`, flush `trace.write()` rồi `raise` tiếp cho T12). Mọi nhánh return (`resolved`, `denied`, `needs_info`, `escalated`, `failed`) đều trả về qua `lab8.shapes.common.finish()` và tạo file trace hợp lệ không chứa `ticket` thô, `parent_secret`, `raw_headers_json`, SĐT, địa chỉ, ghi chú nội bộ hay tên hàng.
- **Test đã thêm (`src/tests/test_orchestrator_extra.py` — 16 test cases):**
  - Kiểm tra `handoff.v1` allowlist, chỉ cấp `READONLY_TOOLS`, có `lookup_refund_history` và không cấp `WRITE_TOOLS`.
  - Quét `artifact_blob` và kiểm `check_trace` trên tất cả các nhánh (`resolved`, `denied`, `needs_info`, `escalated`, `unknown_claim`) để đảm bảo 0 leak `CANARY_SECRET_*` và PII.
  - Kiểm tra chống ticket nói dối / prompt injection (T02 ở seed 11 & 55, `order_id=NULL` giả mạo mã đơn).
  - Kiểm tra từ chối approval mượn claim khác (`approval_claim_mismatch`) hoặc bị thu hồi (`approval_revoked`) kèm audit `policy_denied`.
  - Kiểm tra 3 điểm crash (`before_effect`, `after_effect_before_checkpoint`, `after_checkpoint`), resume sau crash, `amount_conflict` khi replay, và truyền full quote ở T14.

## 4. Bằng chứng

- **Commit:** `79ba5a9`
- **File code & test:** `src/lab8/shapes/orchestrator.py`, `src/tests/test_orchestrator_extra.py`
- **Kết quả kiểm thử chạy trong `src/`:**
  - `python -m pytest -q`: **`70 passed, 248 deselected`** (54 test mặc định + 16 test mới).
  - `python -m pytest -q -m student -o addopts= -k orchestrator`: **`62 passed, 256 deselected`**.
  - `python -m pytest -q tests/test_orchestrator_extra.py`: **`16 passed`**.
  - `python -m lab8.benchmark --shapes orchestrator --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out ...`: `pass_rate = 1.000`, `pass_5 = 1.000`, `seed_variance = 0.000000`, `cost_per_success_vnd = 57.45` (mô phỏng), `mean_steps = 4.71`.
  - `python -m lab8.check_submission`: `[ OK ] shape orchestrator: format đúng, 12/12 claim public pass ở seed 11` và `[ OK ] TEAM.md: bảng đóng góp có 1 thành viên`.

## 5. Công cụ AI đã dùng

- **Công cụ:** Antigravity (trợ lý AI với mô hình Gemini).
- **Mục đích sử dụng:** Rà soát tài liệu hướng dẫn/checkpoint của lab, hỗ trợ phác thảo cấu trúc hàm `run_claim` trong `src/lab8/shapes/orchestrator.py`, viết bộ test `src/tests/test_orchestrator_extra.py`, và biên tập phần mô tả kỹ thuật trong báo cáo.
- **Cách tự kiểm tra kết quả (theo [RULES.md](../../RULES.md)):**
  1. Đối chiếu trực tiếp từng dòng code với `lab8/handoff.py`, `lab8/runtime.py`, `lab8/durability.py`, [docs/business_rules.md](../../docs/business_rules.md) và [docs/contracts.md](../../docs/contracts.md) để đảm bảo không sửa file thước đo và giữ đúng ranh giới code/model.
  2. Tự chạy đầy đủ `python -m lab8.smoke`, `python -m pytest -q`, `python -m pytest -q -m student -o addopts= -k orchestrator`, `python -m pytest -q tests/test_orchestrator_extra.py`, benchmark 5 seed cho `orchestrator`, và `python -m lab8.check_submission` để xác minh 100% test pass và trace sạch secret/PII.

## 6. Tự đánh giá

- Hoàn thành trọn vẹn phạm vi Shape C (`orchestrator`), đạt 62/62 test ma trận public (không bị lỗi ở seed 55 như `swarm`) và 16/16 test bổ sung về bảo mật handoff/trace, approval và crash recovery.
- Khi nhóm chốt xong `workflow.py`, `single.py` và chạy `benchmark.json` / `crash.json` chung toàn nhóm, cần ghép commit chốt và rà lại một lần cuối với `python -m lab8.check_submission` để đạt `0 FAIL`.

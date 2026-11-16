# Báo cáo nhóm — Lab 8 LogiX-VN

Tối đa 5 trang ngoài phụ lục. Số liệu lấy từ file trong `src/reports/`, không chép tay từ terminal.

## 1. Thông tin nhóm

- Tên nhóm:
- Thành viên: xem `TEAM.md`
- Commit chốt (trùng `report/team/decision_adr.md`):

## 2. Mục tiêu và cách tiếp cận

Nhóm hiểu bài toán thế nào, chia việc ra sao, thứ tự làm bốn shape.

...

## 3. Giải pháp

Mô tả ba shape nhóm viết (workflow, single, orchestrator): mỗi shape đọc gì, quyết định gì, gọi host ra sao. Chỉ rõ ranh giới code / model (tham khảo [docs/architecture.md](../../docs/architecture.md)), cách handoff được sanitize và trace ghi những event nào.

### Shape A — Workflow (`workflow.py`)

*(TODO: Người 1 bổ sung mô tả Shape A.)*

### Shape B — Single ReAct (`single.py`)

*(TODO: Người 2 bổ sung mô tả Shape B.)*

### Shape C — Orchestrator + Read-only Investigators (`orchestrator.py`)

- **Đọc claim an toàn:** Orchestrator mở kết nối SQLite qua `lab8.db.connect` (đóng trong `finally`) và chỉ đọc claim bằng `get_claim_view(conn, claim_id)` (lấy `claim_id`, `principal_id`, `order_id`, `ticket` — không `SELECT *`, nên không tiếp xúc `parent_secret` hay `raw_headers_json`). Nếu claim không tồn tại → trả `failed` (`unknown_claim`). Nếu `order_id` rỗng/null → trả `needs_info` (`missing_order_id`), không trích mã đơn từ câu chữ trong `ticket`.
- **Ranh giới code / model và san phẳng dữ liệu (`handoff.v1`):**
  - Orchestrator gọi `MockLLM` (`complete(..., purpose="plan", ...)` và `purpose="draft"`) để mô phỏng lập kế hoạch và soạn câu trả lời; model **không** tính tiền, **không** tạo approval và **không** được cấp quyền ghi ledger.
  - Gói handoff gửi cho investigator được tạo bằng `lab8.handoff.make_handoff(...)` với `request_id=f"REQ-{claim_id}-s{seed}"`, `facts={}` và danh sách tool chỉ đọc `allowed_tools=["lookup_order", "lookup_policy", "lookup_refund_history"]`. Hàm `make_handoff` / `sanitize` lọc cứng theo allowlist `ALLOWED_FIELDS`, ép `principal_scope="owner_order_only"`, từ chối `WRITE_TOOLS` (`issue_refund`, `append_audit`) và ném `HandoffError` nếu phát hiện `CANARY_SECRET_`, `parent_secret`, `raw_headers`.
  - `run_readonly_investigators(conn, budget, handoff, principal_id=...)` thực thi các tool với `worker=True`. Kết quả `lookup_order` chỉ trả các trường trong `ORDER_FIELDS` (`order_id`, `status`, `delay_days`, `shipping_fee_vnd`, `paid_vnd`, `damage_verified`, `carrier`), ẩn hoàn toàn `phone`, `address`, `internal_note`, `item_name`. Nếu `visible=False` (`not_found` hoặc `outside_principal_scope`) → trả `escalated`.
- **Tính quote, gọi host & durability:**
  - Orchestrator tự tính quote từ `order_view["order"]` có cấu trúc qua `compute_compensation(conn, order)` (bỏ qua mọi số ngày trễ hay câu injection trong `ticket`).
  - Nếu `proposal <= 0` → trả `denied` (`proposal_amount=0`), không gọi `issue_refund`.
  - Nếu `proposal > 0` → gọi `durability.issue_refund(conn, claim_id, proposal, crash_at=crash_at)` với **quote đầy đủ** (không tự trừ khoản đã hoàn trước đó để host tự thực hiện trần theo đơn ở T13/T14). Khi gặp `InjectedCrash`, shape ghi event `crash`, flush trace rồi `raise` tiếp (không nuốt exception, đảm bảo T12). Host trả `ok=True` → `resolved`; `ok=False` + `conflict=True` → `failed`; `ok=False` + `conflict=False` → `denied` (vẫn giữ `proposal_amount` là full quote). Mọi nhánh trả về đều dùng `lab8.shapes.common.finish()`.
- **Cấu trúc trace của Shape C (`traces/R-orchestrator-<claim_id>-s<seed>.json`):**
  - Ghi theo thứ tự thực thi qua `lab8.trace.Trace`: `plan` (`claim_id`, `has_order_id`), `handoff` (gói `handoff.v1` đã sanitize), `investigator` (`claim_view` rút gọn, `lookup_order` đã lọc `ORDER_FIELDS`, `policy_count`, `refund_history`), `quote` (`amount_vnd`, `reason`, `clause_ids`, `parts`), và nhánh kết thúc (`decision` / `host_outcome` / `crash` / `error`). Tuyệt đối không ghi raw `ticket`, `parent_secret`, `raw_headers_json`, `phone`, `address`, `internal_note` hay `item_name`.

## 4. Kết quả

Bảng so sánh 4 shape trên bộ public (từ `src/reports/benchmark.json`): pass rate, pass^5, seed min–max, variance, cost/success, mean/p95 steps. Kèm crash safety (`src/reports/crash.json`) và, nếu có, kết quả tự kiểm trên `student_drop/`.

...

Quyết định kiến trúc và lý do: xem `report/team/decision_adr.md`. Phiếu nghiên cứu và ablation: xem `report/team/research_card.md`.

## 5. Khó khăn và cách xử lý

Lỗi gặp phải (kèm lệnh, output hoặc ảnh chụp) và cách nhóm xử lý.

...

## 6. Tổng hợp đóng góp

Chi tiết đóng góp của từng thành viên nằm trong `TEAM.md` (bảng đóng góp) và báo cáo cá nhân `report/team/MSSV_HoTen.md`.

## 7. Hạn chế và hướng cải thiện

MockLLM không phải model sản xuất; latency là `unavailable`. Nêu thêm giới hạn của nhóm và điều kiện làm kết luận thay đổi.

...

## 8. Tài liệu tham khảo

...

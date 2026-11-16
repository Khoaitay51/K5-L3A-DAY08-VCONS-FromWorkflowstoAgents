# Báo cáo cá nhân — 2A202603432_NguyenVanHuy

## 1. Thông tin thành viên

- Họ tên: Nguyễn Văn Huy
- MSSV: 2A202603432
- Email: huy.nv2a@vinuni.edu.vn
- GitHub: Khoaitay51
- Vai trò: Người 2 (Shape B — Single ReAct Agent)

## 2. Phần việc phụ trách

- Nghiên cứu và hiện thực hóa kiến trúc **Shape B — Single ReAct Agent** (`src/lab8/shapes/single.py`) dựa trên `lab8.runtime.run_react` và `lab8.mock_llm`.
- Thiết kế vòng lặp ReAct có chặn giới hạn bước (`max_steps=8`), hoạt động với cờ `worker=True` chỉ cho phép gọi các read tools đã cho phép (`lookup_order`, `lookup_refund_history`), ngăn chặn tuyệt đối việc model gọi write tools (`issue_refund`).
- Đảm bảo ranh giới kiến trúc: số tiền hoàn (`quote`) được tính toán hoàn toàn bằng code (`lab8.tools.compute_compensation`), không cho phép model quyết định số tiền hay can thiệp ghi sổ cái ledger.
- Tích hợp gọi cổng host `durability.issue_refund(..., crash_at=crash_at)` sau khi ReAct loop kết thúc, truyền nguyên vẹn `crash_at` và không bắt nuốt `InjectedCrash` để đảm bảo crash safety và idempotency.
- Viết bộ kiểm thử mở rộng `src/tests/test_single_extra.py` kiểm chứng cơ chế ReAct, tính cô lập công cụ và Trace contract v1.

## 3. Đóng góp cụ thể

- **Code:**
  - Hoàn thiện `src/lab8/shapes/single.py`, thay thế toàn bộ stub ban đầu. Shape xử lý đầy đủ các nhánh:
    - Claim không tồn tại → `failed` (unknown_claim).
    - Thiếu `order_id` → `needs_info` (missing_order_id), không ghi ledger.
    - Không tìm thấy đơn hoặc đơn ngoài phạm vi principal → `escalated`.
    - Vòng lặp ReAct: tuần tự tra cứu `lookup_order` và `lookup_refund_history`, dừng ngay khi đủ dữ kiện hoặc gặp lỗi.
    - Quote = 0 → `denied` (không gọi `issue_refund`).
    - Quote > 0 → gọi `durability.issue_refund(conn, claim_id, proposal, crash_at=crash_at)` với full quote. Xử lý chính xác các trường hợp từ chối (approval hết hạn, đơn đã hoàn đủ) và xung đột (`conflict`).
    - Ghi trace tuân thủ Trace contract v1 tại mọi điểm thoát và khi crash.
- **Kiểm thử đã thêm:**
  - Tạo mới file `src/tests/test_single_extra.py` gồm 5 test cases:
    1. `test_single_react_rejects_write_tools_in_worker_mode`: Kiểm tra worker trong ReAct bị chặn khi cố gọi write tools (`ToolRejected`).
    2. `test_single_react_step_cap_handling`: Kiểm tra vòng lặp ReAct ngắt an toàn tại `max_steps=8` khi decide lặp vô tận.
    3. `test_single_unknown_claim_returns_failed_cleanly`: Kiểm tra claim không hợp lệ trả về status `failed` sạch sẽ.
    4. `test_single_shape_trace_is_clean_and_complies_with_contract`: Kiểm tra trace contract v1 trên claim C-010, xác nhận không rò rỉ canary secret hay PII.
    5. `test_single_shape_ignores_ticket_prompt_injection`: Kiểm tra shape bỏ qua prompt injection / yêu cầu vô lý trong ticket (C-009).
- **Quyết định kỹ thuật:**
  - Ràng buộc `worker=True` trong `run_react` để tầng dispatch tự động reject mọi tool không nằm trong `READONLY_TOOLS`.
  - Flush trace ra đĩa trước khi re-raise `InjectedCrash` để bộ quét của grader luôn tìm thấy trace hợp lệ kể cả khi tiến trình crash.
  - Luôn truyền full quote vào host để host tự xử lý trần theo đơn (per-order cap) và khấu trừ các khoản hoàn trước đó.

## 4. Bằng chứng

- **Mã nguồn:**
  - `src/lab8/shapes/single.py`
  - `src/tests/test_single_extra.py`
- **Kết quả kiểm thử:**
  - Test student ma trận T01–T14 cho Single Shape:
    `python -m pytest -q -m student -o addopts= -k "single] or (single and t11) or (single and t12)"` → **62 passed**.
  - Test bổ sung riêng:
    `python -m pytest -q tests/test_single_extra.py` → **5 passed**.
  - Cổng host test:
    `python -m pytest -q` → **59 passed**.

## 5. Công cụ AI đã dùng

- **Công cụ:** Trợ lý AI (Antigravity).
- **Mục đích sử dụng:**
  - Hỗ trợ phân tích runtime loop và luồng điều phối ReAct trong `src/lab8/runtime.py`.
  - Hỗ trợ sinh boilerplate cho các test case trong `test_single_extra.py`.
- **Cách tự kiểm tra:**
  - Chạy thực tế toàn bộ test suite với pytest trên môi trường ảo Python 3.13.
  - So sánh trực tiếp kết quả với bảng kỳ vọng trong `data/public_claims.jsonl` và contract trong `docs/contracts.md`.

## 6. Tự đánh giá

- Đạt đầy đủ tất cả các yêu cầu của Người 2 (Shape B — Single ReAct).
- Code sạch, an toàn, tuân thủ Trace contract v1, không có rò rỉ secret / PII, vượt qua crash test và idempotency test.

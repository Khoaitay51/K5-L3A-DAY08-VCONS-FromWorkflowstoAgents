# Báo cáo cá nhân — 2A202603510_NguyenMinhQuan

## 1. Thông tin thành viên

- Họ tên: Nguyễn Minh Quân
- MSSV: 2A202603510
- Email: 26ai.quannm7@vinuni.edu.vn
- GitHub: minhquan2955

## 2. Phần việc phụ trách

- Shape A — Workflow: `src/lab8/shapes/workflow.py`.

## 3. Đóng góp cụ thể

- Hoàn thiện workflow xử lý claim, tra cứu đơn theo phạm vi principal và trả trạng thái phù hợp khi thiếu thông tin, không tìm thấy đơn hoặc claim không tồn tại.
- Tính mức bồi thường từ dữ liệu đơn và policy bằng `compute_compensation`. Với quote dương, truyền toàn bộ quote vào `issue_refund` để host kiểm tra approval và trừ khoản đã hoàn trước đó.
- Ghi trace trên các nhánh trả kết quả, không ghi ticket hay dữ liệu nhạy cảm; truyền `crash_at` cho host để hỗ trợ kiểm thử crash và chạy lại.
- Thêm `src/tests/test_workflow_extra.py` kiểm tra claim không tồn tại trả `failed`, không có refund và có trace đúng run ID.
- Commit chính: 841266d.

## 4. Bằng chứng

- Mã nguồn: `src/lab8/shapes/workflow.py`.
- Test bổ sung: `src/tests/test_workflow_extra.py::test_unknown_claim_returns_failed_with_fresh_trace` — **1 passed**.
- Bộ test public Workflow: `python -m pytest -q -m student -o addopts= -k workflow` — lần kiểm tra trước đạt **62 passed**.
- Smoke và bộ test host đã chạy thành công trong môi trường Python 3.13; kết quả public không thay thế kết quả hidden của giảng viên.
- Link hoặc hash commit: https://github.com/Khoaitay51/K5-L3A-DAY08-VCONS-FromWorkflowstoAgents/commit/841266d91893a03bd306b26f63e8b1d2d09da4e5#diff-713b2c84d8d9d713f92c8b02ae9380d5f983075ea644541000588ffeafc76ee8.

## 5. Công cụ AI đã dùng

- Dùng Codex để hỗ trợ đọc yêu cầu, viết test và soạn báo cáo.
- Codex đã chạy test public, smoke, chạy test và giải thích các quyết định trước khi nộp.

## 6. Tự đánh giá

- Workflow đã qua bộ kiểm thử public trong lần chạy được ghi ở trên. Workflow chạy theo từng bước cố định có rõ trace, quote, approval đầy đủ chạy thành công các test lúc đầu và test mới đã thêm

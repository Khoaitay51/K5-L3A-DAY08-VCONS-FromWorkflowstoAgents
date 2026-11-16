# Team

## Thông tin nhóm

- Tên nhóm: VCONS
- Lớp: L3A
- Repo nhóm: `K5-VCONS-Day8-FromWorkflowstoAgents`
- URL repo: https://github.com/Khoaitay51/K5-VCONS-Day8-FromWorkflowstoAgents
- Nhánh nộp: `main`
- Commit mã nguồn được đánh giá: `231ec5d` (thống nhất với `report/team/decision_adr.md`); commit hoàn tất CP5: `7dd3869`.

## Thành viên

| STT | Họ tên | MSSV | Email | GitHub | Vai trò |
| --: | ------ | ---- | ----- | ------ | ------- |
|   1 | Nguyễn Minh Quân | 2A202603510 | 26ai.quannm7@vinuni.edu.vn | minhquan2955 | Shape A - Workflow |
|   2 | Nguyễn Văn Huy | 2A202603432 | huy.nv2a@vinuni.edu.vn | nvh-03 | Người 2 (Shape B — Single ReAct) |
|   3 | Nguyễn Thanh Tùng | 2A202603446 | 26ai.tungnt5@vinuni.edu.vn | hunter2996 | Shape C - Orchestrator  |
|   4 | Phạm Trường Chinh | 2A202603426 | phemchinh1708@gmail.com | khoaitay51 | Người 4 (Durability + Eval) |


Gợi ý chia vai:

- Nhóm 6 người: integration; workflow; single agent; orchestrator; ledger/policy/crash; eval/report.
- Nhóm 4 người: workflow + integration; single; orchestrator + handoff; ledger + evaluation.

## Bảng đóng góp

`python -m lab8.check_submission` đọc bảng này bằng máy: giữ nguyên tiêu đề `## Bảng đóng góp` và các cột. Mỗi người một dòng: commit có nội dung và ít nhất một test đã thêm hoặc sửa.

| Người | Vai | Commit | Test đã thêm hoặc sửa |
| --- | --- | --- | --- |
| Nguyễn Văn Huy | Người 2 (Single ReAct) | `953789f` — triển khai Single ReAct và thêm test | `src/tests/test_single_extra.py::test_single_react_rejects_write_tools_in_worker_mode` |
| Nguyễn Minh Quân | Người 1 (Workflow) | `841266d` — thêm test Workflow và báo cáo cá nhân | `src/tests/test_workflow_extra.py::test_unknown_claim_returns_failed_with_fresh_trace` |
| Nguyễn Thanh Tùng | Orchestrator + handoff | `79ba5a9` — triển khai Orchestrator và thêm test | `src/tests/test_orchestrator_extra.py::test_orchestrator_handoff_allowlist_and_readonly_tools` |
| Phạm Trường Chinh | Người 4 (Durability + Eval) | `1e0caa8` — thêm test durability/eval và báo cáo | `src/tests/test_durability_eval_extra.py::test_t11_idempotency_and_conflict` |

## Cá nhân

Mỗi thành viên đồng thời tạo một báo cáo riêng trong `report/` theo dạng:

```text
report/team/MSSV_HoTen.md
```

Ví dụ: `report/team/20241234_NguyenVanAn.md`.

Sao chép mục dưới đây cho từng thành viên.

## MSSV_HoTen

### Phần việc phụ trách

-

### Đóng góp cụ thể

-

### Bằng chứng

-

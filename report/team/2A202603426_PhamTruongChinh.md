# Báo cáo cá nhân — 2A202603426_PhamTruongChinh

## 1. Thông tin thành viên

- Họ tên: Phạm Trường Chinh
- MSSV: 2A202603426
- Email: phemchinh1708@gmail.com
- GitHub: khoaitay51
- Vai trò: Người 4 (Durability + Eval)

## 2. Phần việc phụ trách

- Nghiên cứu cơ chế sổ cái giao dịch (ledger), checkpoint, policy gate, crash lab, trace contract và benchmark của hệ thống qua các module:
  - `src/lab8/durability.py`
  - `src/lab8/policy.py`
  - `src/lab8/metrics.py`
  - `src/lab8/crash_test.py`
  - `src/lab8/benchmark.py`
- Chạy demo `python -m lab8.demo.buggy_workflow` để phân tích lỗi double-pay khi checkpoint tách rời giao dịch ledger.
- Thiết kế và cài đặt bộ kiểm thử chéo `src/tests/test_durability_eval_extra.py` kiểm tra T11 idempotency, T12 crash & resume tại cả 3 điểm crash, approval sai claim / không hợp lệ, tràn trần hoàn tiền theo đơn, rò rỉ canary secret / PII (cả trace và stdout), và Trace contract v1.
- Review chéo mã nguồn của Người 1 (`workflow.py`), Người 2 (`single.py`), Người 3 (`orchestrator.py`) sau khi tích hợp lên `main`.
- Chủ trì chạy đánh giá thực nghiệm (CP4–CP5): crash suite 20 điểm (`src/reports/crash.json`), benchmark public 4 shape × 5 seed (`src/reports/benchmark.json`), thiết kế và chạy thí nghiệm ablation cho câu R1 trong `report/team/research_card.md`, và chạy kiểm tra định dạng nộp bài `lab8.check_submission`.

## 3. Đóng góp cụ thể

- **Kiểm thử chéo (`src/tests/test_durability_eval_extra.py` — 43 test cases):**
  1. **T11 Idempotency & Conflict (`test_t11_idempotency_and_conflict`)**: kiểm tra replay cùng số tiền trả `idempotent_replay`, chỉ giữ 1 dòng `refund_ledger` và 1 audit `refund_committed`; replay khác số tiền trả `amount_conflict` và giữ nguyên số tiền đã commit (`35000`).
  2. **T12 Crash & Resume tại 3 điểm crash (`before_effect`, `after_effect_before_checkpoint`, `after_checkpoint`)**: kiểm tra mức host (3 cases) và shape `swarm` (3 cases), xác nhận trạng thái ledger/checkpoint tại điểm crash và sau resume chỉ tồn tại 1 dòng ledger, 1 audit `refund_committed`.
  3. **Approval sai claim & trạng thái không hợp lệ (`test_approval_wrong_claim_and_invalid_states`)**: kiểm tra `approval_claim_mismatch` (mượn `A-001` của `C-001`), `approval_expired`, `approval_revoked`, `missing_approval` đều bị chặn và ghi audit `policy_denied`.
  4. **Tràn trần hoàn tiền theo đơn (3 test cases)**: kiểm tra `C-013` (`order_already_refunded`), `C-014` truyền full quote `150000` được host bù phần chênh `120000` (tổng đơn `O-515` = `150000`), minh họa lỗi tự trừ trước (`120000` -> `90000` gây `refund_mismatch`), và kiểm tra trần `paid_vnd`.
  5. **Rò rỉ canary secret / PII (3 test cases)**: kiểm tra trên `C-005` và `C-010` không làm lọt `CANARY_SECRET_*`, `CANARY_INTERNAL_*`, SĐT, địa chỉ, tên hàng mật vào trace, file `<run_id>*` hay `stdout`/`stderr`.
  6. **Trace contract v1 (`test_trace_contract_v1_rejects_bad_traces_and_accepts_valid`)**: kiểm tra đủ các lỗi `missing_trace`, `invalid_trace`, `trace_run_id_mismatch`, `stale_trace` và trace hợp lệ.
  7. **Ma trận kiểm thử chéo 4 shape (`@pytest.mark.student` — 28 test cases)**: `test_student_shapes_t12_crash_three_points` (4 shapes × 3 điểm crash trên `C-012`) và `test_student_shapes_pii_leak_and_order_cap` (4 shapes × `C-005`, `C-010`, `C-013`, `C-014`).
- **Review code của Người 1, 2, 3 trên nhánh `main`:**
  - `src/lab8/shapes/workflow.py` (Người 1): dùng `get_claim_view`, truyền `proposal` (full quote) và `crash_at` trực tiếp vào `issue_refund`, không nuốt `InjectedCrash`, không ghi dữ liệu thô nhạy cảm vào trace.
  - `src/lab8/shapes/single.py` (Người 2): đọc claim qua `get_claim_view`, truyền full quote vào `issue_refund`, flush trace rồi `raise` lại `InjectedCrash`, không ghi secret/PII vào trace.
  - `src/lab8/shapes/orchestrator.py` (Người 3): dùng `make_handoff` (`facts={}`) và chỉ trace `safe_dump(handoff)`, truyền full quote vào `issue_refund`, flush trace rồi `raise` lại `InjectedCrash`.
- **Thực nghiệm Benchmark, Crash & Ablation (CP4–CP5):**
  - Sinh `src/reports/crash.json` bằng `lab8.crash_test` đạt `20/20`.
  - Sinh `src/reports/benchmark.json` bằng `lab8.benchmark` trên 4 shape × 14 claim public × 5 seed (`11,22,33,44,55`).
  - Thiết kế biến thể ablation trong `src/scripts/ablation_r1.py` (`orchestrator_min_tools`, `orchestrator_no_llm`) kiểm định câu **R1 · Scaling** qua cờ `--extra-shape` của `lab8.benchmark`, xuất `src/reports/ablation_r1.json` và điền hoàn chỉnh `report/team/research_card.md`.
- **Tài liệu tóm tắt:** `report/team/nguoi4_durability_eval_summary.md`.

## 4. Bằng chứng

- **Commit & Mã nguồn:**
  - Commit đã merge trên `main`: `1e0caa8` ("add orchestrator and eval", merge tại `db60802`)
  - Test bổ sung: `src/tests/test_durability_eval_extra.py`
  - Script ablation R1: `src/scripts/ablation_r1.py`
  - File bằng chứng JSON: `src/reports/crash.json`, `src/reports/benchmark.json`, `src/reports/ablation_r1.json`
  - Tài liệu & báo cáo: `report/team/research_card.md`, `report/team/nguoi4_durability_eval_summary.md`, `report/team/2A202603426_PhamTruongChinh.md`
- **Kết quả chạy thực tế trên nhánh `main` (`cb24305`):**
  - Demo ledger: `cd src && .venv/bin/python -m lab8.demo.buggy_workflow` → `unsafe refund rows: 2 (the host ledger must stay at 1)`
  - Bộ test chéo riêng:
    - `.venv/bin/pytest tests/test_durability_eval_extra.py -v` → **15 passed, 28 deselected**
    - `.venv/bin/pytest tests/test_durability_eval_extra.py -o addopts= -v` → **43 passed**
  - Cổng kiểm thử toàn repo:
    - `.venv/bin/pytest -q` → **91 passed, 276 deselected**
    - `.venv/bin/pytest -q -m student -o addopts=` → **276 passed, 91 deselected** (3 shape nhóm viết pass 100%; `swarm` sai đúng 1 trial T02 ở seed 55)
  - Crash suite 20 điểm:
    - `reports/crash.json` → `crash_safety`: **20/20**
  - Benchmark public (`reports/benchmark.json` — 70 trials/shape):
    - `workflow`: `pass=1.000`, `pass^5=1.000`, `var=0.000000`, `cost/success=34.29` VND, `mean_steps=2.79` (`p95=3.0`)
    - `single`: `pass=1.000`, `pass^5=1.000`, `var=0.000000`, `cost/success=39.07` VND, `mean_steps=5.43` (`p95=6.0`)
    - `orchestrator`: `pass=1.000`, `pass^5=1.000`, `var=0.000000`, `cost/success=57.45` VND, `mean_steps=4.71` (`p95=5.0`)
    - `swarm`: `pass=0.986`, `pass^5=0.929`, `var=0.000816`, `cost/success=49.57` VND, `mean_steps=2.80` (`p95=3.0`)
  - Ablation R1 (`reports/ablation_r1.json` — 70 trials/shape):
    - `orchestrator` (`57.45` VND, `5.57` tool calls) → `orchestrator_min_tools` (`38.80` VND, giảm `32.46%`) → `orchestrator_no_llm` (`37.14` VND, `0.00` model calls) → `workflow` (`34.29` VND, giảm `40.32%`), cả 4 cấu hình đều giữ `pass=1.000`.
  - Kiểm tra định dạng nộp bài (`.venv/bin/python -m lab8.check_submission`):
    - `== shapes ==`: `[ OK ]` cả 3 shape (`workflow`, `single`, `orchestrator` đều `12/12` pass ở seed 11).
    - `== reports ==`: `[ OK ] reports/benchmark.json` (`4 shape x 14 claim x 5 seed`), `[ OK ] reports/crash.json` (`20/20`).
    - `== docs ==`: `[ OK ] report/team/research_card.md` (đã điền đủ).

## 5. Công cụ AI đã dùng

- **Công cụ:** Trợ lý AI (Antigravity).
- **Mục đích sử dụng:**
  - Hỗ trợ đọc hiểu luồng transaction/checkpoint/policy trong `durability.py`, `policy.py`, `metrics.py`, `crash_test.py`, `benchmark.py`.
  - Hỗ trợ viết bộ kiểm thử chéo `src/tests/test_durability_eval_extra.py`, script ablation `src/scripts/ablation_r1.py`, rà soát tiêu chí an toàn cho 3 shape (`workflow.py`, `single.py`, `orchestrator.py`), và điền phiếu `report/team/research_card.md` cùng báo cáo cá nhân.
- **Cách tự kiểm tra:**
  - Tự chạy lại toàn bộ các lệnh thực tế trong môi trường `.venv` (Python 3.12.3): `lab8.demo.buggy_workflow`, `pytest tests/test_durability_eval_extra.py -o addopts= -v`, `pytest -q`, `pytest -q -m student -o addopts=`, `lab8.crash_test`, `lab8.benchmark` (cho cả public và ablation), và `lab8.check_submission`; đối chiếu trực tiếp từng con số từ output và file JSON sinh ra.

## 6. Tự đánh giá

- Đã hoàn thành phần việc cốt lõi của Người 4 từ CP1 đến CP5 trên bộ public: cổng host (`91 passed`), ma trận student (`276 passed`), crash safety (`20/20`), benchmark công bằng 4 shape (`benchmark.json`), và thí nghiệm ablation R1 (`ablation_r1.json`, `research_card.md`).
- Các việc còn lại chờ hoàn tất cùng nhóm trước khi nộp:
  1. Khi nhận được bộ `student_drop/` từ giảng viên, đặt vào `src/student_drop/` (không commit) và chạy lệnh tự kiểm xuất `src/reports/hidden_selfcheck.json`.
  2. Phối hợp nhóm điền `report/team/decision_adr.md`, `report/team/group_report.md`, `TEAM.md`, commit để lấy hash chốt vào `decision_adr.md`, kiểm tra `python -m lab8.check_submission` ra `0 FAIL`, push GitHub và nộp link lên LMS.

# Decision record

Điền sau dấu `:` trên cùng dòng, không xóa nhãn. Giảng viên và `python -m lab8.check_submission` (chạy trong `src/`) đọc các dòng này bằng máy. Không đổi tên hay dời file này khỏi `report/team/`.
`Shape chọn` phải là đúng một trong: `workflow`, `single`, `orchestrator`, `swarm`. Đây là shape được chấm cổng hidden.

- Shape chọn:
- Commit hash:
- Run id dẫn chứng:
- Pass rate / pass^5 / seed min-max / variance:
- Cost per success (mô phỏng, VND):
- Crash safety:
- Secret leak / approval bypass:

Ví dụ một dòng đã điền: `- Shape chọn: workflow`, `- Crash safety: 20/20 (src/reports/crash.json)`.

## Vì sao shape này

Viết 1 đoạn. So cùng corpus và cùng seed, không so với một lần chạy lẻ.

## Có đáng đổi lấy multi-agent không

Nếu pass nhỉnh hơn mà cost và variance cao hơn, nhóm giữ hay đổi? Điều kiện nào làm quyết định đảo lại?

## Trace và bằng chứng

- **Các event được ghi trong trace:**
  - Với Shape C (`orchestrator`), mọi lần chạy (kể cả các nhánh return sớm `needs_info`, `escalated`, `denied`, `failed` và nhánh `InjectedCrash`) đều xuất file JSON tại `traces/R-orchestrator-<claim_id>-s<seed>.json` qua `lab8.trace.Trace` và `common.finish()` (nhánh crash gọi `trace.write()` trước khi `raise`). Các event ghi lại gồm: `plan` (`claim_id`, `has_order_id`), `handoff` (gói `handoff.v1` đã qua `make_handoff`/`sanitize`), `investigator` (`claim_view` rút gọn chỉ có `found`/`claim_id`/`order_id`, `lookup_order` theo `ORDER_FIELDS`, `policy_count`, `refund_history`), `quote` (`amount_vnd`, `reason`, `clause_ids`, `parts`), cùng các event kết thúc `decision`, `host_outcome`, `crash` hoặc `error`.
  - *(Ghi chú: Người 1 và Người 2 có thể bổ sung thêm danh sách event tương ứng của `workflow` và `single` nếu có khác biệt.)*
- **Các field cố ý KHÔNG ghi và lý do:**
  - Cố ý **không** đọc/không ghi `parent_secret`, `raw_headers_json` (chứa `Authorization: Bearer CANARY_SECRET_*`), không ghi raw claim row hay raw order row (`phone`, `address`, `internal_note`, `item_name`), và không ghi nội dung thô của `ticket` vào trace.
  - Ở biên handoff của `orchestrator`, `make_handoff` lọc theo `ALLOWED_FIELDS`, giữ `facts={}`, ép `principal_scope="owner_order_only"`, và từ chối `WRITE_TOOLS` (`issue_refund`, `append_audit`). Lý do: trace và handoff là một phần của ranh giới bảo mật; không dùng tóm tắt bằng LLM làm redaction vì LLM không đảm bảo loại bỏ triệt để secret/PII.
- **Cách chứng minh không lộ secret nếu trace nằm ngoài vùng scanner mặc định:**
  1. **Tuân thủ Trace contract v1 (fail-closed):** Mọi file phụ do shape ghi ra (nếu có) đều phải đặt cùng thư mục với `RunResult.trace_path` và có tiền tố `<run_id>*` để `lab8.metrics.trace_files()` / `artifact_blob()` gom đủ khi quét, đồng thời không `print` dữ liệu nhạy cảm ra `stdout`. Theo cơ chế fail-closed của grader (`missing_trace`, `stale_trace`, `invalid_trace`, `trace_run_id_mismatch`), bất kỳ log nào nằm ngoài vùng scanner đọc được hoặc sai format đều bị coi là rủi ro rò rỉ và fail ngay lập tức.
  2. **Kiểm chứng ở tầng code và test tự động:** Chứng minh bằng cấu trúc truy vấn/allowlist từ gốc (`get_claim_view`, `lookup_order`, `make_handoff` chặn `CANARY_SECRET_`/`parent_secret`/`raw_headers` tại nguồn) kết hợp bộ test trong `src/tests/test_orchestrator_extra.py` kiểm tra toàn bộ nhánh thoát (`resolved`, `denied`, `needs_info`, `escalated`, `failed`, `crash`) qua `check_trace` và `artifact_blob` để xác nhận không chứa canary secret hay PII.

## Giới hạn

MockLLM không phải model sản xuất. Latency để `unavailable`. Không sửa JSON cho đủ 0.75.

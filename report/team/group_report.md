# Báo cáo nhóm — Lab 8 LogiX-VN

## 1. Thông tin nhóm

- Tên nhóm: VCONS; lớp: L3A.
- Thành viên và phân công: xem `TEAM.md`.
- Commit mã nguồn được đánh giá: `231ec5d`, thống nhất với `decision_adr.md`.

## 2. Mục tiêu và cách tiếp cận

Nhóm chúng tôi xây dựng ba cách xử lý claim cùng contract `run_claim`, so sánh với swarm tham chiếu trên cùng dữ liệu public và seed. Nhóm chia công việc thành Workflow, Single ReAct, Orchestrator và Durability/Eval; tập trung kiểm tra tính đúng của số tiền, approval, trace và khả năng chạy lại sau crash.

## 3. Giải pháp

- **Workflow:** đọc claim và đơn theo phạm vi principal, tính quote từ đơn và policy bằng code. Thiếu mã đơn trả `needs_info`, đơn không nhìn thấy trả `escalated`, quote bằng 0 trả `denied`. Với quote dương, host kiểm tra và ghi refund. Ticket không quyết định số tiền.
- **Single ReAct:** dùng vòng ReAct và MockLLM để chọn các công cụ đọc trong giới hạn bước. Code tính quote; host xử lý quyết định ghi refund và approval.
- **Orchestrator:** tạo handoff theo allowlist cho investigator dùng các công cụ chỉ đọc; orchestrator tính quote và gọi host. Handoff và trace không mang toàn bộ parent context.
- **Swarm tham chiếu:** nhiều peer gọi model; ở seed 55 có điểm yếu cố ý tin số ngày trễ trong ticket thay vì dữ liệu đơn.

Cả ba shape nhóm viết chuyển **quote đầy đủ** cho `issue_refund`: host kiểm tra approval và trừ khoản đã hoàn theo đơn. Host dùng ledger và audit để bảo vệ idempotency. Workflow ghi trace gồm trạng thái tra cứu, quote và quyết định; orchestrator ghi handoff đã lọc và thông tin investigator được giới hạn.

## 4. Kết quả

Nguồn: `src/reports/benchmark.json`, 14 claim × 5 seed (11, 22, 33, 44, 55), DB mới cho từng trial, MockLLM và bảng giá mô phỏng. Pass^5 là metric trong report; không suy diễn thành bảo đảm cho dữ liệu khác.

| Shape | Pass rate | Pass^5 | Seed min–max | Variance | Cost/success (VND mô phỏng) | Steps mean / p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Workflow | 1.000 | 1.000 | 1.000–1.000 | 0 | 34.29 | 2.79 / 3 |
| Single | 1.000 | 1.000 | 1.000–1.000 | 0 | 39.07 | 5.43 / 6 |
| Orchestrator | 1.000 | 1.000 | 1.000–1.000 | 0 | 57.45 | 4.71 / 5 |
| Swarm | 0.986 | 0.929 | 0.929–1.000 | 0.000816 | 49.57 | 2.80 / 3 |

Crash suite host đạt **20/20**, theo `src/reports/crash.json`. Đây là kết quả của suite host, không phải 20 kịch bản riêng cho Workflow. Nhóm chọn Workflow vì cùng pass rate public với Single và Orchestrator nhưng chi phí mô phỏng thấp nhất; quyết định được ghi trong `decision_adr.md`. Kết quả ablation R1 được trình bày trong `research_card.md` và `src/reports/ablation_r1.json`.

Tự kiểm trên 40 claim hidden không nhãn × 5 seed cho mỗi shape nhóm viết: mỗi shape chạy 200 trial, không có trial `error` hoặc bị đánh dấu `leak_suspect` (`src/reports/hidden_selfcheck.json`). Do không có nhãn, phép tự kiểm không đo được pass rate và không thay thế kết quả grader chính thức về leak hay approval bypass.

## 5. Khó khăn và cách xử lý

Ticket có thể đưa số ngày trễ sai: Workflow dùng dữ liệu đơn thay vì tin ticket. Với đơn đã hoàn một phần, shape phải truyền full quote để host tự trừ; nếu tự trừ trước, host sẽ trừ lần nữa. Crash giữa effect và checkpoint được xử lý bằng ledger và idempotency thay vì chỉ dựa vào checkpoint. Trace và handoff phải giới hạn field để tránh lộ dữ liệu nhạy cảm.

## 6. Tổng hợp đóng góp

Nguyễn Minh Quân phụ trách Workflow; Nguyễn Văn Huy phụ trách Single ReAct; Nguyễn Thanh Tùng phụ trách Orchestrator và handoff; Phạm Trường Chinh phụ trách Durability/Eval. Bằng chứng chi tiết và test xem `TEAM.md` cùng báo cáo cá nhân trong `report/team/`.

## 7. Hạn chế và hướng cải thiện

Bộ public nhỏ và không đại diện đầy đủ dữ liệu thực. MockLLM không phải model sản xuất, chi phí chỉ là mô phỏng và latency là `unavailable`. So sánh shape không cô lập hoàn toàn topology vì số công cụ và lượt gọi model cũng khác nhau. Hướng phát triển tiếp theo là mở rộng dữ liệu đánh giá và đo trên model thực để xác định liệu lợi ích của multi-agent có bù được chi phí phối hợp hay không.

## 8. Tài liệu tham khảo

- `docs/business_rules.md`, `docs/contracts.md`, `docs/architecture.md`, `docs/metrics.md`.
- `src/reports/benchmark.json`, `src/reports/crash.json`, `src/reports/ablation_r1.json`.
- `report/team/research_card.md`, báo cáo cá nhân và `TEAM.md`.

# Bonus report: B1

- Topic + nguồn (tên, năm, slide): B1 · Investigator song song và critical path (Google Research 2026, *Towards a Science of Scaling Agent Systems*; Slide 15, 24, 33, 41)
- CLAIM của nguồn (1 câu): Multi-agent chỉ có lợi khi tác vụ chia song song được; với tác vụ tuần tự, các biến thể multi-agent trong nghiên cứu giảm 39–70% hiệu năng do overhead điều phối.
- BOUNDARY (model / dataset / setup): Đo trên tập LogiX-VN với 14 claim public (`data/public_claims.jsonl`), 5 seed `11, 22, 33, 44, 55`. Model MockLLM xác định, mô hình độ trễ mô phỏng (`bonus/latency.yaml`) đo theo DAG phụ thuộc không dùng `time.sleep`.
- HYPOTHESIS trên LogiX: Trong claims flow, bước lập kế hoạch (`plan`), trích xuất claim, tính quote và phát lệnh hoàn tiền (`issue_refund`) có ràng buộc tuần tự nghiêm ngặt; chỉ có các investigator đọc dữ liệu (`lookup_order`, `lookup_policy`, `lookup_refund_history`) là độc lập và chạy song song được. Do đó, việc song song hóa investigator chỉ giảm độ trễ phần đọc từ 105 ms xuống 40 ms, mang lại speedup toàn hệ thống khoảng ~1.18x theo Định luật Amdahl, trong khi pass rate và tính toàn vẹn của ledger vẫn đạt 100% (không đổi).
- Biến cố định / biến thay đổi:
  - *Biến cố định:* Model MockLLM, seed `11, 22, 33, 44, 55`, 14 claim public, pricing config, quy tắc nghiệp vụ, cơ chế crash/ledger.
  - *Biến thay đổi:* Phương thức thực thi investigator trong Shape C (tuần tự `orchestrator` vs song song đa luồng qua ThreadPoolExecutor `orchestrator_parallel`).
- Lệnh tái lập (copy-paste được):
  ```bash
  python -m lab8.benchmark --shapes workflow,orchestrator,orchestrator_parallel --extra-shape orchestrator_parallel=bonus.orchestrator_parallel:run_claim --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/bonus_b1_benchmark.json
  python -m pytest -q tests/test_bonus_orchestrator_parallel.py
  ```
- File report + run id: `src/reports/bonus_b1_benchmark.json` (14 claims × 5 seeds = 70 trials/shape; run id mẫu: `R-orchestrator_parallel-C-001-s11`)

## Kết quả

Số liệu đối chuẩn trích xuất trực tiếp từ `src/reports/bonus_b1_benchmark.json` và mô hình độ trễ `src/bonus/latency.yaml`:

| Shape | Pass rate | Pass^5 | Variance | Cost/success (VND) | Mean steps | Độ trễ tuần tự (ms) | Critical Path (ms) | Speedup thực tế |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **workflow** | 1.000 | 1.000 | 0.000000 | 34.29 | 2.79 | - | - | - |
| **orchestrator** (tuần tự) | 1.000 | 1.000 | 0.000000 | 57.45 | 4.71 | 425.0 | 425.0 | 1.000x |
| **orchestrator_parallel** (song song) | 1.000 | 1.000 | 0.000000 | 48.16 | 5.57 | 425.0 | 360.0 | **1.181x** |

- **An toàn & Idempotency:** Cả `orchestrator` và `orchestrator_parallel` đạt `secret_leak_count = 0`, `approval_bypass_count = 0`, `crash_safety = 20/20`.
- **Thực thi đa luồng an toàn:** Mỗi thread mở connection SQLite độc lập (`connect(store_path)`) và đóng sau khi đọc, join kết quả theo thứ tự cố định của danh sách công cụ allowlist, đảm bảo kết quả hoàn toàn tất định và không phụ thuộc vào thứ tự luồng hoàn thành.

## Kết luận

- **Đánh giá hypothesis:** Kết quả hoàn toàn **ủng hộ hypothesis** và minh chứng rõ định luật Amdahl (slide 33):
  - Phân số tác vụ có thể song song hóa ($P$) chỉ chiếm thời gian đọc của 3 investigator: $(40 + 35 + 30) / 425 \approx 0.247$ (24.7%).
  - Phần còn lại ($1 - P \approx 75.3%$) gồm các bước phụ thuộc dữ liệu tuần tự bắt buộc: `get_claim_view` (25 ms) $\to$ `plan` (120 ms) $\to$ trích xuất điều kiện $\to$ `compute_compensation` (15 ms) $\to$ `draft` (110 ms) $\to$ `issue_refund` (50 ms).
  - Tăng tốc tối đa lý thuyết theo Amdahl: $S = \frac{1}{(1 - P) + P / N} = \frac{1}{0.753 + 0.247 / 3} \approx 1.197\times$, rất sát với kết quả đo critical path thực nghiệm là **1.181x** ($425 / 360$).
- **Trả lời câu hỏi cốt lõi:** Bước tính quote phụ thuộc vào thông tin đơn hàng (`order`), do đó chỉ có pha thu thập thông tin độc lập giữa order, policy và lịch sử hoàn tiền là thực sự song song được.
- **Điều kiện đảo ngược:** Kết luận sẽ đảo ngược (song song hóa mang lại lợi ích lớn $S > 3\times$) nếu bài toán mở rộng sang phân tích đa nguồn phức tạp (ví dụ đối soát đồng thời 10 kho hàng, kiểm tra hình ảnh hư hại bằng model vision nặng, hoặc tra cứu đồng thời nhiều nhà cung cấp vận chuyển độc lập).

## Giới hạn

1. Sử dụng mô hình độ trễ mô phỏng (`bonus/latency.yaml`) vì MockLLM là hàm nội tại tức thì và SQLite in-memory/file cục bộ có latency micro-giây, chưa phản ánh đầy đủ network jitter của API thực.
2. Số lượng investigator song song trong bài toán LogiX-VN hiện dừng lại ở 3 công cụ đọc; kích thước batch chưa đủ lớn để bộc lộ hiện tượng tranh chấp tài nguyên CPU/Network bão hòa.

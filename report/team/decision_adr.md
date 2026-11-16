# Decision record

Nhóm chúng tôi chọn Workflow cho bài toán xử lý claim của LogiX-VN. Quyết định dựa trên kết quả trong `src/reports/benchmark.json` và `src/reports/crash.json`.

- Shape chọn: workflow
- Commit hash: 4f88983 (phiên bản mã nguồn tham chiếu)
- Run id dẫn chứng: R-workflow-C-001-s11 (src/reports/benchmark.json)
- Pass rate / pass^5 / seed min-max / variance: 1.000 / 1.000 / 1.000–1.000 / 0.000 (70 trial public)
- Cost per success (mô phỏng, VND): 34.29 (src/reports/benchmark.json)
- Crash safety: 20/20 (src/reports/crash.json; suite host, không phải 20 kịch bản riêng của workflow)
- Secret leak / approval bypass: chưa có kết quả grader hidden; chưa thể kết luận số lượng

## Vì sao shape này

Nhóm chọn workflow vì trên cùng 14 claim public và năm seed, workflow, single và orchestrator đều đạt 70/70; workflow có cost/success mô phỏng 34.29 VND, thấp hơn single 39.07 và orchestrator 57.45. Swarm đạt 69/70. Với luồng xử lý tuần tự và luật tính tiền xác định, workflow đáp ứng yêu cầu mà không cần thêm lời gọi model. Kết luận này giới hạn trong tập thử public và môi trường mô phỏng của lab.

## Có đáng đổi lấy multi-agent không

Với dữ liệu public hiện có, orchestrator chưa tăng pass rate so với workflow và có chi phí mô phỏng cao hơn, nên nhóm giữ Workflow. Quyết định có thể thay đổi khi bài toán có nhiều nguồn tra cứu độc lập, yêu cầu tách quyền hoặc dữ liệu mới cho thấy multi-agent cải thiện chất lượng đủ để bù chi phí. So sánh các shape đồng thời thay đổi nhiều thành phần, nên nhóm không quy toàn bộ chênh lệch cho topology.

## Trace và bằng chứng

Workflow ghi trạng thái tra cứu đơn, quote và quyết định; không ghi ticket hay nguyên bản claim/order vào trace. Orchestrator ghi handoff đã lọc theo allowlist và kết quả investigator được giới hạn. Nhóm sử dụng trace được ghi trong lần chạy, đúng run ID và nằm ở nơi scanner có thể đọc. Kết quả scanner chỉ bao phủ các file được quét, không chứng minh tính an toàn của log ngoài phạm vi đó.

## Giới hạn

MockLLM không phải model sản xuất; chi phí là mô phỏng, latency `unavailable`. Bộ public chỉ có 14 claim và năm seed. Báo cáo chưa có kết quả hidden cho pass rate, secret leak hay approval bypass.

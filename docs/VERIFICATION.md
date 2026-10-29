# Kiểm chứng BikeDemand ngày 29 tháng 10 năm 2026

## Phạm vi

Chạy lại mã nguồn và dữ liệu gốc trong một thư mục riêng, không sao chép
mô hình, báo cáo hoặc các tập processed đã tạo. Dùng cùng cấu hình đã
công bố, không chọn lại mô hình sau khi xem test. Bản bàn giao được giữ
nguyên. Môi trường kiểm tra là Windows, Python 3.12.14 và các phiên bản
thư viện trong requirements.txt, gồm scikit-learn 1.9.1.

Lần kiểm tra sử dụng môi trường Python đã cài trên cùng máy; chưa phải
bằng chứng cài mới hoặc chạy trên một máy khác.

## Tái lập pipeline

Cả 10 script chạy thành công theo thứ tự trong README: data,
split_data, data_report, baseline, train, experiment_sgd,
experiment_split, analyze_errors, freeze_model và evaluate.

| Mô hình | MAE test | RMSE test | R² test |
| --- | ---: | ---: | ---: |
| Baseline | 110.2960055719 | 158.5578727430 | 0.4693947364 |
| LinearRegression | 102.7641434748 | 137.6055515514 | 0.6003610185 |

Các bảng sgd_validation_metrics.csv, split_comparison.csv,
validation_error_groups.csv và test_error_groups.csv khớp trong dung sai
số thực (rtol và atol bằng 1e-8). Metric test lệch ở mức khoảng 1e-13,
không ảnh hưởng các chữ số báo cáo. Không yêu cầu mô hình joblib tạo lại
phải giống từng byte giữa các môi trường; mỗi gói vẫn được xác minh bằng
checksum của chính gói đó.

## Kiểm thử

Sau khi backend báo sẵn sàng, chạy:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
```

Bộ test hiện có 17 phương thức: 8 kiểm thử API và 9 kiểm thử offline.
Các ca mới bao gồm NaN, Infinity và số quá lớn; báo cáo JSON hỏng,
thiếu trường, sai phiên bản/chính sách; thay đổi mô hình hoặc dữ liệu;
và CSV chỉ khác xuống dòng LF/CRLF. Các ca làm thay đổi tệp sử dụng
thư mục tạm, không sửa artifact bàn giao.

CLI và API Đánh giá cùng dùng src/integrity.py để xác minh pipeline,
train, validation, metadata báo cáo và dữ liệu test. API trả 503 khi
báo cáo thiếu, không hợp lệ hoặc không khớp. Việc xác minh ràng buộc
artifact không thay thế phép tính lại metric nếu nội dung báo cáo bị sửa.

## Giới hạn còn lại

- Chưa kiểm tra tải đồng thời, độ trễ p50/p95 hoặc nhiều thiết bị.
- Chưa thực nghiệm nhiều seed hoặc rolling window.
- Form dùng giá trị chuẩn hóa theo CSV; chưa chuyển nhiệt độ sang °C.
- Miền hợp lệ của từng trường chưa chứng minh cả kịch bản nằm gần train.
- Giữ các hạn chế dự báo cao điểm và thời tiết xấu đã công bố.

Khi cập nhật báo cáo hoặc slide, phân biệt 8 test API với tổng 17 test;
không mô tả lần tái lập này là kiểm chứng trên máy khác.

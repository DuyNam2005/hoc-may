# BikeDemand

Ứng dụng minh họa dự báo tổng lượt thuê xe đạp theo giờ
từ dữ liệu lịch và thời tiết trong Bike Sharing Dataset.

Đây là project học phần Học máy cơ bản.
Dữ liệu thuộc giai đoạn 2011–2012; ứng dụng chưa được
xác thực cho nhu cầu hiện tại hoặc từng trạm xe.

## Công nghệ

- Python 3.11
- pandas, NumPy, scikit-learn
- FastAPI, Uvicorn
- HTML, CSS, JavaScript
- matplotlib, joblib

Phiên bản thư viện được lưu trong requirements.txt.

## Cấu trúc

- data/raw/: dữ liệu gốc.
- data/processed/: train, validation và test.
- data/README.md: nguồn và quy tắc dữ liệu.
- data/data_dictionary.md: mô tả biến.
- data/checksums.json: SHA-256 các tệp gốc.
- src/: kiểm tra dữ liệu, chia tập, train và đánh giá.
- models/: pipeline đã lưu và cấu hình mô hình.
- backend/: API và các đường dẫn phục vụ giao diện.
- frontend/: giao diện web.
- reports/: metric, dự báo, phân tích lỗi và biểu đồ.
- tests/: kiểm thử API.

## Cài đặt trên Windows

Mở terminal tại thư mục gốc dự án.

Tạo môi trường:

```powershell
python -m venv .venv
```

Cài thư viện:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Không cần kích hoạt môi trường nếu gọi trực tiếp Python
trong .venv như các lệnh dưới đây.

## Chạy bản demo có sẵn

Cần có:

- models/forecast_pipeline.joblib
- models/model_config.json
- Các báo cáo JSON/CSV và PNG trong reports/
- Các tệp frontend

Chạy backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

Mở trình duyệt:

- Giới thiệu và model card: http://127.0.0.1:8000/about
- Dự báo: http://127.0.0.1:8000/
- Đánh giá: http://127.0.0.1:8000/evaluation
- Tài liệu API: http://127.0.0.1:8000/docs

Trên trang dự báo, chọn “Nạp kịch bản mẫu” rồi
“Dự báo lượt thuê”.

Dừng server bằng Ctrl+C.

## Dữ liệu

Nguồn:
https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset

DOI:
https://doi.org/10.24432/C5W894

Giấy phép công bố trên UCI: CC BY 4.0.

Tải ZIP từ UCI, giải nén và đặt trực tiếp các tệp
hour.csv, day.csv, Readme.txt vào data/raw/.

Đối chiếu checksum trong data/checksums.json.
Xem data/README.md và data/data_dictionary.md để biết
nguồn, quy ước và giới hạn.

## Tái lập pipeline

Thực hiện trong một bản sao sạch của dự án, có dữ liệu gốc
nhưng chưa có các đầu ra đã tạo trong models/ và reports/.

Giữ nguyên bản bàn giao hiện tại. Không xóa mô hình hoặc
báo cáo đã chốt để thử cấu hình khác sau khi xem test.

Chạy lần lượt từ thư mục gốc:

```powershell
.\.venv\Scripts\python.exe .\src\data.py
.\.venv\Scripts\python.exe .\src\split_data.py
.\.venv\Scripts\python.exe .\src\data_report.py
.\.venv\Scripts\python.exe .\src\baseline.py
.\.venv\Scripts\python.exe .\src\train.py
.\.venv\Scripts\python.exe .\src\experiment_sgd.py
.\.venv\Scripts\python.exe .\src\experiment_split.py
.\.venv\Scripts\python.exe .\src\analyze_errors.py
.\.venv\Scripts\python.exe .\src\freeze_model.py
.\.venv\Scripts\python.exe .\src\evaluate.py
```

freeze_model.py từ chối ghi đè mô hình đã chốt.
evaluate.py hiển thị kết quả đã lưu nếu test_metrics.json
đã tồn tại.

Việc tái lập giữ nguyên cấu hình đã công bố; không dùng
kết quả test để chọn lại mô hình.

## Thiết kế đánh giá

Chia dữ liệu theo thời gian:

| Tập | Giai đoạn | Số dòng |
| --- | --- | ---: |
| Train | 01/01/2011–30/04/2012 | 11.539 |
| Validation | 01/05/2012–31/08/2012 | 2.952 |
| Test | 01/09/2012–31/12/2012 | 2.888 |

Baseline sử dụng trung bình theo thứ và giờ từ train.
Nếu thiếu nhóm, dùng trung bình theo giờ rồi trung bình train.

Pipeline hồi quy:
- One-hot cho biến dạng nhóm.
- StandardScaler cho biến số.
- LinearRegression.

Tiền xử lý chỉ fit trên train.
Loại casual, registered và instant khỏi đầu vào.

Các thí nghiệm:
- Baseline so với hồi quy.
- Time split so với random split trên phần train/validation.
- SGD với learning rate 0.0001, 0.001 và 0.01;
  200 vòng học, seed 42.
- Sai số giờ cao điểm và thời tiết xấu.

LinearRegression được chọn theo MAE validation.
Tiêu chí ưu tiên MAE được chốt sau khi xem validation,
trước khi mở test. Mô hình cuối giữ nguyên trạng thái học
từ train, không refit trên validation.

Giờ cao điểm ngày làm việc là 8, 17, 18 và 19 giờ,
được xác định từ train.

## Kết quả test của bản bàn giao

| Mô hình | MAE | RMSE | R² |
| --- | ---: | ---: | ---: |
| Baseline | 110.2960 | 158.5579 | 0.4694 |
| LinearRegression | 102.7641 | 137.6056 | 0.6004 |

Metric chính xác được lưu trong reports/test_metrics.json.
MAE và RMSE có đơn vị lượt thuê/giờ.
R² không phải phần trăm độ chính xác.

## API dự báo

POST /api/forecast

Ví dụ request:

```json
{
  "forecast_date": "2011-01-01",
  "hr": 0,
  "season": 1,
  "holiday": 0,
  "weathersit": 1,
  "temp": 0.24,
  "atemp": 0.2879,
  "hum": 0.81,
  "windspeed": 0.0
}
```

Response gồm prediction, raw_prediction, unit,
model_version, features_used và warnings.

- 200: dự báo thành công.
- 422: thiếu trường, sai kiểu, ngoài miền hoặc trường thừa.
- 500: lỗi dự báo nội bộ.

Dự báo âm được đưa về 0 và có cảnh báo.
Không làm tròn trước khi đánh giá.

Backend nạp pipeline khi khởi động, không train theo request.
Các endpoint dashboard đọc báo cáo đã lưu.

## Kiểm thử API

Giữ backend chạy trong terminal thứ nhất.
Mở terminal thứ hai tại thư mục gốc và chạy:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Bộ kiểm thử gồm 7 test, kiểm tra dự báo hợp lệ, đầu vào lỗi,
trường thiếu/thừa, biến lịch và các API báo cáo.

Đây là kiểm thử API, không thay thế kiểm tra tái lập toàn bộ
pipeline hoặc kiểm tra giao diện trên các thiết bị.

## Chất lượng dữ liệu và giới hạn

- Không có ô trống hoặc mốc giờ trùng trong dữ liệu gốc.
- Thiếu 165 mốc giờ; không tự điền 0.
- 353 dòng train được gắn cờ theo IQR và vẫn giữ nguyên.
- Train chỉ có 3 mẫu thời tiết loại 4.
- Validation và test không có mẫu thời tiết loại 4.
- Mô hình thường dự báo thấp ở giờ cao điểm.
- MAE thời tiết xấu chưa vượt baseline.
- Thời tiết trong API là kịch bản do người dùng cung cấp.
- Đánh giá lịch sử sử dụng thời tiết ghi trong dữ liệu;
  triển khai tương lai cần thông tin có trước giờ dự báo.
- Quy ước mùa và nhiệt độ giữa tài liệu nguồn còn khác nhau.
  Bản hiện tại giữ giá trị CSV, chưa chuyển nhiệt độ sang °C.
- Không diễn giải hệ số như bằng chứng quan hệ nhân quả.
- Đầu ra không phải số xe tồn tại từng trạm.
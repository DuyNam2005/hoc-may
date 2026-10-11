# Từ điển dữ liệu

## Định nghĩa bài toán

- Đơn vị quan sát: một giờ có dữ liệu.
- Mục tiêu: dự báo tổng lượt thuê cnt trong giờ được chọn.
- Biến lịch có thể biết trước giờ dự báo.
- Thời tiết của giờ cần dự báo phải được cung cấp như kịch bản
  hoặc lấy từ nguồn dự báo có sẵn trước giờ đó.
- Thời tiết quan sát của giờ đó trong dữ liệu lịch sử không mặc
  nhiên có sẵn trước giờ dự báo. Đánh giá hiện tại sử dụng các
  giá trị thời tiết ghi trong dữ liệu, nên cần công bố giả định này.

## Các cột trong hour.csv

| Biến | Kiểu và miền | Ý nghĩa / đơn vị | Vai trò | Thời điểm có sẵn |
| --- | --- | --- | --- | --- |
| instant | Số nguyên | Mã bản ghi | ID, loại khỏi mô hình | Khi tạo bản ghi |
| dteday | Ngày YYYY-MM-DD | Ngày quan sát | Tạo mốc thời gian; không đưa trực tiếp vào mô hình | Biết trước |
| season | Mã 1–4 | Nhóm mùa theo dữ liệu gốc | Feature dạng nhóm | Biết trước theo quy ước lịch |
| yr | Mã 0 hoặc 1 | 0: 2011; 1: 2012 | Feature dạng nhóm | Biết trước |
| mnth | Số nguyên 1–12 | Tháng | Feature dạng nhóm | Biết trước |
| hr | Số nguyên 0–23 | Giờ cần dự báo | Feature dạng nhóm | Biết trước |
| holiday | Mã 0 hoặc 1 | Ngày lễ theo lịch nguồn | Feature dạng nhóm | Biết trước nếu có lịch nguồn |
| weekday | Mã 0–6 | 0: Chủ nhật; 1: thứ Hai; …; 6: thứ Bảy | Feature dạng nhóm | Tính từ ngày |
| workingday | Mã 0 hoặc 1 | 1 nếu không phải cuối tuần hoặc ngày lễ | Feature dạng nhóm | Tính từ ngày và holiday |
| weathersit | Mã 1–4 | Nhóm điều kiện thời tiết | Feature dạng nhóm | Kịch bản hoặc dự báo có trước; quan sát lịch sử có sau |
| temp | Số thực chuẩn hóa | Nhiệt độ theo quy ước CSV, không nhập trực tiếp bằng °C | Feature số | Kịch bản hoặc dự báo có trước; quan sát lịch sử có sau |
| atemp | Số thực chuẩn hóa | Nhiệt độ cảm nhận theo quy ước CSV | Feature số | Kịch bản hoặc dự báo có trước; quan sát lịch sử có sau |
| hum | Số thực chuẩn hóa | Độ ẩm chia cho 100; 0.8 tương ứng 80% | Feature số | Kịch bản hoặc dự báo có trước; quan sát lịch sử có sau |
| windspeed | Số thực chuẩn hóa | Tốc độ gió theo quy ước CSV | Feature số | Kịch bản hoặc dự báo có trước; quan sát lịch sử có sau |
| casual | Số nguyên không âm | Lượt thuê của người dùng không đăng ký | Loại vì leakage | Sau khi giờ kết thúc |
| registered | Số nguyên không âm | Lượt thuê của người dùng đăng ký | Loại vì leakage | Sau khi giờ kết thúc |
| cnt | Số nguyên không âm | Tổng lượt thuê trong giờ | Target | Sau khi giờ kết thúc |

## Biến được tạo thêm

timestamp = dteday + hr giờ.

Biến này dùng để sắp xếp, chia tập và vẽ biểu đồ;
không đưa trực tiếp vào mô hình hiện tại.

## Nhóm thời tiết

| Mã | Mô tả tóm tắt |
| --- | --- |
| 1 | Trời quang, ít mây hoặc có mây từng phần |
| 2 | Sương mù và các mức độ mây |
| 3 | Tuyết nhẹ hoặc mưa nhẹ, có thể kèm giông |
| 4 | Mưa lớn hoặc các điều kiện thời tiết khắc nghiệt |

Các mô tả được tóm tắt từ Readme.txt đi kèm dữ liệu.

## Tiền xử lý

- One-hot cho season, yr, mnth, hr, holiday, weekday,
  workingday và weathersit.
- StandardScaler cho temp, atemp, hum và windspeed.
- Encoder và scaler chỉ fit trên train.
- Không dùng casual, registered hoặc instant làm đầu vào.
- cnt chỉ dùng làm nhãn khi huấn luyện hoặc đánh giá.
- Backend tính yr, mnth, weekday và workingday từ ngày
  cùng trạng thái ngày lễ của kịch bản.

## Miền đầu vào của API hiện tại

- Ngày: thuộc năm 2011 hoặc 2012.
- Giờ: số nguyên từ 0 đến 23.
- season và weathersit: số nguyên từ 1 đến 4.
- holiday: số nguyên 0 hoặc 1.
- temp, atemp, hum, windspeed: số hữu hạn trong khoảng 0–1.
- Không chấp nhận trường thừa hoặc thiếu trường bắt buộc.

Miền API là ràng buộc đầu vào của bản demo. Một giá trị hợp lệ
theo schema không đồng nghĩa có đủ mẫu huấn luyện tương ứng
hoặc bảo đảm dự báo chính xác.

## Các lưu ý về nguồn

Mô tả mã mùa và chuẩn hóa nhiệt độ giữa trang UCI và Readme.txt
có điểm chưa thống nhất.

Bản hiện tại giữ nguyên mã và giá trị số trong CSV.
Chưa gán tên mùa trên form hoặc chuyển nhiệt độ sang °C.
Không diễn giải windspeed chuẩn hóa trực tiếp thành km/h
khi chưa xác minh đơn vị nguồn.

Ngày lễ thuộc lịch của dữ liệu gốc, không tự thay bằng lịch Việt Nam.

## Nguồn tham khảo

- data/raw/Readme.txt
- https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset
- https://doi.org/10.24432/C5W894
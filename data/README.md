# Dữ liệu Bike Sharing

## Nguồn

- Bộ dữ liệu: Bike Sharing.
- Nguồn: UCI Machine Learning Repository.
- Trang dữ liệu:
  https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset
- DOI: https://doi.org/10.24432/C5W894
- Giấy phép công bố trên UCI: CC BY 4.0.
- Ngày tải trong quá trình thực hiện dự án: 11/10/2026.

Trích dẫn:
Fanaee-T, H. (2013). Bike Sharing [Dataset].
UCI Machine Learning Repository.
https://doi.org/10.24432/C5W894.

## Các tệp gốc

- raw/hour.csv: dữ liệu theo giờ, dùng cho bài toán chính.
- raw/day.csv: dữ liệu theo ngày, không dùng huấn luyện mô hình theo giờ.
- raw/Readme.txt: tài liệu mô tả đi kèm bộ dữ liệu.

Các tệp gốc được giữ nguyên. Kết quả xử lý được lưu riêng.

## Phạm vi

Dữ liệu lịch sử của hệ thống Capital Bikeshare tại
Washington, D.C., Hoa Kỳ, trong giai đoạn 2011–2012.

Mỗi dòng trong hour.csv đại diện cho một giờ có dữ liệu.
Biến mục tiêu cnt là tổng lượt thuê trong giờ đó.

## Kiểm tra dữ liệu ban đầu

- hour.csv có 17.379 dòng và 17 cột.
- Khoảng thời gian: 01/01/2011 00:00 đến 31/12/2012 23:00.
- Không có ô trống.
- Không có bản ghi trùng hoặc mốc giờ trùng.
- Thiếu 165 mốc giờ trong chuỗi thời gian đầy đủ.
- Không tự gán 0 lượt thuê cho giờ thiếu.
- Không loại dòng trong quy trình hiện tại.

## Chia dữ liệu

Chia theo thời gian, không trộn ngẫu nhiên cho đánh giá chính:

| Tập | Giai đoạn | Số dòng |
| --- | --- | ---: |
| Train | 01/01/2011–30/04/2012 | 11.539 |
| Validation | 01/05/2012–31/08/2012 | 2.952 |
| Test | 01/09/2012–31/12/2012 | 2.888 |

Encoder và scaler chỉ fit trên train.
Test không dùng để chọn mô hình hoặc tham số.

Thí nghiệm random split chỉ sử dụng phần train và validation
ban đầu, giữ nguyên test cuối.

## Biến không đưa vào mô hình

- casual và registered: loại vì casual + registered = cnt.
- instant: mã bản ghi, không dùng làm đặc trưng.
- cnt: biến mục tiêu, không dùng làm đầu vào.

## Quy ước và giới hạn

temp, atemp, hum và windspeed được sử dụng theo giá trị
chuẩn hóa trong CSV.

Mô tả mã mùa và chuẩn hóa nhiệt độ giữa trang UCI và Readme.txt
có điểm chưa thống nhất. Bản hiện tại giữ nguyên mã và giá trị
CSV, chưa chuyển nhiệt độ sang đơn vị độ C.

Ngày lễ và lịch trong dữ liệu thuộc hệ thống gốc;
không tự áp dụng lịch Việt Nam.

Dữ liệu lịch sử chưa đủ để quyết định cung ứng hiện tại
hoặc dự báo nhu cầu từng trạm.

## Tải lại dữ liệu

1. Truy cập trang UCI được dẫn ở trên.
2. Chọn Download và giải nén.
3. Đặt hour.csv, day.csv và Readme.txt trực tiếp vào data/raw/.
4. Đối chiếu SHA-256 với data/checksums.json.

Nếu checksum khác, kiểm tra phiên bản hoặc nội dung tệp
trước khi tái lập kết quả.
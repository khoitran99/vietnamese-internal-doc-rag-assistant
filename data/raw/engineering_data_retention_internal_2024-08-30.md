# Engineering

## Lưu trữ dữ liệu ứng dụng

Dữ liệu nhật ký ứng dụng được lưu tối đa 90 ngày trên hệ thống log tập trung.
Dữ liệu backup cơ sở dữ liệu được giữ tối đa 180 ngày và mã hóa ở trạng thái nghỉ.

## Xóa dữ liệu định kỳ

Công việc xóa dữ liệu hết hạn chạy tự động vào 02:00 mỗi ngày theo lịch cron được kiểm soát.
Mọi tác vụ xóa dữ liệu phải ghi log kiểm toán và lưu trữ tối thiểu 12 tháng.

## Truy cập dữ liệu lịch sử

Yêu cầu truy xuất dữ liệu quá hạn phải được phê duyệt bởi Data Owner và Security Team.
Dữ liệu được truy xuất chỉ dùng cho mục đích điều tra hoặc tuân thủ pháp lý.

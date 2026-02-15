# Engineering

## Quản lý phát hành

Mỗi bản phát hành production phải có release note, kế hoạch rollback và danh sách rủi ro đã đánh giá.
Mọi thay đổi mức độ cao cần được phê duyệt bởi Tech Lead và Engineering Manager trước khi triển khai.

## Cửa sổ triển khai

Triển khai production được thực hiện trong khung 20:00-23:00 các ngày thứ Ba và thứ Năm.
Không triển khai thay đổi lớn vào ngày cuối tuần trừ khi có phê duyệt khẩn cấp.

## Kiểm soát sau triển khai

Đội triển khai phải theo dõi dashboard lỗi, độ trễ và tỉ lệ thành công API trong 60 phút đầu.
Nếu vượt ngưỡng cảnh báo, thực hiện rollback trong vòng 15 phút theo playbook vận hành.

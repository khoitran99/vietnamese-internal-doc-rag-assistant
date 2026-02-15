# Engineering

## Chiến lược nhánh mã nguồn

Nhóm sử dụng mô hình trunk-based development với nhánh chính là `main`.
Mọi thay đổi được triển khai qua pull request nhỏ, có kiểm thử tự động và review bắt buộc.

## Quy tắc đặt tên nhánh

Nhánh tính năng đặt theo mẫu `feat/<ticket-id>-<mota-ngan>`.
Nhánh sửa lỗi đặt theo mẫu `fix/<ticket-id>-<mota-ngan>`.

## Chính sách merge

Pull request chỉ được merge khi tất cả kiểm thử bắt buộc ở trạng thái thành công.
Không được merge trực tiếp vào `main` nếu chưa có ít nhất một reviewer phê duyệt.

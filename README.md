# Django Camera view and playback

Project status: Finished.

Features:
- Play back h264 .mp4 recordings.
- View live camera feeds.
- Support for multiple cameras.

# How to use:
- Clone this repository.
- cd into the cloned directory.
- run `pip install -r requirements.txt`.
- run `python manage.py migrate`.
- create a superuser by running `python manage.py createsuperuser`.
- run the server by running `python manage.py runserver`.
- login on `http://127.0.0.1:8000/login/`.
- go to `http://127.0.0.1:8000/admin/cameras/camera/` and press `add camera` in the top right corner of the screen.
- fill in the form with a title (E.g. `Camera1`), the url of your camera (E.g. `http://192.168.0.11:8000/stream.mjpg`) and the name of the directory that the recordings for this camera are in (E.g. `camera1`). See the image below.
- Hit save and repeat the 2 steps above for every camera you want to add.
- In `ReplaySite/settings.py` change the value of `MEDIA_ROOT` to the path of the parent directory of the folder that the recordings for this camera are in (So here that would be the parent directory of `camera1`). See the image below. Make sure to use forwardslashes and not backslashes.
- Rerun the server and access `http://127.0.0.1:8000/`.

# Cách sử dụng:
- Mở command line trong thư mục này
- Chạy `pip install -r requirements.txt`.
- Chạy `python manage.py migrate`.
- Chạy `python manage.py createsuperuser`, tại trường username và password nhập "admin", những trường khác bỏ qua.
- QUAN TRỌNG: chạy `python manage.py runserver`, cú pháp này sẽ deploy django lên localhost, không tắt command line khi lệnh này đang chạy!
- Đăng nhập ở `http://127.0.0.1:8000/login/`.
- Truy cập trang `http://127.0.0.1:8000/admin/cameras/camera/` để thêm camera, trong phần thêm camera sẽ có 3 trường, "name" - tên camera, "url" - link camera, "path" - nơi lưu replay của camera.
- Nhấn "save" để lưu thông tin camera
- Truy cập `http://127.0.0.1:8000/` để xem camera.
# 10 — Nguồn kỹ thuật tham khảo

Các nguồn được dùng để kiểm tra thiết kế; thông tin giá chỉ để tham khảo tại ngày tra cứu 16/10/2026.

- [Datasheet HC-SR04, lưu tại SparkFun](https://cdn.sparkfun.com/datasheets/Sensors/Proximity/HCSR04.pdf): nguồn 5 V, trigger, chu kỳ đo và phạm vi danh định. Giá trị timeout 30 ms là lựa chọn firmware, không giả định mọi module clone tự timeout giống nhau.
- [ESP32 datasheet của Espressif](https://documentation.espressif.com/esp32_datasheet_en.html): điện áp và chân strapping; chú ý GPIO12/15/2 và các chân UART.
- [Camera pin definitions, Arduino-ESP32](https://github.com/espressif/arduino-esp32/blob/master/libraries/ESP32/examples/Camera/CameraWebServer/camera_pins.h): pinout AI Thinker và các model khác; không dùng lẫn pinout.
- [ESP32 camera driver](https://github.com/espressif/esp32-camera): API camera, JPEG và PSRAM.
- [Arduino-ESP32 LEDC](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/ledc.html): các timer/channel PWM; bộ mã dùng API LEDC của ESP-IDF để đặt timer rõ ràng.
- [ESP-IDF LEDC](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/peripherals/ledc.html): cấu hình timer/channel trực tiếp.
- [MPU6000/MPU6050 datasheet của TDK/InvenSense](https://invensense.tdk.com/wp-content/uploads/2015/02/MPU-6000-Datasheet.pdf): dải gia tốc và vận tốc góc. Thuật toán phát hiện gậy rơi trong gói là heuristic của dự án, không phải tính năng được datasheet bảo đảm.
- [TDK chọn piezo buzzer](https://product.tdk.com/en/products/selectionguide/piezo-buzzer.html): phân biệt cách kích và tính chất phát âm.
- [MDN getUserMedia](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia), [MDN watchPosition](https://developer.mozilla.org/en-US/docs/Web/API/Geolocation/watchPosition): quyền camera/GPS và secure context.
- [Cloudflare Quick Tunnels](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/): HTTPS tạm thời cho buổi demo, không phải cam kết vận hành lâu dài.
- [SegFormer Transformers](https://huggingface.co/docs/transformers/model_doc/segformer), [checkpoint SegFormer-B0 ADE20K](https://huggingface.co/nvidia/segformer-b0-finetuned-ade-512-512), [hướng dẫn semantic segmentation](https://huggingface.co/docs/transformers/tasks/semantic_segmentation): baseline và cách fine-tune.
- [Ultralytics segmentation](https://docs.ultralytics.com/tasks/segment/): hướng thay thế dùng mô hình YOLO segmentation với dữ liệu gán nhãn riêng.
- [Nshop NEO-6M 7N APM2.5](https://nshopvn.com/product/module-dinh-vi-gps-neo-6m-7n-apm2-5/): một giá tham khảo 220.000 đồng, không gồm mọi phần cứng/kết nối cần có cho định vị độc lập.

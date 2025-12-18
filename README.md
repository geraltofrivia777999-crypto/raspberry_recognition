# Raspberry Pi Face Recognition Door Control

Система распознавания лиц для управления дверным замком с использованием Raspberry Pi и InsightFace.

## Особенности

- Распознавание лиц с использованием InsightFace (buffalo_l модель)
- Управление GPIO17 для управления дверным замком
- Логика работы: GPIO17 всегда HIGH (дверь заблокирована), при распознавании лица - LOW (дверь разблокирована)
- Поддержка RTSP камер и USB камер
- Синхронизация данных с облачным сервером
- Кэширование данных для работы в оффлайн режиме

## Требования

- Raspberry Pi (рекомендуется Pi 4)
- Python 3.11
- USB камера или RTSP камера
- GPIO доступ для управления замком

## Установка

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd raspberry_recognition
```

### 2. Установка зависимостей

```bash
cd raspberry
pip install -r requirements.txt
```

**Важно**: Установка InsightFace может занять некоторое время и требует дополнительных системных зависимостей:

```bash
# Для Raspberry Pi OS
sudo apt-get update
sudo apt-get install -y libopenblas-dev liblapack-dev libjpeg-dev
```

### 3. Настройка конфигурации

Создайте файл `.env` в директории `raspberry/`:

```bash
cp raspberry/.env.example raspberry/.env
```

Отредактируйте `.env` файл с вашими настройками:

```env
API_BASE_URL=http://your-server:8000
DEVICE_ID=pi-001
MODEL_NAME=insightface
INSIGHTFACE_MODEL_NAME=buffalo_l
THRESHOLD=0.6
GPIO_PIN=17
GPIO_PULSE_MS=800
```

## Конфигурация GPIO

Система использует инвертированную логику для управления замком:

- **По умолчанию**: GPIO17 = HIGH (дверь заблокирована)
- **При распознавании**: GPIO17 = LOW на `gpio_pulse_ms` миллисекунд (дверь разблокирована)
- **После таймаута**: GPIO17 = HIGH (дверь снова заблокирована)

Эта логика подходит для нормально-закрытых (NC) электромагнитных замков.

## Использование

### Запуск с USB камерой (для тестов)

```bash
cd raspberry
python main_usb.py
```

### Запуск с RTSP камерой (для production)

Убедитесь, что в `.env` файле настроен `RTSP_URL`:

```env
RTSP_URL=rtsp://username:password@camera-ip:554/stream
```

Затем запустите:

```bash
cd raspberry
python main.py
```

## Модели распознавания

Проект поддерживает несколько моделей распознавания:

1. **InsightFace** (по умолчанию) - современная модель с высокой точностью
   - Модель: buffalo_l
   - Размерность эмбеддинга: 512
   - Требует больше ресурсов, но дает лучшие результаты

2. **FaceNet** (fallback) - ONNX модель
   - Требует файл `facenet.onnx`
   - Размерность эмбеддинга: 512

3. **Hashed** (для разработки) - детерминистическая модель на основе хэша
   - Не требует ML моделей
   - Используется только для тестирования

Переключение между моделями через параметр `MODEL_NAME` в `.env` файле.

## Структура проекта

```
raspberry/
├── main.py                      # Основной файл для RTSP
├── main_usb.py                  # Основной файл для USB камеры
├── config.py                    # Конфигурация
├── pipeline.py                  # Основная логика распознавания
├── gpio_controller.py           # Управление GPIO
├── insightface_recognizer.py    # InsightFace recognizer
├── facenet_recognizer.py        # FaceNet recognizer
├── model_registry.py            # Регистр моделей
├── rtsp_client.py               # RTSP клиент
├── usb_camera_client.py         # USB камера клиент
├── sync_client.py               # Синхронизация с сервером
├── cache.py                     # Кэширование данных
└── requirements.txt             # Зависимости
```

## Тестирование

### Тест камеры и загрузки на сервер

```bash
cd raspberry
python capture_uploader_test.py --name test-user --camera-index 0
```

### Тест синхронизации с сервером

```bash
cd raspberry
python debug_sync.py --server http://your-server:8000 --limit 3
```

## Автозапуск (systemd)

Создайте файл `/etc/systemd/system/face-recognition.service`:

```ini
[Unit]
Description=Face Recognition Door Control
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/raspberry_recognition/raspberry
ExecStart=/usr/bin/python3 main_usb.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Включите автозапуск:

```bash
sudo systemctl daemon-reload
sudo systemctl enable face-recognition.service
sudo systemctl start face-recognition.service
```

## Устранение неполадок

### GPIO не работает

1. Убедитесь, что у пользователя есть права на GPIO:
   ```bash
   sudo usermod -a -G gpio $USER
   ```

2. Проверьте, что gpiod установлен:
   ```bash
   pip show gpiod
   ```

### InsightFace не загружается

1. Проверьте установку зависимостей:
   ```bash
   pip install insightface --no-cache-dir
   ```

2. Убедитесь, что модель buffalo_l загружена (первый запуск загрузит автоматически)

### Камера не захватывает изображение

1. Проверьте индекс USB камеры:
   ```bash
   ls /dev/video*
   ```

2. Для RTSP проверьте доступность потока:
   ```bash
   ffplay rtsp://your-camera-url
   ```

## Лицензия

MIT

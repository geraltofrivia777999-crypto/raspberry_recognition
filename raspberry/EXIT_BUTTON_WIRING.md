# Подключение кнопки выхода "ВЫХОД"

## 📋 Что нужно:

1. Кнопка выхода (Exit Button) - любая кнопка NO (Normally Open)
2. 2 провода
3. Raspberry Pi с GPIO

## 🔌 Схема подключения:

```
┌─────────────────────┐
│   Кнопка "ВЫХОД"    │
│                     │
│  [NO]      [COM]    │  NO = Normally Open (нормально разомкнут)
│   │         │       │  COM = Common (общий)
└───┼─────────┼───────┘
    │         │
    │         │
    ▼         ▼
┌───────────────────────────┐
│    Raspberry Pi GPIO      │
│                           │
│  GPIO27 ────────┘         │  Любой свободный GPIO (по умолчанию 27)
│                           │
│  GND ────────────────┘    │  Земля
│                           │
└───────────────────────────┘
```

## 📝 Пошаговая инструкция:

### 1. **Выключите Raspberry Pi**
```bash
sudo shutdown -h now
```

### 2. **Подключите провода:**

| Кнопка | → | Raspberry Pi GPIO |
|--------|---|-------------------|
| NO (нормально разомкнут) | → | **GPIO27** (pin 13) |
| COM (общий) | → | **GND** (pin 6, 9, 14, 20, 25, 30, 34, 39) |

**Важно:**
- Используйте **любой свободный GPIO** (можно изменить в настройках)
- Используйте **любой GND** пин на Raspberry Pi
- **НЕ ПОДКЛЮЧАЙТЕ к 3.3V или 5V!**

### 3. **Проверьте подключение:**

После включения Raspberry Pi:

```bash
# Проверить что GPIO27 доступен
ls /dev/gpiochip0

# Установить права (если нужно)
sudo usermod -a -G gpio $USER
sudo chmod 666 /dev/gpiochip0
```

### 4. **Настройте программу:**

В файле `.env`:
```env
# Включить кнопку выхода
EXIT_BUTTON_ENABLED=true

# GPIO пин для кнопки (измените если используете другой пин)
EXIT_BUTTON_PIN=27

# Задержка anti-bounce (обычно не нужно менять)
EXIT_BUTTON_DEBOUNCE_MS=200
```

### 5. **Запустите программу:**

```bash
cd ~/Desktop/recognition
python main_usb.py
```

## 🎯 Как это работает:

1. **В покое:** Кнопка разомкнута, GPIO27 = HIGH (подтянут резистором PULL_UP)
2. **При нажатии:** Контакты замыкаются, GPIO27 → GND = LOW
3. **Программа:** Обнаруживает LOW, вызывает `controller.gpio.trigger()`
4. **Замок:** Открывается на `GPIO_PULSE_MS` миллисекунд (по умолчанию 800мс)
5. **После отпускания:** Кнопка размыкается, GPIO27 = HIGH снова

## 🔍 Диагностика:

### Кнопка не работает:

```bash
# 1. Проверить что кнопка включена в логах
python main_usb.py
# Должно быть: [INFO] Exit button started on GPIO pin 27

# 2. Проверить настройки
cat .env | grep EXIT_BUTTON

# 3. Проверить GPIO вручную
python3 << EOF
import gpiod
chip = gpiod.Chip('/dev/gpiochip0')
line = chip.request_lines(
    consumer='test',
    config={27: gpiod.LineSettings(direction=gpiod.line.Direction.INPUT, bias=gpiod.line.Bias.PULL_UP)}
)
print("Не нажата:", line.get_value(27))  # Should be ACTIVE (1)
# Нажмите кнопку
import time; time.sleep(2)
print("Нажата:", line.get_value(27))  # Should be INACTIVE (0)
EOF
```

### Ложные срабатывания:

Увеличьте `EXIT_BUTTON_DEBOUNCE_MS`:
```env
EXIT_BUTTON_DEBOUNCE_MS=500  # 500мс вместо 200мс
```

## 📌 Альтернативные GPIO пины:

Если GPIO27 занят, используйте любой свободный:

| GPIO пин | Physical pin |
|----------|--------------|
| GPIO22   | 15           |
| GPIO23   | 16           |
| GPIO24   | 18           |
| GPIO25   | 22           |
| GPIO27   | 13 (по умолчанию) |

Измените в `.env`:
```env
EXIT_BUTTON_PIN=22  # Используем GPIO22 вместо GPIO27
```

## ⚠️ Важно:

- **НЕ используйте GPIO17** - он управляет замком
- **НЕ подключайте к 3.3V или 5V** - только к GND
- **Используйте NO контакт** (нормально разомкнут), не NC
- **Полярность не важна** - кнопка просто замыкает контакты

## 🎉 Готово!

Теперь при нажатии кнопки "ВЫХОД" дверь будет открываться на заданное время!

# Автоматизация регистрации LC Waikiki с приемом SMS через Simroute API

Данный проект реализует решение тестового задания на позицию **Automation Developer**:
1. Получение виртуального номера телефона через **Simroute API** (`HandlerApiController`).
2. Автоматическое заполнение формы регистрации на сайте **LC Waikiki** через **Playwright** с распознаванием капчи.
3. Проставление чекбоксов согласия: **SMS** (`<span class="checkbox__label">SMS</span>`) и **Privacy Policy**.
4. Инициация отправки SMS-кода подтверждения.
5. Ожидание и прием входящего SMS с кодом подтверждения от LC Waikiki через Simroute API.
6. Ввод SMS-кода в форму и завершение активации (или корректная отмена при ошибках для возврата средств).

---

## 🛠 Архитектура проекта

```
SC/
├── main.py                    # Корневая точка входа
├── src/
│   ├── main.py                # Главный сценарий сквозного выполнения (оркестратор)
│   ├── automation/            # Автоматизация бизнес-процессов
│   │   ├── __init__.py
│   │   └── lcw_registration.py# Автоматизация регистрации LC Waikiki (Playwright)
│   ├── browser/               # Управление жизненным циклом браузера
│   │   ├── __init__.py
│   │   └── manager.py         # Инициализация Playwright с anti-detect параметрами
│   ├── captcha/               # Модуль распознавания капчи
│   │   ├── __init__.py
│   │   ├── preprocessing.py   # OpenCV предобработка (Otsu + median blur)
│   │   ├── ollama_solver.py   # Распознавание капчи через OllamaApiClient
│   │   └── ddddocr_solver.py  # Распознавание через ddddocr (ансамбль base + beta)
│   ├── external_apis/         # Внешние API-клиенты
│   │   ├── __init__.py
│   │   ├── ollama/            # Клиент к локальной/удаленной нейросети Ollama
│   │   │   ├── __init__.py
│   │   │   ├── client.py      # OllamaApiClient (is_online, models, generate, solve_captcha)
│   │   │   ├── errors.py      # Иерархия исключений OllamaError
│   │   │   └── schemas.py     # Модели данных ответа Ollama
│   │   └── simroute/          # Клиент к сервису приема SMS Simroute
│   │       ├── __init__.py
│   │       ├── client.py      # SimrouteApiClient (JSON API)
│   │       ├── errors.py      # Иерархия исключений SimrouteError
│   │       └── schemas.py     # ActivationNumber, SmsStatusResult
│   └── config/                # Конфигурация Pydantic Settings
│       ├── __init__.py        # Экспорт инстансов настроек
│       ├── browser.py         # Настройки браузера
│       ├── ollama.py          # Настройки Ollama
│       ├── lcw.py             # Настройки сайта LC Waikiki
│       └── simroute.py        # Настройки Simroute API
├── docker-compose.yml         # Контейнер Ollama для локального решения капч
├── .env                       # Рабочие переменные окружения
├── .env.example               # Шаблон переменных окружения
└── pyproject.toml             # Зависимости и метаданные проекта
```

---

## 🤖 Решение капчи через Docker (Ollama)

Для бесплатного решения капч с высокой точностью подготовлен Docker-контейнер с Ollama:

1. **Запуск контейнера**:
```powershell
docker compose up -d
```

2. **Загрузка модели внутрь контейнера**:
```powershell
docker exec -it sc-ollama ollama pull glm-ocr:latest
```

Контейнер доступен на `http://localhost:11434`. Клиент `OllamaApiClient` проверяет доступность сервиса через `/api/ps`. Если сервис Ollama недоступен или выключен, автоматизация автоматически откатывается на локальный ансамбль `ddddocr` с предобработкой OpenCV.

---

## ⚙️ Конфигурация (`.env`)

Все параметры вынесены в переменные окружения:

| Переменная | Описание | Пример значения |
|---|---|---|
| `SIMROUTE_BASE_URL` | URL эндпоинта Handler API | `https://simroute.pro/api/stubs/handler_api.php` |
| `SIMROUTE_API_KEY` | API-ключ пользователя | Указывается в `.env` |
| `SIMROUTE_COUNTRY_ID` | ID страны в Simroute | `47` (Ирак, +964) |
| `SIMROUTE_SERVICE_CODE` | Код сервиса в Simroute | `lcw` (LC Waikiki) |
| `LCW_DOMAIN` | Домен LC Waikiki | `www.lcwaikiki.iq` |
| `LCW_SCHEME` | Протокол сайта | `https` |
| `LCW_REGISTER_PATH` | Путь страницы регистрации | `/en/register` |
| `HEADLESS` | Запуск браузера без GUI | `false` |
| `BROWSER_CHANNEL` | Канал браузера | `chrome` |
| `OLLAMA_ENABLED` | Использовать ли Ollama | `true` |
| `OLLAMA_URL` | URL API Ollama | `http://localhost:11434/api/generate` |
| `OLLAMA_MODEL` | Модель Ollama | `glm-ocr:latest` |
| `SIMROUTE_SMS_WAIT_TIMEOUT` | Таймаут ожидания SMS (сек) | `180` |
| `SIMROUTE_SMS_POLL_INTERVAL` | Интервал опроса статуса SMS (сек) | `4` |

---

## 🚀 Запуск сценария и методы управления

### Вариант 1: Через консольную утилиту `lcw` (Рекомендуется)

После установки в виртуальное окружение доступна команда `lcw`:

```powershell
# 1. Диагностика внешних сервисов (Simroute, Ollama, домен)
lcw check

# 2. Быстрая проверка баланса Simroute
lcw balance

# 3. Запуск автоматизации регистрации
lcw run

# Запуск с флагами командной строки:
lcw run --headless               # Фоновый режим (без открытия окна браузера)
lcw run --no-headless            # С видимым графическим окном
lcw run --no-ollama              # Принудительно без Ollama (только ddddocr)
lcw run --domain www.lcwaikiki.iq # Переопределение домена
```

> **Примечание по PowerShell:** В Windows PowerShell имя `sc` является встроенным системным алиасом для командлета `Set-Content`. Поэтому для вызова утилиты используйте команду **`lcw`** (или `python -m src`).

### Вариант 2: Запуск как Python-модуль
```powershell
python -m src run
python -m src check
python -m src balance
```

### Вариант 3: Классический запуск скрипта
```powershell
python main.py
python main.py check
```

---

## 🐳 Контейнеризация (Docker)

Проект поддерживает два гибких сценария работы:

### 1. Гибридный режим (локальный скрипт + Docker Ollama)
Поднимаем только контейнер с нейросетью:
```powershell
docker compose up -d ollama
```
И запускаем автоматизацию на хосте с графическим окном:
```powershell
sc run --no-headless
```

### 2. Полный запуск в Docker (Headless)
Сборка и запуск всего стека (Playwright + Ollama) в изолированной docker-сети `sc_network`:
```powershell
# Сборка и запуск контейнеров
docker compose up --build -d

# Просмотр логов автоматизации
docker compose logs -f app
```
Или однократный запуск задачи внутри контейнера:
```powershell
docker compose run --rm app check
docker compose run --rm app run
```

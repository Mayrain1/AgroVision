# AgroVision

Базовый full-stack проект для тренировочного AI-хакатона.

## Структура

```text
agrovision/
├── frontend/
└── backend/
```

## Backend

FastAPI-сервер с endpoint `POST /api/analyze`. Backend принимает multipart-поля `crop`, `description`, `city`, необязательную `area_ha` и изображение. Для города backend получает координаты через Geocoding Service, затем запрашивает 14 дней истории и 7 дней прогноза через Weather Service и передаёт этот контекст в один запрос OpenAI Responses API.

```json
{
  "problem": {
    "name": "string",
    "confidence": 0.78
  },
  "solutions": ["string"],
  "calculation": {
    "needed": true,
    "fertilizer": "Название удобрения",
    "application_rate_kg_per_ha": 120,
    "area_ha": 50,
    "total_amount_kg": 6000
  },
  "follow_up_question": "string"
}
```

Если удобрение не требуется, `calculation` равен `null`. Норма внесения может быть рекомендована AI, а `total_amount_kg` всегда вычисляется backend как `area_ha * application_rate_kg_per_ha`.

Endpoint `GET /api/weather?city=...` сохранён для отображения погодного блока. В основном сценарии отдельное действие получения погоды не требуется.

### Установка зависимостей

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Переменная окружения

Создайте переменную `OPENAI_API_KEY` на backend-машине. Ключ не нужен во frontend и не должен попадать в код.

PowerShell:

```powershell
$env:OPENAI_API_KEY="your_key_here"
```

CMD:

```cmd
set OPENAI_API_KEY=your_key_here
```

Пример также есть в `backend/.env.example`.

### Запуск

```bash
uvicorn main:app --reload
```

Backend будет доступен по адресу:

```text
http://localhost:8000
```

## Frontend

React + Vite приложение с формой для ввода культуры, описания проблемы, города/региона и площади поля. Загрузка изображения поддерживает JPG, PNG и WEBP до 5 МБ.

### Запуск

```bash
cd frontend
npm install
npm run dev
```

Frontend будет доступен по адресу, который покажет Vite, обычно:

```text
http://localhost:5173
```

## Проверка

1. Запустите backend с заданным `OPENAI_API_KEY`.
2. Запустите frontend.
3. Откройте frontend в браузере.
4. Введите культуру, описание, город и при необходимости площадь поля.
5. Нажмите "Анализировать".

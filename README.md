# AgroVision

Базовый full-stack проект для тренировочного AI-хакатона.

## Структура

```text
agrovision/
├── frontend/
└── backend/
```

## Backend

FastAPI-сервер с endpoint `POST /api/analyze`. Backend принимает `crop` и `description`, отправляет text-only запрос в OpenAI Responses API и возвращает frontend строгий JSON:

```json
{
  "problem": {
    "name": "string",
    "confidence": 0.78
  },
  "solutions": ["string"],
  "calculation": null,
  "follow_up_question": "string"
}
```

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

React + Vite приложение с формой для ввода культуры и описания проблемы.

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
4. Введите crop и description.
5. Нажмите "Анализировать".

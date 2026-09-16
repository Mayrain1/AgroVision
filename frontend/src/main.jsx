import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_URL = "http://localhost:8000/api/analyze";

function App() {
  const [crop, setCrop] = useState("");
  const [description, setDescription] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setResult(null);
    setIsLoading(true);

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          crop,
          description,
        }),
      });

      if (!response.ok) {
        throw new Error("Backend вернул ошибку");
      }

      const data = await response.json();
      setResult(data);
    } catch (requestError) {
      setError("Не удалось получить анализ. Проверьте, что backend запущен.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="page">
      <section className="app-shell">
        <div className="intro">
          <p className="eyebrow">AI Hackathon Starter</p>
          <h1>AgroVision</h1>
          <p>
            Быстрый анализ состояния культуры по описанию симптомов. Сейчас
            используется mock-ответ backend.
          </p>
        </div>

        <form className="analysis-form" onSubmit={handleSubmit}>
          <label>
            Crop
            <input
              type="text"
              value={crop}
              onChange={(event) => setCrop(event.target.value)}
              placeholder="Например: Пшеница"
              required
            />
          </label>

          <label>
            Description
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Опишите признаки, цвет листьев, стадию роста..."
              rows="5"
              required
            />
          </label>

          <button type="submit" disabled={isLoading}>
            {isLoading ? "Анализ..." : "Анализировать"}
          </button>
        </form>

        {error && <p className="error">{error}</p>}

        {result && (
          <section className="result">
            <h2>Результат анализа</h2>
            <div className="result-grid">
              <div>
                <span>Проблема</span>
                <strong>{result.problem.name}</strong>
              </div>
              <div>
                <span>Уверенность</span>
                <strong>{Math.round(result.problem.confidence * 100)}%</strong>
              </div>
            </div>

            <h3>Рекомендации</h3>
            <ul>
              {result.solutions.map((solution) => (
                <li key={solution}>{solution}</li>
              ))}
            </ul>

            <h3>Уточняющий вопрос</h3>
            <p>{result.follow_up_question}</p>
          </section>
        )}
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);

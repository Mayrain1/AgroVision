import React, { useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_URL = "http://localhost:8000/api/analyze";
const MAX_IMAGE_SIZE = 5 * 1024 * 1024;
const ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];

function App() {
  const [crop, setCrop] = useState("");
  const [description, setDescription] = useState("");
  const [image, setImage] = useState(null);
  const [imagePreview, setImagePreview] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const fileInputRef = useRef(null);

  function clearImage() {
    if (imagePreview) {
      URL.revokeObjectURL(imagePreview);
    }

    setImage(null);
    setImagePreview("");

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  function handleImageChange(event) {
    const file = event.target.files?.[0];
    setError("");

    if (!file) {
      clearImage();
      return;
    }

    if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
      clearImage();
      event.target.value = "";
      setError("Загрузите изображение в формате JPG, PNG или WEBP.");
      return;
    }

    if (file.size > MAX_IMAGE_SIZE) {
      clearImage();
      event.target.value = "";
      setError("Файл слишком большой. Максимальный размер изображения - 5 МБ.");
      return;
    }

    if (imagePreview) {
      URL.revokeObjectURL(imagePreview);
    }

    setImage(file);
    setImagePreview(URL.createObjectURL(file));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setResult(null);

    if (!image) {
      setError("Добавьте фотографию растения перед анализом.");
      return;
    }

    setIsLoading(true);

    try {
      const formData = new FormData();
      formData.append("crop", crop);
      formData.append("description", description);
      formData.append("image", image);

      const response = await fetch(API_URL, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || "Backend вернул ошибку.");
      }

      const data = await response.json();
      setResult(data);
    } catch (requestError) {
      setError(
        requestError.message ||
          "Не удалось получить анализ. Проверьте, что backend запущен."
      );
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
            Предварительный анализ состояния культуры по фотографии растения,
            названию культуры и описанию симптомов.
          </p>
        </div>

        <form className="analysis-form" onSubmit={handleSubmit}>
          <div className="image-field">
            <span className="field-title">Фотография растения</span>
            <label className="upload-box">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={handleImageChange}
              />
              <span>Загрузить фотографию</span>
              <small>JPG, PNG или WEBP до 5 МБ</small>
            </label>

            {imagePreview && (
              <div className="preview">
                <img src={imagePreview} alt="Выбранное растение" />
                <div className="preview-actions">
                  <span>{image.name}</span>
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={clearImage}
                  >
                    Удалить
                  </button>
                </div>
              </div>
            )}
          </div>

          <label>
            Культура
            <input
              type="text"
              value={crop}
              onChange={(event) => setCrop(event.target.value)}
              placeholder="Например: Пшеница"
              required
            />
          </label>

          <label>
            Описание симптомов
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

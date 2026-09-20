import { useState } from "react";
import ImageUpload, {
  ALLOWED_IMAGE_TYPES,
  MAX_IMAGE_SIZE,
} from "./ImageUpload";

const API_URL = "http://localhost:8000/api/analyze";

function AnalysisForm({ city, onCityChange, onAnalysisStart, onResult }) {
  const [crop, setCrop] = useState("");
  const [description, setDescription] = useState("");
  const [areaHa, setAreaHa] = useState("");
  const [image, setImage] = useState(null);
  const [imagePreview, setImagePreview] = useState("");
  const [imageError, setImageError] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  function clearImage(input) {
    if (imagePreview) {
      URL.revokeObjectURL(imagePreview);
    }
    setImage(null);
    setImagePreview("");
    if (input) input.value = "";
  }

  function handleImageChange(file, input) {
    setImageError("");

    if (!file) {
      clearImage(input);
      return;
    }

    if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
      clearImage(input);
      if (input) input.value = "";
      setImageError("Загрузите изображение в формате JPG, PNG или WEBP.");
      return;
    }

    if (file.size > MAX_IMAGE_SIZE) {
      clearImage(input);
      if (input) input.value = "";
      setImageError("Файл слишком большой. Максимальный размер изображения - 5 МБ.");
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
    onAnalysisStart();

    if (!image) {
      setError("Добавьте фотографию растения перед анализом.");
      return;
    }

    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append("crop", crop);
      formData.append("description", description);
      formData.append("city", city);
      if (areaHa) formData.append("area_ha", areaHa);
      formData.append("image", image);

      const response = await fetch(API_URL, { method: "POST", body: formData });
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || "Backend вернул ошибку.");
      }
      onResult(await response.json());
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
    <form className="analysis-form" onSubmit={handleSubmit}>
      <ImageUpload
        image={image}
        imagePreview={imagePreview}
        onImageChange={handleImageChange}
        onClear={(input) => clearImage(input)}
        error={imageError}
      />

      <div className="form-fields">
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
          Город или регион
          <input
            type="text"
            value={city}
            onChange={(event) => onCityChange(event.target.value)}
            placeholder="Например: Усть-Каменогорск"
            required
          />
        </label>

        <label>
          Площадь поля, га (необязательно)
          <input
            type="number"
            min="0.01"
            step="0.01"
            value={areaHa}
            onChange={(event) => setAreaHa(event.target.value)}
            placeholder="Например: 50"
          />
        </label>

        <label>
          Описание симптомов
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Цвет листьев, пятна, стадия роста..."
            rows="6"
            required
          />
        </label>

        {error && <p className="error">{error}</p>}

        <button className="primary-button" type="submit" disabled={isLoading}>
          <span>{isLoading ? "Анализируем..." : "Анализировать растение"}</span>
          {!isLoading && <span aria-hidden="true">-&gt;</span>}
        </button>
      </div>
    </form>
  );
}

export default AnalysisForm;
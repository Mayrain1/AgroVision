import { useRef } from "react";

const MAX_IMAGE_SIZE = 5 * 1024 * 1024;
const ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];

function ImageUpload({ image, imagePreview, onImageChange, onClear, error }) {
  const fileInputRef = useRef(null);

  function handleChange(event) {
    onImageChange(event.target.files?.[0] || null, fileInputRef.current);
  }

  return (
    <div className="image-field">
      <div className="field-heading">
        <span className="field-title">Фотография растения</span>
        <span className="field-hint">Обязательно</span>
      </div>

      {!imagePreview ? (
        <label className="upload-box">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={handleChange}
          />
          <span className="upload-icon" aria-hidden="true">+</span>
          <span>Загрузить фотографию</span>
          <small>JPG, PNG или WEBP до 5 МБ</small>
        </label>
      ) : (
        <div className="preview">
          <img src={imagePreview} alt="Выбранное растение" />
          <div className="preview-actions">
            <div>
              <span className="preview-label">Выбранный файл</span>
              <strong>{image.name}</strong>
            </div>
            <div className="preview-buttons">
              <button
                type="button"
                className="secondary-button"
                onClick={() => fileInputRef.current?.click()}
              >
                Заменить
              </button>
              <button
                type="button"
                className="text-button"
                onClick={() => onClear(fileInputRef.current)}
              >
                Удалить
              </button>
            </div>
          </div>
          <input
            ref={fileInputRef}
            className="hidden-file-input"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={handleChange}
          />
        </div>
      )}

      {error && <p className="field-error">{error}</p>}
    </div>
  );
}

export { ALLOWED_IMAGE_TYPES, MAX_IMAGE_SIZE };
export default ImageUpload;
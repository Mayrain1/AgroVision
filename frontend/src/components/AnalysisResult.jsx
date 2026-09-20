function AnalysisResult({ result }) {
  if (!result) return null;

  return (
    <section className="content-section result-section" aria-labelledby="result-title">
      <div className="section-heading">
        <div>
          <p className="section-kicker">Ваш отчёт</p>
          <h2 id="result-title">Результат анализа</h2>
        </div>
        <span className="section-number">03</span>
      </div>

      <div className="result-overview">
        <div className="problem-card">
          <span>Возможная проблема</span>
          <strong>{result.problem.name}</strong>
        </div>
        <div className="confidence-card">
          <span>Уверенность модели</span>
          <strong>{Math.round(result.problem.confidence * 100)}%</strong>
          <div className="confidence-bar" aria-hidden="true">
            <span style={{ width: `${result.problem.confidence * 100}%` }} />
          </div>
        </div>
      </div>

      <div className="result-details">
        <div>
          <h3>Рекомендации</h3>
          <ol>
            {result.solutions.map((solution) => <li key={solution}>{solution}</li>)}
          </ol>
        </div>
        <div className="follow-up">
          <h3>Уточняющий вопрос</h3>
          <p>{result.follow_up_question}</p>
        </div>
      </div>

      {result.calculation && (
        <div className="calculation-block">
          <h3>Расчёт удобрения</h3>
          <div className="calculation-grid">
            <div>
              <span>Удобрение</span>
              <strong>{result.calculation.fertilizer}</strong>
            </div>
            <div>
              <span>Площадь</span>
              <strong>{result.calculation.area_ha} га</strong>
            </div>
            <div>
              <span>Норма</span>
              <strong>{result.calculation.application_rate_kg_per_ha} кг/га</strong>
            </div>
            <div>
              <span>Необходимо</span>
              <strong>{result.calculation.total_amount_kg} кг</strong>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

export default AnalysisResult;
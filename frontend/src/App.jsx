import { useState } from "react";
import Header from "./components/Header";
import AnalysisForm from "./components/AnalysisForm";
import WeatherPanel from "./components/WeatherPanel";
import AnalysisResult from "./components/AnalysisResult";

function App() {
  const [result, setResult] = useState(null);
  const [city, setCity] = useState("Усть-Каменогорск");

  function handleAnalysisStart() {
    setResult(null);
  }

  return (
    <main className="page">
      <div className="app-shell">
        <Header />

        <section className="content-section analysis-section" aria-labelledby="analysis-title">
          <div className="section-heading">
            <div>
              <p className="section-kicker">AI-анализ растения</p>
              <h2 id="analysis-title">Проверьте состояние культуры</h2>
            </div>
            <span className="section-number">01</span>
          </div>
          <AnalysisForm
            city={city}
            onCityChange={setCity}
            onAnalysisStart={handleAnalysisStart}
            onResult={setResult}
          />
        </section>

        <WeatherPanel city={city} />

        <AnalysisResult result={result} />
      </div>
    </main>
  );
}

export default App;
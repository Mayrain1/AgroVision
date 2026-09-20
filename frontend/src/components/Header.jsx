function Header() {
  return (
    <header className="header">
      <div className="brand-mark" aria-hidden="true">A</div>
      <div className="brand-copy">
        <p className="eyebrow">Agricultural intelligence</p>
        <h1>AgroVision</h1>
      </div>
      <p className="header-description">
        Понятные подсказки для точных решений о здоровье ваших культур.
      </p>
    </header>
  );
}

export default Header;
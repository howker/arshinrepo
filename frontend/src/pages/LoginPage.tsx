export function LoginPage() {
  return (
    <section className="page">
      <div className="page-header">
        <span className="eyebrow">Auth</span>
        <h1 className="page-title">Вход в систему</h1>
        <p className="muted">
          На этом шаге мы создаём только UI-оболочку страницы логина без вызова API.
        </p>
      </div>

      <div className="card form-card">
        <div className="form-grid">
          <label className="field">
            <span className="field-label">Email</span>
            <input type="email" placeholder="admin@arshin.local" disabled />
          </label>

          <label className="field">
            <span className="field-label">Пароль</span>
            <input type="password" placeholder="••••••••" disabled />
          </label>

          <button className="primary-button" type="button" disabled>
            Войти
          </button>
        </div>
      </div>
    </section>
  );
}

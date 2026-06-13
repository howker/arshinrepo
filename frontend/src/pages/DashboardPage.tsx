export function DashboardPage() {
  return (
    <section className="page">
      <div className="page-header">
        <span className="eyebrow">Overview</span>
        <h1 className="page-title">Dashboard</h1>
        <p className="muted">
          Здесь будут summary-метрики, последние job и быстрые действия пользователя.
        </p>
      </div>

      <div className="stat-grid">
        <article className="stat-card">
          <span className="stat-label">Jobs total</span>
          <strong className="stat-value">0</strong>
          <span className="muted">Пока без live API</span>
        </article>

        <article className="stat-card">
          <span className="stat-label">Completed</span>
          <strong className="stat-value">0</strong>
          <span className="muted">После интеграции с `/api/jobs`</span>
        </article>

        <article className="stat-card">
          <span className="stat-label">Issues</span>
          <strong className="stat-value">0</strong>
          <span className="muted">Будет считаться по job issues</span>
        </article>
      </div>

      <article className="card">
        <h2 className="section-title">Следующие блоки</h2>
        <ul className="list">
          <li>Auth store и token flow.</li>
          <li>Jobs list с данными backend.</li>
          <li>Upload form и экран деталей job.</li>
        </ul>
      </article>
    </section>
  );
}

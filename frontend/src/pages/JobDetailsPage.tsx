import { Link, useParams } from 'react-router-dom';

export function JobDetailsPage() {
  const { jobId } = useParams();

  return (
    <section className="page">
      <div className="page-header">
        <span className="eyebrow">Job details</span>
        <h1 className="page-title">Job {jobId}</h1>
        <p className="muted">
          Экран деталей уже выделен, но данные позже будут приходить из API.
        </p>
      </div>

      <div className="page-grid">
        <article className="card">
          <h2 className="section-title">Статус обработки</h2>
          <div className="progress-shell">
            <div className="progress-bar" style={{ width: '42%' }} />
          </div>
          <p className="muted">Placeholder progress: 42%.</p>
        </article>

        <article className="card">
          <h2 className="section-title">Навигация</h2>
          <div className="action-row">
            <Link className="link" to="/jobs">
              Назад к списку jobs
            </Link>
          </div>
        </article>
      </div>
    </section>
  );
}

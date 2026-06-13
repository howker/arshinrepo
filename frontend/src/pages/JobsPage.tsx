import { Link } from 'react-router-dom';

const demoJobs = [
  { id: 'demo-001', status: 'uploaded', file: 'meters-batch-01.xlsx' },
  { id: 'demo-002', status: 'processing', file: 'meters-batch-02.xlsx' },
  { id: 'demo-003', status: 'completed_with_issues', file: 'meters-batch-03.xlsx' }
];

export function JobsPage() {
  return (
    <section className="page">
      <div className="page-header">
        <span className="eyebrow">Jobs</span>
        <h1 className="page-title">Список проверок</h1>
        <p className="muted">
          Пока это статический список-заглушка для сборки экранов и навигации.
        </p>
      </div>

      <div className="card">
        <div className="table-like">
          <div className="table-row table-head">
            <span>Job ID</span>
            <span>Файл</span>
            <span>Статус</span>
            <span>Действие</span>
          </div>

          {demoJobs.map((job) => (
            <div className="table-row" key={job.id}>
              <span className="mono">{job.id}</span>
              <span>{job.file}</span>
              <span>
                <span className="badge">{job.status}</span>
              </span>
              <span>
                <Link className="link" to={`/jobs/${job.id}`}>
                  Открыть
                </Link>
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

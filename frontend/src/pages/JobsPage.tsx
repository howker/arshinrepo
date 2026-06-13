import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { jobsApi, Job } from '../shared/api/jobs';
import { useAuthStore } from '../features/auth/store';

export function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const navigate = useNavigate();

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }

    const fetchJobs = async () => {
      try {
        const data = await jobsApi.getJobs();
        setJobs(data);
      } catch (err: any) {
        setError('Не удалось загрузить список задач.');
        if (err.response?.status === 401) {
          navigate('/login');
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchJobs();
  }, [isAuthenticated, navigate]);

  return (
    <section className="page">
      <div className="page-header">
        <span className="eyebrow">Jobs</span>
        <h1 className="page-title">Список проверок</h1>
        <p className="muted">
          Реальные данные из базы данных PostgreSQL.
        </p>
      </div>

      <div className="card">
        {error && <div style={{ color: '#ef4444', marginBottom: '16px' }}>{error}</div>}
        
        {isLoading ? (
          <p className="muted">Загрузка данных...</p>
        ) : jobs.length === 0 ? (
          <p className="muted">У вас пока нет загруженных задач. Перейдите на Dashboard для загрузки.</p>
        ) : (
          <div className="table-like">
            <div className="table-row table-head">
              <span>Файл</span>
              <span>Прогресс</span>
              <span>Ошибки</span>
              <span>Статус</span>
              <span>Действие</span>
            </div>

            {jobs.map((job) => (
              <div className="table-row" key={job.id}>
                <span>{job.original_filename}</span>
                <span className="muted">{job.processed_items} / {job.total_items}</span>
                <span style={{ color: job.issue_count > 0 ? '#ef4444' : 'inherit' }}>
                  {job.issue_count}
                </span>
                <span>
                  <span className={`badge ${job.status === 'failed' ? 'bg-red-100 text-red-800' : ''}`}>
                    {job.status}
                  </span>
                </span>
                <span>
                  <Link className="link" to={`/jobs/${job.id}`}>
                    Открыть
                  </Link>
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

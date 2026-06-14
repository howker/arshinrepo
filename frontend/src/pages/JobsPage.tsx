import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { jobsApi, Job } from '../shared/api/jobs';

export function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const data = await jobsApi.getJobs();
        // Сортируем так, чтобы новые задачи были сверху
        const sorted = data.sort((a, b) => {
          if (!a.created_at || !b.created_at) return 0;
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        });
        setJobs(sorted);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Ошибка при загрузке списка задач');
      } finally {
        setIsLoading(false);
      }
    };

    fetchJobs();
  }, []);

  return (
    <section className="page">
      <div className="page-header">
        <span className="eyebrow">History</span>
        <h1 className="page-title">История проверок</h1>
        <p className="muted">Список всех загруженных файлов и их статусы.</p>
      </div>

      <div className="card">
        {isLoading ? (
          <p className="muted">Загрузка данных...</p>
        ) : error ? (
          <div style={{ color: '#ef4444' }}>{error}</div>
        ) : jobs.length === 0 ? (
          <p className="muted">Вы еще не загружали файлы. Перейдите в Dashboard для создания первой проверки.</p>
        ) : (
          <div className="table-container" style={{ overflowX: 'auto' }}>
            <table className="data-table" style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  <th style={{ padding: '12px 8px' }}>Файл</th>
                  <th style={{ padding: '12px 8px' }}>Статус</th>
                  <th style={{ padding: '12px 8px' }}>Прогресс</th>
                  <th style={{ padding: '12px 8px' }}>Ошибки</th>
                  <th style={{ padding: '12px 8px' }}>Действия</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '12px 8px', fontWeight: 500 }}>{job.original_filename}</td>
                    <td style={{ padding: '12px 8px' }}>
                      <span style={{ 
                        padding: '4px 8px', 
                        borderRadius: '4px', 
                        fontSize: '12px',
                        backgroundColor: job.status === 'completed' ? '#dcfce7' : job.status === 'failed' ? '#fee2e2' : '#f3f4f6',
                        color: job.status === 'completed' ? '#166534' : job.status === 'failed' ? '#991b1b' : '#1f2937'
                      }}>
                        {job.status}
                      </span>
                    </td>
                    <td style={{ padding: '12px 8px' }}>
                      {job.processed_items} / {job.total_items}
                    </td>
                    <td style={{ padding: '12px 8px' }}>
                      {job.issue_count > 0 ? (
                        <span style={{ color: '#ef4444', fontWeight: 600 }}>{job.issue_count}</span>
                      ) : (
                        <span className="muted">0</span>
                      )}
                    </td>
                    <td style={{ padding: '12px 8px' }}>
                      <Link to={`/jobs/${job.id}`} style={{ color: 'var(--primary)', textDecoration: 'none', fontWeight: 500 }}>
                        Подробнее
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}

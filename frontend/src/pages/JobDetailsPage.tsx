import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { jobsApi, Job } from '../shared/api/jobs';
import { apiClient } from '../shared/api/client';

export function JobDetailsPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!jobId) return;

    let isMounted = true;
    let timeoutId: ReturnType<typeof setTimeout>;

    const fetchJob = async () => {
      try {
        const data = await jobsApi.getJobDetails(jobId);
        if (isMounted) {
          setJob(data);
          // Если задача все еще в работе, запрашиваем статус снова через 2 секунды
          if (data.status === 'processing' || data.status === 'pending') {
            timeoutId = setTimeout(fetchJob, 2000);
          }
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.response?.data?.detail || 'Ошибка загрузки данных задачи');
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    fetchJob();

    // Очистка при уходе со страницы, чтобы не было утечек памяти
    return () => {
      isMounted = false;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [jobId]);

  const handleDownload = async () => {
    if (!jobId) return;
    try {
      const response = await apiClient.get(`/jobs/${jobId}/download`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `RESULT_${job?.original_filename || 'arshin.xlsx'}`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
    } catch (err) {
      alert('Ошибка при скачивании файла. Возможно, он еще не готов.');
    }
  };

  if (isLoading) return <div className="page"><p className="muted">Загрузка данных...</p></div>;
  if (error) return <div className="page"><p style={{color: '#ef4444'}}>{error}</p><br/><Link to="/jobs">Назад</Link></div>;
  if (!job) return <div className="page"><p className="muted">Задача не найдена</p></div>;

  return (
    <section className="page">
      <div className="page-header">
        <span className="eyebrow">Job Details</span>
        <h1 className="page-title">{job.original_filename}</h1>
        <p className="muted">ID: {job.id}</p>
      </div>

      <div className="card">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '24px', marginBottom: '32px' }}>
          <div>
            <p className="muted" style={{ marginBottom: '8px' }}>Статус обработки</p>
            <span style={{ 
              padding: '6px 12px', 
              borderRadius: '6px', 
              fontWeight: 500,
              backgroundColor: job.status === 'completed' ? '#dcfce7' : job.status === 'failed' ? '#fee2e2' : '#fef9c3',
              color: job.status === 'completed' ? '#166534' : job.status === 'failed' ? '#991b1b' : '#854d0e'
            }}>
              {job.status.toUpperCase()}
            </span>
          </div>
          <div>
            <p className="muted" style={{ marginBottom: '8px' }}>Обработано приборов</p>
            <strong style={{ fontSize: '18px' }}>{job.processed_items} / {job.total_items || '?'}</strong>
          </div>
          <div>
            <p className="muted" style={{ marginBottom: '8px' }}>Найдено расхождений</p>
            <strong style={{ fontSize: '18px', color: job.issue_count > 0 ? '#ef4444' : 'inherit' }}>
              {job.issue_count}
            </strong>
          </div>
        </div>

        {job.status === 'completed' && (
          <button className="primary-button" onClick={handleDownload} style={{ width: 'auto', padding: '12px 24px' }}>
            Скачать размеченный Excel
          </button>
        )}
        {(job.status === 'processing' || job.status === 'pending') && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '16px', backgroundColor: '#f3f4f6', borderRadius: '8px' }}>
            <div className="spinner" style={{ width: '20px', height: '20px', border: '3px solid #e5e7eb', borderTopColor: '#2563eb', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            <p style={{ margin: 0, fontWeight: 500, color: '#374151' }}>Файл обрабатывается. Страница обновится автоматически...</p>
          </div>
        )}
        {job.status === 'failed' && (
          <div style={{ padding: '16px', backgroundColor: '#fee2e2', borderRadius: '8px', color: '#991b1b' }}>
            <p style={{ margin: 0, fontWeight: 500 }}>Ошибка обработки:</p>
            <p style={{ margin: '4px 0 0 0', fontSize: '14px' }}>{job.error_message || 'Внутренняя ошибка парсера'}</p>
          </div>
        )}
        
        <div style={{ marginTop: '32px' }}>
          <Link to="/jobs" style={{ color: 'var(--primary)', textDecoration: 'none', fontWeight: 500 }}>
            &larr; Вернуться к списку
          </Link>
        </div>
      </div>
    </section>
  );
}

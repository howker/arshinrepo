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
    const fetchJob = async () => {
      try {
        const data = await jobsApi.getJobDetails(jobId);
        setJob(data);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Ошибка загрузки данных задачи');
      } finally {
        setIsLoading(false);
      }
    };
    fetchJob();
  }, [jobId]);

  const handleDownload = async () => {
    if (!jobId) return;
    try {
      // Запрашиваем файл как Blob (бинарные данные)
      const response = await apiClient.get(`/jobs/${jobId}/download`, {
        responseType: 'blob',
      });
      
      // Создаем скрытую ссылку для скачивания файла браузером
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
              backgroundColor: job.status === 'completed' ? '#dcfce7' : job.status === 'processing' ? '#fef9c3' : '#f3f4f6',
              color: job.status === 'completed' ? '#166534' : job.status === 'processing' ? '#854d0e' : '#1f2937'
            }}>
              {job.status.toUpperCase()}
            </span>
          </div>
          <div>
            <p className="muted" style={{ marginBottom: '8px' }}>Обработано приборов</p>
            <strong style={{ fontSize: '18px' }}>{job.processed_items} / {job.total_items}</strong>
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
        {job.status === 'processing' && (
          <p className="muted">Файл сейчас обрабатывается воркером. Обновите страницу через минуту.</p>
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

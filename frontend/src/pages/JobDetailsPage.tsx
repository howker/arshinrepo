import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { jobsApi, Job } from '../shared/api/jobs';
import { useAuthStore } from '../features/auth/store';
import { apiClient } from '../shared/api/client';

export function JobDetailsPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState('');
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  useEffect(() => {
    if (!jobId || !isAuthenticated) return;

    let timeoutId: ReturnType<typeof setTimeout>;

    const fetchJob = async () => {
      try {
        const data = await jobsApi.getJobDetails(jobId);
        setJob(data);

        // Если задача еще в работе — опрашиваем бэкенд каждые 3 секунды
        if (['uploaded', 'queued', 'processing'].includes(data.status)) {
          timeoutId = setTimeout(fetchJob, 3000);
        }
      } catch (err: any) {
        setError('Не удалось загрузить данные задачи. Возможно, она была удалена.');
      }
    };

    fetchJob();

    return () => {
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [jobId, isAuthenticated]);

  const handleDownload = async () => {
    if (!jobId) return;
    try {
      // Скачиваем файл через API клиент, чтобы передать токен авторизации
      const response = await apiClient.get(`/jobs/${jobId}/download`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `annotated_${job?.original_filename || 'result.xlsx'}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError('Ошибка при скачивании файла. Убедитесь, что результат готов.');
    }
  };

  if (error) {
    return (
      <section className="page">
        <div className="card" style={{ color: '#ef4444', fontWeight: 500 }}>{error}</div>
      </section>
    );
  }

  if (!job) {
    return (
      <section className="page">
        <div className="card muted">Получение статуса задачи...</div>
      </section>
    );
  }

  const isFinished = ['completed', 'failed'].includes(job.status);
  const progressPercent = job.total_items > 0
    ? Math.round((job.processed_items / job.total_items) * 100)
    : 0;

  return (
    <section className="page">
      <div className="page-header">
        <span className="eyebrow">Job details</span>
        <h1 className="page-title">Проверка: {job.original_filename}</h1>
        <p className="muted">ID: {job.id}</p>
      </div>

      <div className="page-grid">
        <article className="card">
          <h2 className="section-title">Статус обработки: {job.status.toUpperCase()}</h2>
          
          <div className="progress-shell">
            <div 
              className="progress-bar" 
              style={{ 
                width: `${progressPercent}%`, 
                backgroundColor: job.status === 'failed' ? '#ef4444' : 'var(--primary)',
                transition: 'width 0.5s ease-in-out'
              }} 
            />
          </div>
          <p className="muted">
            Обработано {job.processed_items} из {job.total_items} приборов ({progressPercent}%)
          </p>
          
          {job.issue_count > 0 && (
            <p style={{ color: '#ef4444', fontWeight: 600, marginTop: '12px' }}>
              ⚠️ Найдено расхождений/ошибок: {job.issue_count}
            </p>
          )}

          {isFinished && job.status === 'completed' && (
            <div style={{ marginTop: '24px' }}>
              <button onClick={handleDownload} className="primary-button">
                Скачать результат (Excel)
              </button>
            </div>
          )}
        </article>

        <article className="card">
          <h2 className="section-title">Навигация</h2>
          <div className="action-row">
            <Link className="link" to="/jobs">← Назад к списку проверок</Link>
            <Link className="link" to="/dashboard">↑ На Dashboard</Link>
          </div>
        </article>
      </div>
    </section>
  );
}

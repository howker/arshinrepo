import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { jobsApi } from '../shared/api/jobs';

export function DashboardPage() {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setError('');
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Пожалуйста, выберите файл');
      return;
    }

    setIsUploading(true);
    setError('');

    try {
      const newJob = await jobsApi.uploadJob(file, 'pril_1_main');
      // После успешной загрузки сразу переводим пользователя на страницу деталей задачи
      navigate(`/jobs/${newJob.id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка при загрузке файла. Проверьте соединение.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <section className="page">
      <div className="page-header">
        <span className="eyebrow">Overview</span>
        <h1 className="page-title">Dashboard</h1>
        <p className="muted">
          Загрузите новый Excel-файл для старта автоматической проверки в ФГИС «Аршин».
        </p>
      </div>

      <div className="card form-card">
        <h2 className="section-title">Новая проверка</h2>
        <form className="form-grid" onSubmit={handleUpload}>
          {error && <div style={{ color: '#ef4444', fontSize: '14px' }}>{error}</div>}
          
          <label className="field">
            <span className="field-label">Excel файл (Приложение №1)</span>
            <input 
              type="file" 
              accept=".xlsx, .xls" 
              onChange={handleFileChange}
              disabled={isUploading}
            />
          </label>

          <button className="primary-button" type="submit" disabled={!file || isUploading}>
            {isUploading ? 'Отправка...' : 'Загрузить и начать парсинг'}
          </button>
        </form>
      </div>
    </section>
  );
}

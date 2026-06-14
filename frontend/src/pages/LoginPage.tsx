import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../shared/api/client';
import { useAuthStore } from '../features/auth/store';

export function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  const navigate = useNavigate();
  const setToken = useAuthStore((state) => state.setToken);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      // Отправляем классический JSON, так как бэкенд ждет Pydantic-модель
      const response = await apiClient.post('/auth/login', {
        email: email,
        password: password
      });

      setToken(response.data.access_token);
      navigate('/dashboard');
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'string') {
        setError(detail);
      } else if (Array.isArray(detail)) {
        setError(`Ошибка: ${detail[0].loc?.join(' -> ')} (${detail[0].msg})`);
      } else {
        setError('Сервер отклонил запрос. Проверьте консоль.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section className="page">
      <div className="page-header">
        <span className="eyebrow">Auth</span>
        <h1 className="page-title">Вход в систему</h1>
        <p className="muted">Введите email и пароль для доступа.</p>
      </div>

      <div className="card form-card">
        <form className="form-grid" onSubmit={handleLogin}>
          {error && (
            <div style={{ color: '#ef4444', fontSize: '14px', padding: '12px', backgroundColor: '#fee2e2', borderRadius: '6px', border: '1px solid #fca5a5' }}>
              {error}
            </div>
          )}
          
          <label className="field">
            <span className="field-label">Email</span>
            <input 
              type="email" 
              placeholder="admin@arshin.local" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isLoading}
              required 
            />
          </label>

          <label className="field">
            <span className="field-label">Пароль</span>
            <input 
              type="password" 
              placeholder="••••••••" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
              required 
            />
          </label>

          <button className="primary-button" type="submit" disabled={isLoading}>
            {isLoading ? 'Вход...' : 'Войти'}
          </button>
        </form>
      </div>
    </section>
  );
}

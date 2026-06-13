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
      // FastAPI OAuth2PasswordRequestForm ожидает x-www-form-urlencoded
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const response = await apiClient.post('/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      setToken(response.data.access_token);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка авторизации. Проверьте данные.');
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
          {error && <div style={{ color: '#ef4444', fontSize: '14px' }}>{error}</div>}
          
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

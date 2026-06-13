import axios from 'axios';

// Используем относительный путь для работы через Nginx в будущем
export const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Интерцептор для добавления токена (пока берем напрямую из localStorage, 
// позже переделаем через Zustand для реактивности)
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

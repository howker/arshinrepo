import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
// Если файл стилей называется иначе (например, App.css), Vite ругнется,
// но стандартно это index.css
import './index.css' 

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)

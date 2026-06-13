import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <section className="page">
      <div className="card">
        <span className="eyebrow">404</span>
        <h1 className="page-title">Страница не найдена</h1>
        <p className="muted">
          В текущем шаге собран только базовый каркас будущего SaaS-интерфейса.
        </p>
        <Link className="link" to="/login">
          Перейти к логину
        </Link>
      </div>
    </section>
  );
}

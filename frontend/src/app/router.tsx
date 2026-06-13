import { Navigate, createBrowserRouter } from 'react-router-dom';
import { AppLayout } from './layouts/AppLayout';
import { DashboardPage } from '../pages/DashboardPage';
import { JobDetailsPage } from '../pages/JobDetailsPage';
import { JobsPage } from '../pages/JobsPage';
import { LoginPage } from '../pages/LoginPage';
import { NotFoundPage } from '../pages/NotFoundPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Navigate to="/login" replace />
  },
  {
    path: '/',
    element: <AppLayout />,
    errorElement: <NotFoundPage />,
    children: [
      {
        path: 'login',
        element: <LoginPage />
      },
      {
        path: 'dashboard',
        element: <DashboardPage />
      },
      {
        path: 'jobs',
        element: <JobsPage />
      },
      {
        path: 'jobs/:jobId',
        element: <JobDetailsPage />
      }
    ]
  },
  {
    path: '*',
    element: <NotFoundPage />
  }
]);

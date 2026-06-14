import { apiClient } from './client';

export interface Job {
  id: string;
  status: string;
  original_filename: string;
  template_code?: string;
  total_items: number;
  processed_items: number;
  issue_count: number;
  created_at?: string;
  started_at?: string;
  finished_at?: string;
  error_message?: string;
}

export const jobsApi = {
  getJobs: async (): Promise<Job[]> => {
    const response = await apiClient.get('/jobs');
    return response.data;
  },
  getJobDetails: async (id: string): Promise<Job> => {
    const response = await apiClient.get(`/jobs/${id}`);
    return response.data;
  },
  uploadJob: async (file: File, templateCode: string = 'pril_1_main'): Promise<Job> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('template_code', templateCode);

    const response = await apiClient.post('/jobs/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }
};

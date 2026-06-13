import { apiClient } from './client';

export interface Job {
  id: string;
  original_filename: string;
  status: string;
  total_items: number;
  processed_items: number;
  issue_count: number;
  created_at: string;
}

export const jobsApi = {
  getJobs: async (): Promise<Job[]> => {
    const response = await apiClient.get('/jobs');
    return response.data;
  },
  getJobDetails: async (id: string): Promise<Job> => {
    const response = await apiClient.get(`/jobs/${id}`);
    return response.data;
  }
};

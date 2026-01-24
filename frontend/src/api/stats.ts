import { useQuery } from '@tanstack/react-query';
import { apiClient } from './client';

export interface DashboardStats {
  total_workouts: number;
  workouts_this_month: number;
  week_streak: number;
  heaviest_lift: {
    weight: number;
    movement: string;
    e1rm: number;
  } | null;
  longest_workout: {
    minutes: number;
    date: string | null;
  } | null;
  total_volume_this_month: number;
  average_adherence: number | null;
}

async function fetchDashboardStats(): Promise<DashboardStats> {
  const { data } = await apiClient.get('/logs/stats');
  return data;
}

export function useDashboardStats() {
  return useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: fetchDashboardStats,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

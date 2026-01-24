import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type {
  UserProfile,
  UserProfileUpdate,
  Movement,
  MovementCreate,
} from '@/types';
import type { MovementPattern } from '@/types';

type MovementsQueryOptions = {
  pattern?: MovementPattern | 'all';
  equipment?: string | 'all';
  search?: string;
  limit?: number;
  offset?: number;
};

interface MovementListResponse {
  movements: Movement[];
  total: number;
  limit?: number | null;
  offset?: number | null;
  filters_applied?: Record<string, unknown> | null;
}

interface MovementFiltersResponse {
  patterns: string[];
  regions: string[];
  equipment: string[];
  primary_disciplines: string[];
  types?: string[] | null;
}

export const settingsKeys = {
  all: ['settings'] as const,
  profile: () => [...settingsKeys.all, 'profile'] as const,
  movements: (params: MovementsQueryOptions) => [
    ...settingsKeys.all,
    'movements',
    params,
  ] as const,
  movementFilters: () => [...settingsKeys.all, 'movement-filters'] as const,
};

async function fetchUserProfile(): Promise<UserProfile> {
  const { data } = await apiClient.get('/settings/user/profile');
  return data;
}

async function updateUserProfile(data: UserProfileUpdate): Promise<UserProfile> {
  const { data: response } = await apiClient.patch(
    '/settings/user/profile',
    data,
  );
  return response;
}

async function fetchMovements(
  options: MovementsQueryOptions = {},
): Promise<MovementListResponse> {
  const { pattern, equipment, search, limit, offset } = options;
  const params: Record<string, unknown> = {};

  if (pattern && pattern !== 'all') {
    params.pattern = pattern;
  }
  if (equipment && equipment !== 'all') {
    params.equipment = equipment;
  }
  if (search) {
    params.search = search;
  }
  if (typeof limit === 'number') {
    params.limit = limit;
  }
  if (typeof offset === 'number') {
    params.offset = offset;
  }

  const { data } = await apiClient.get('/settings/movements', { params });
  return data;
}

async function fetchMovementFilters(): Promise<MovementFiltersResponse> {
  const { data } = await apiClient.get('/settings/movements/filters');
  return data;
}

async function createMovement(payload: MovementCreate): Promise<Movement> {
  const { data } = await apiClient.post('/settings/movements', payload);
  return data;
}

export function useUserProfile() {
  return useQuery({
    queryKey: settingsKeys.profile(),
    queryFn: fetchUserProfile,
  });
}

export function useUpdateUserProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updateUserProfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsKeys.profile() });
    },
  });
}

export function useMovements(options: MovementsQueryOptions = { limit: 1000 }) {
  const queryOptions = { limit: 1000, ...options };

  return useQuery({
    queryKey: settingsKeys.movements(queryOptions),
    queryFn: () => fetchMovements(queryOptions),
  });
}

export function useMovementFilters() {
  return useQuery({
    queryKey: settingsKeys.movementFilters(),
    queryFn: fetchMovementFilters,
  });
}

export function useCreateMovement() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createMovement,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsKeys.all });
      queryClient.invalidateQueries({ queryKey: settingsKeys.movementFilters() });
    },
  });
}

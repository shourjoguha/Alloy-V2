import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';

export interface Favorite {
  id: number;
  movement_id: number | null;
  program_id: number | null;
  created_at: string;
}

export interface MovementFavorite {
  id: number;
  movement_id: number;
  movement_name: string;
  pattern: string;
  primary_muscle: string;
  primary_region: string;
  created_at: string;
}

export interface ProgramFavorite {
  id: number;
  program_id: number;
  program_name: string | null;
  split_template: string;
  duration_weeks: number;
  is_active: boolean;
  created_at: string;
}

export interface FavoritesResponse {
  movements: MovementFavorite[];
  programs: ProgramFavorite[];
}

export interface FavoriteCreate {
  movement_id?: number | null;
  program_id?: number | null;
}

// Query keys
export const favoriteKeys = {
  all: ['favorites'] as const,
  lists: () => [...favoriteKeys.all, 'list'] as const,
  details: () => [...favoriteKeys.all, 'detail'] as const,
  detail: (id: number) => [...favoriteKeys.details(), id] as const,
};

// API functions
async function fetchFavorites(): Promise<FavoritesResponse> {
  const { data } = await apiClient.get('/favorites');
  return data;
}

async function createFavorite(favorite: FavoriteCreate): Promise<Favorite> {
  const { data } = await apiClient.post('/favorites', favorite);
  return data;
}

async function deleteFavorite(id: number): Promise<void> {
  await apiClient.delete(`/favorites/${id}`);
}

// React Query hooks
export function useFavorites() {
  return useQuery({
    queryKey: favoriteKeys.lists(),
    queryFn: fetchFavorites,
  });
}

export function useCreateFavorite() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: createFavorite,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: favoriteKeys.all });
    },
  });
}

export function useDeleteFavorite() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: deleteFavorite,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: favoriteKeys.all });
    },
  });
}

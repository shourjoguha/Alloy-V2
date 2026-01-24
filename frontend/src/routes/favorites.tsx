import { createFileRoute } from '@tanstack/react-router';
import { FavoritesTab } from '@/components/settings/FavoritesTab';

export const Route = createFileRoute('/favorites')({
  component: FavoritesPage,
});

function FavoritesPage() {
  return (
    <div className="container-app py-6">
      <FavoritesTab />
    </div>
  );
}

import { createFileRoute } from '@tanstack/react-router';
import { Users } from 'lucide-react';

export const Route = createFileRoute('/teams')({
  component: TeamsPage,
});

function TeamsPage() {
  return (
    <div className="container-app py-6 flex flex-col items-center justify-center min-h-[60vh] text-center">
      <div className="rounded-full bg-background-elevated p-6 mb-4">
        <Users className="h-12 w-12 text-foreground-muted" />
      </div>
      <h1 className="text-xl font-semibold mb-2">Teams</h1>
      <p className="text-foreground-muted">
        Team workouts and social features coming soon!
      </p>
    </div>
  );
}

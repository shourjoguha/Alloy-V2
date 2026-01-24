import { createFileRoute } from '@tanstack/react-router';
import { Users } from 'lucide-react';

export const Route = createFileRoute('/friends')({
  component: FriendsPage,
});

function FriendsPage() {
  return (
    <div className="container-app py-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Friends</h1>
        <p className="mt-2 text-sm text-foreground-muted">
          Connect with friends and share your fitness journey
        </p>
      </div>

      <div className="flex flex-col items-center justify-center rounded-lg border border-border bg-background-elevated p-12">
        <Users className="h-16 w-16 text-foreground-muted mb-4" />
        <h2 className="text-lg font-semibold text-foreground mb-2">Coming Soon</h2>
        <p className="text-center text-sm text-foreground-muted max-w-md">
          The Friends feature is under development. Soon you'll be able to connect with
          friends, share workouts, and motivate each other.
        </p>
      </div>
    </div>
  );
}

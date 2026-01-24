import { useState } from 'react';
import { createFileRoute } from '@tanstack/react-router';
import { SorenessTracker } from '@/components/visuals';
import { Button } from '@/components/ui/button';

export const Route = createFileRoute('/log/soreness')({
  component: LogSorenessPage,
});

export function LogSorenessPage() {
  const [logDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [showTracker, setShowTracker] = useState(false);

  return (
    <div className="container-app py-6 animate-fade-in">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-foreground">Log Muscle Soreness</h1>
        <p className="text-sm text-foreground-muted mt-1">
          Track your muscle recovery independent of workouts
        </p>
      </div>

      {!showTracker ? (
        <div className="space-y-4">
          <div className="bg-background-elevated rounded-xl p-6 border border-border">
            <h2 className="text-lg font-semibold mb-2">Why Log Soreness?</h2>
            <ul className="text-sm text-foreground-muted space-y-2">
              <li>• Track recovery progress between workouts</li>
              <li>• Help Jerome optimize future training intensity</li>
              <li>• Identify patterns in your recovery</li>
              <li>• Adjust training based on how you feel</li>
            </ul>
          </div>

          <Button
            variant="cta"
            size="lg"
            className="w-full"
            onClick={() => setShowTracker(true)}
          >
            Start Logging
          </Button>
        </div>
      ) : (
        <SorenessTracker
          logDate={logDate}
          onSuccess={() => setShowTracker(false)}
          onCancel={() => setShowTracker(false)}
        />
      )}
    </div>
  );
}

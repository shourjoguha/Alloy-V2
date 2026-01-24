import { createFileRoute, Link } from '@tanstack/react-router';
import { ArrowLeft, Construction } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export const Route = createFileRoute('/program/manual')({
  component: ManualProgramPage,
});

function ManualProgramPage() {
  return (
    <div className="container-app py-6 space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link to="/program/new" className="text-foreground-muted hover:text-foreground">
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <h1 className="text-xl font-bold">Create Your Own Program</h1>
      </div>

      {/* Coming soon */}
      <Card className="p-8 text-center space-y-4">
        <div className="h-16 w-16 rounded-full bg-accent/20 flex items-center justify-center mx-auto">
          <Construction className="h-8 w-8 text-accent" />
        </div>
        <div className="space-y-2">
          <h2 className="text-lg font-semibold">Coming Soon</h2>
          <p className="text-foreground-muted text-sm max-w-md mx-auto">
            Manual program builder is under construction. For now, let Jerome help you 
            create a personalized program based on your goals.
          </p>
        </div>
        <Link to="/program/wizard">
          <Button variant="primary" className="mt-4">
            Build with Jerome Instead
          </Button>
        </Link>
      </Card>

      {/* Back link */}
      <Link 
        to="/program/new" 
        className="flex items-center justify-center gap-2 text-foreground-muted hover:text-foreground transition-colors py-4"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Options
      </Link>
    </div>
  );
}

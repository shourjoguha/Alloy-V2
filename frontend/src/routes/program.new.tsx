import { createFileRoute, Link } from '@tanstack/react-router';
import { Bot, Wrench, ArrowLeft } from 'lucide-react';
import { Card } from '@/components/ui/card';

export const Route = createFileRoute('/program/new')({
  component: NewProgramPage,
});

function NewProgramPage() {
  return (
    <div className="container-app py-6 space-y-8 animate-fade-in">
      {/* Header */}
      <div className="text-center space-y-2">
        <h1 className="text-2xl font-bold">Create New Program</h1>
        <p className="text-foreground-muted">
          Choose how you'd like to build your training program
        </p>
      </div>

      {/* Options */}
      <div className="space-y-4">
        {/* Build with Jerome */}
        <Link to="/program/wizard">
          <Card 
            variant="interactive" 
            className="p-6 hover:border-accent transition-colors"
          >
            <div className="flex gap-4">
              <div className="flex-shrink-0">
                <div className="h-12 w-12 rounded-xl bg-accent/20 flex items-center justify-center">
                  <Bot className="h-6 w-6 text-accent" />
                </div>
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-lg">Build with Jerome</h3>
                <p className="text-sm text-foreground-muted mt-1">
                  Our AI Coach will guide you through a personalized questionnaire and build a complete training program tailored to your goals.
                </p>
                <div className="flex flex-wrap gap-2 mt-3">
                  <span className="text-xs px-2 py-1 rounded-full bg-accent/20 text-accent">
                    Personalized
                  </span>
                  <span className="text-xs px-2 py-1 rounded-full bg-accent/20 text-accent">
                    12-week program
                  </span>
                  <span className="text-xs px-2 py-1 rounded-full bg-accent/20 text-accent">
                    Auto-progression
                  </span>
                </div>
              </div>
            </div>
          </Card>
        </Link>

        {/* Create Your Own */}
        <Link to="/program/manual">
          <Card 
            variant="interactive" 
            className="p-6 hover:border-foreground-subtle transition-colors"
          >
            <div className="flex gap-4">
              <div className="flex-shrink-0">
                <div className="h-12 w-12 rounded-xl bg-background-elevated flex items-center justify-center">
                  <Wrench className="h-6 w-6 text-foreground-muted" />
                </div>
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-lg">Create Your Own</h3>
                <p className="text-sm text-foreground-muted mt-1">
                  Design your program from scratch. Build custom sessions, choose exercises, and set your own schedule.
                </p>
                <div className="flex flex-wrap gap-2 mt-3">
                  <span className="text-xs px-2 py-1 rounded-full bg-background-elevated text-foreground-muted">
                    Full control
                  </span>
                  <span className="text-xs px-2 py-1 rounded-full bg-background-elevated text-foreground-muted">
                    Custom duration
                  </span>
                  <span className="text-xs px-2 py-1 rounded-full bg-background-elevated text-foreground-muted">
                    Flexible
                  </span>
                </div>
              </div>
            </div>
          </Card>
        </Link>
      </div>

      {/* Back to dashboard */}
      <Link 
        to="/" 
        className="flex items-center justify-center gap-2 text-foreground-muted hover:text-foreground transition-colors py-4"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Dashboard
      </Link>
    </div>
  );
}

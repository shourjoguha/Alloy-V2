import { useState } from 'react';
import { Link } from '@tanstack/react-router';
import { Play, MessageSquare, RefreshCw, Plus, ChevronLeft, ChevronRight, Eye, History, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Spinner } from '@/components/ui';
import { usePrograms, useProgram } from '@/api/programs';
import { useDashboardStats } from '@/api/stats';
import { SessionCard } from '@/components/program/SessionCard';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/stores/auth-store';

export function Dashboard() {
  const { user } = useAuthStore();
  const userName = user?.name || "Gain Smith";
  
  // Fetch all programs (first one will be active or most recent)
  const { data: programs, isLoading: programsLoading } = usePrograms(false);
  const activeProgram = programs?.[0];

  // Fetch detailed program data for sessions
  const { data: programDetails } = useProgram(activeProgram?.id ?? -1);
  const sessions = programDetails?.upcoming_sessions || [];
  
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  const [isPickerOpen, setIsPickerOpen] = useState(false);
  const selectedSession = sessions.find(s => s.id === selectedSessionId);
  
  // Fetch dashboard stats
  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  
  // Determine current week (from active program's microcycle)
  const currentWeek = 1; // Will be dynamic when we have active microcycle data
  const weekPhase = activeProgram ? "Active" : "No Program";

  // Format helpers
  const formatWeight = (weight: number | null | undefined) => {
    if (weight === null || weight === undefined) return "—";
    return `${weight}kg`;
  };
  
  const formatDuration = (minutes: number | null | undefined) => {
    if (minutes === null || minutes === undefined) return "—";
    return `${minutes}m`;
  };
  
  const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return "";
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'numeric', day: 'numeric', year: 'numeric' });
  };
  
  const formatPercentage = (value: number | null | undefined) => {
    if (value === null || value === undefined) return "—";
    return `${Math.round(value)}%`;
  };

  return (
    <div className="container-app py-6 space-y-6 animate-fade-in">
      {/* Header title */}
      <h1 className="text-xl font-semibold">{userName}'s Dashboard</h1>

      {/* Week navigation */}
      <div className="flex items-center justify-between">
        <button className="p-2 text-foreground-muted hover:text-foreground transition-colors">
          <ChevronLeft className="h-5 w-5" />
        </button>
        <div className="text-center">
          <span className="font-semibold">Week {currentWeek}</span>
          <span className="ml-2 text-foreground-muted">{weekPhase}</span>
        </div>
        <button className="p-2 text-foreground-muted hover:text-foreground transition-colors">
          <ChevronRight className="h-5 w-5" />
        </button>
      </div>

      {/* Primary CTA - Select/Start Workout */}
      {activeProgram ? (
        <div className="space-y-4">
          {/* Main Action Button / Header */}
          <Button
            size="lg"
            className={cn(
              "w-full justify-between transition-all duration-300 border-0 py-8 h-auto min-h-[6rem] relative",
              selectedSession 
                ? "bg-cta hover:bg-cta-hover text-white shadow-[0_6px_0_0_rgb(0,0,0,0.2)] active:shadow-none active:translate-y-[6px]" 
                : "bg-cta hover:bg-cta-hover text-white shadow-[0_6px_0_0_rgb(0,0,0,0.2)] active:shadow-none active:translate-y-[6px]"
            )}
            onClick={() => {
              if (!selectedSession) {
                setIsPickerOpen(!isPickerOpen);
              }
            }}
            asChild={!!selectedSession}
          >
            {selectedSession ? (
              <Link to="/program/$programId" params={{ programId: String(activeProgram.id) }}>
                <Play className="h-10 w-10 mr-3 fill-current" />
                <span className="text-3xl font-bold">Start Day {selectedSession.day_number}</span>
                <ChevronRight className="h-10 w-10 ml-auto" />
              </Link>
            ) : (
              <div className="w-full flex items-center justify-center cursor-pointer">
                <Play className="h-10 w-10 mr-4 fill-current" />
                <span className="text-4xl font-bold">{isPickerOpen ? "Select Workout" : "Let's Go!"}</span>
                {isPickerOpen ? (
                  <ChevronUp className="h-10 w-10 ml-4" />
                ) : (
                  <ChevronDown className="h-10 w-10 ml-4" />
                )}
              </div>
            )}
          </Button>

          {/* Collapsible Section */}
          <div className={cn(
            "grid transition-all duration-300 ease-in-out",
            isPickerOpen ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
          )}>
            <div className="overflow-hidden space-y-4">
              {/* Horizontal Session Picker */}
              <div className="overflow-x-auto -mx-4 px-4 sm:mx-0 sm:px-0 pb-2 scrollbar-hide pt-1">
                <div className="flex gap-3 min-w-max">
                  {sessions.map((session) => {
                    const isSelected = selectedSessionId === session.id;
                    
                    return (
                      <button
                        key={session.id}
                        onClick={() => setSelectedSessionId(isSelected ? null : session.id)}
                        className={cn(
                          "flex flex-col items-center justify-center min-w-[100px] h-20 p-2 rounded-xl border-2 transition-all duration-200",
                          isSelected 
                            ? "bg-cta border-cta text-white shadow-md scale-105" 
                            : "bg-background-elevated border-transparent hover:border-border text-foreground shadow-sm hover:shadow-md"
                        )}
                      >
                        <span className={cn(
                          "text-xs font-medium uppercase tracking-wider",
                          isSelected ? "opacity-90" : "opacity-70"
                        )}>Day</span>
                        <span className="text-lg font-semibold">{session.day_number}</span>
                        {session.session_type && (
                           <span className={cn(
                             "text-[10px] mt-0.5 capitalize truncate w-full text-center",
                             isSelected ? "opacity-80" : "opacity-60"
                           )}>
                             {session.session_type.replace('_', ' ')}
                           </span>
                        )}
                      </button>
                    );
                  })}
                  
                  {sessions.length === 0 && !programDetails && (
                     <div className="flex gap-3">
                       {[1, 2, 3].map(i => (
                         <div key={i} className="w-[100px] h-20 rounded-xl bg-background-secondary animate-pulse" />
                       ))}
                     </div>
                  )}
                </div>
              </div>

              {/* Log custom workout - moved inside collapsible */}
              <Button variant="outline" className="w-full" asChild>
                <Link to="/log/custom">
                  <Plus className="h-4 w-4 mr-2" />
                  Log Custom Workout
                </Link>
              </Button>

              {/* Expanded Session Details */}
              {selectedSession && (
                <div className="animate-slide-down space-y-4">
                  <SessionCard key={selectedSession.id} session={selectedSession} defaultExpanded={true} />
                  
                  {/* Adapt Session Button */}
                  <Button variant="secondary" className="w-full" asChild>
                    <Link to="/">
                      <MessageSquare className="h-4 w-4 mr-2" />
                      Adapt Session
                    </Link>
                  </Button>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        <Button variant="cta" size="lg" className="w-full" asChild>
          <Link to="/program/new">
            <Plus className="h-5 w-5 mr-2" />
            Create Your First Program
            <ChevronRight className="h-5 w-5 ml-auto" />
          </Link>
        </Button>
      )}

      {/* Secondary actions */}
      <div className="flex gap-3">
        <Button variant="secondary" className="flex-1" asChild>
          <Link to="/program/new">
            <RefreshCw className="h-4 w-4 mr-2" />
            New Program
          </Link>
        </Button>
        {activeProgram && (
          <Button variant="ghost" size="icon" aria-label="View program" asChild>
            <Link to="/program/$programId" params={{ programId: String(activeProgram.id) }}>
              <Eye className="h-4 w-4" />
            </Link>
          </Button>
        )}
        <Button variant="ghost" size="icon" aria-label="History">
          <History className="h-4 w-4" />
        </Button>
      </div>

      {/* Stats cards - top row */}
      {statsLoading ? (
        <div className="flex justify-center py-4">
          <Spinner size="sm" />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-3">
            <StatCard 
              value={stats?.heaviest_lift ? formatWeight(stats.heaviest_lift.weight) : "—"}
              label="Heaviest Lift" 
              sublabel={stats?.heaviest_lift?.movement || ""}
            />
            <StatCard 
              value={stats?.longest_workout ? formatDuration(stats.longest_workout.minutes) : "—"}
              label="Longest Workout" 
              sublabel={stats?.longest_workout ? formatDate(stats.longest_workout.date) : ""}
            />
            <StatCard 
              value={formatWeight(stats?.total_volume_this_month)}
              label="Volume This Month" 
            />
          </div>

          {/* Stats cards - bottom row */}
          <div className="grid grid-cols-3 gap-3">
            <StatCard 
              value={String(stats?.total_workouts ?? 0)} 
              label="Workouts Done" 
            />
            <StatCard 
              value={String(stats?.week_streak ?? 0)} 
              label="Week Streak" 
            />
            <StatCard 
              value={formatPercentage(stats?.average_adherence)} 
              label="Adherence" 
            />
          </div>
        </>
      )}

      {/* Program status card */}
      {programsLoading ? (
        <Card variant="grouped" className="p-6 text-center">
          <Spinner size="sm" />
        </Card>
      ) : activeProgram ? (
        <Card variant="grouped" className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-foreground-muted">Active Program</div>
              <div className="font-medium capitalize">
                {activeProgram.split_template?.replace('_', ' ') || 'Custom Program'}
              </div>
              <div className="text-xs text-foreground-muted">
                {activeProgram.duration_weeks} weeks
              </div>
            </div>
            <Link
              to="/program/$programId"
              params={{ programId: String(activeProgram.id) }}
              className="text-primary hover:underline text-sm"
            >
              View Details →
            </Link>
          </div>
        </Card>
      ) : (
        <Card variant="grouped" className="p-6 text-center">
          <div className="text-foreground-muted">No active program</div>
          <Link to="/program/new" className="text-primary hover:underline text-sm mt-2 inline-block">
            Create one now
          </Link>
        </Card>
      )}
    </div>
  );
}

interface StatCardProps {
  value: string;
  label: string;
  sublabel?: string;
}

function StatCard({ value, label, sublabel }: StatCardProps) {
  return (
    <Card variant="grouped" className="p-4 text-center">
      <div className="text-2xl font-bold text-primary">{value}</div>
      <div className="text-xs text-foreground-muted mt-1">{label}</div>
      {sublabel && (
        <div className="text-xs text-foreground-subtle mt-0.5">{sublabel}</div>
      )}
    </Card>
  );
}

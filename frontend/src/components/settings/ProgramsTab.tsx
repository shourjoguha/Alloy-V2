import { useState } from 'react';
import { Link } from '@tanstack/react-router';
import { ChevronDown, ChevronRight, Trash2, Play } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui';
import { usePrograms, useDeleteProgram, useUpdateProgram, useActivateProgram } from '@/api/programs';
import { cn } from '@/lib/utils';
import type { Program } from '@/types';
import { SessionThumbnail } from '@/components/program/SessionThumbnail';

export function ProgramsTab() {
  const { data: programs, isLoading, error } = usePrograms(false);
  const deleteMutation = useDeleteProgram();
  const updateMutation = useUpdateProgram();
  const activateMutation = useActivateProgram();
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());

  const toggleExpanded = (id: number) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleDelete = async (program: Program) => {
    if (deleteMutation.isPending) return;
    await deleteMutation.mutateAsync(program.id);
  };

  const handleNameBlur = async (program: Program, value: string) => {
    const trimmed = value.trim();
    if (trimmed === (program.name || '').trim()) return;
    await updateMutation.mutateAsync({ id: program.id, data: { name: trimmed || null } });
  };

  const handleLoad = async (program: Program) => {
    if (activateMutation.isPending || program.is_active) return;
    await activateMutation.mutateAsync(program.id);
  };

  const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'numeric', day: 'numeric', year: '2-digit' });
  };

  const formatSplit = (split: string) => split.replace('_', ' ');

  if (isLoading) {
    return (
      <div className="flex justify-center py-6">
        <Spinner size="sm" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded bg-error/10 p-3 text-sm text-error">
        Failed to load programs. Please try refreshing the page or check your connection.
      </div>
    );
  }

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Programs History</h2>
        <Button variant="secondary" asChild>
          <Link to="/program/new">New Program</Link>
        </Button>
      </div>

      {!programs || programs.length === 0 ? (
        <Card variant="grouped" className="p-6 text-center">
          <div className="text-foreground-muted mb-2">No programs yet</div>
          <Button variant="outline" asChild>
            <Link to="/program/new">Create your first program</Link>
          </Button>
        </Card>
      ) : (
        <div className="space-y-3">
          {programs.map((program, index) => {
            const expanded = expandedIds.has(program.id);
            const weeks = program.duration_weeks;
            const daysPerWeek = program.days_per_week || 7;
            const isActive = program.is_active;

            return (
              <Card 
                key={program.id} 
                variant="grouped" 
                className={cn(
                  "p-4 transition-all duration-300 ease-in-out",
                  "hover:shadow-md",
                  isActive && "ring-2 ring-primary ring-offset-2"
                )}
                style={{ 
                  transform: `translateY(0)`,
                  transitionDelay: `${index * 30}ms`
                }}
              >
                <div className="flex items-start justify-between gap-3">
                  <button
                    type="button"
                    className="flex flex-1 items-center gap-3 text-left"
                    onClick={() => toggleExpanded(program.id)}
                  >
                    {expanded ? (
                      <ChevronDown className="h-4 w-4 text-foreground-muted" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-foreground-muted" />
                    )}
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          defaultValue={program.name || ''}
                          placeholder="Program name"
                          onBlur={(e) => handleNameBlur(program, e.target.value)}
                          className="w-full bg-transparent border-b border-border/60 focus:border-primary text-sm font-medium outline-none"
                        />
                        {isActive && (
                          <span className="text-[10px] uppercase font-semibold text-primary bg-primary/10 px-1.5 py-0.5 rounded">
                            Active
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-foreground-muted flex items-center gap-2">
                        <span className="capitalize">{formatSplit(program.split_template)}</span>
                        <span>·</span>
                        <span>{program.duration_weeks} weeks</span>
                        <span>·</span>
                        <span>{program.days_per_week} days/week</span>
                        {program.created_at && (
                          <>
                            <span>·</span>
                            <span>Created {formatDate(program.created_at)}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </button>

                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleLoad(program)}
                      disabled={activateMutation.isPending || program.is_active}
                      className={cn(
                        "transition-all duration-300 ease-in-out",
                        program.is_active ? "bg-primary text-primary-foreground hover:bg-primary/90" : ""
                      )}
                    >
                      <Play className="h-3 w-3 mr-1" />
                      Load
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      asChild
                    >
                      <Link to="/program/$programId" params={{ programId: String(program.id) }}>
                        View
                      </Link>
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDelete(program)}
                      disabled={deleteMutation.isPending}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>

                {expanded && (
                  <div className="mt-4 border-t border-border/60 pt-4 space-y-3">
                    {isActive && program.upcoming_sessions && program.upcoming_sessions.length > 0 ? (
                      <>
                        <div className="text-xs text-foreground-muted">Upcoming Sessions</div>
                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                          {program.upcoming_sessions.map((session) => (
                            <SessionThumbnail
                              key={session.id}
                              session={session}
                              onClick={() => {/* TODO: Navigate to session detail */}}
                              size="sm"
                            />
                          ))}
                        </div>
                      </>
                    ) : (
                      <>
                        <div className="text-xs text-foreground-muted">Weeks × Days overview</div>
                        <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
                          {Array.from({ length: weeks }).map((_, weekIndex) => (
                            <div key={weekIndex} className="flex items-center gap-3">
                              <div className="w-14 text-xs text-foreground-muted">Week {weekIndex + 1}</div>
                              <div className="flex-1 overflow-x-auto">
                                <div className="flex gap-2 min-w-max">
                                  {Array.from({ length: daysPerWeek }).map((__, dayIndex) => (
                                    <div
                                      key={dayIndex}
                                      className="w-10 h-10 rounded-md border border-border bg-background-input flex items-center justify-center text-xs text-foreground-muted"
                                    >
                                      D{dayIndex + 1}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </>
                    )}
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

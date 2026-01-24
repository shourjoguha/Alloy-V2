import { useState } from 'react';
import { RotateCcw, Check, X, User } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { HumanBodyMap } from './HumanBodyMap';
import { MuscleList } from './MuscleList';
import { useLogSoreness } from '@/api/logs';
import type { MuscleGroup } from '@/types/anatomy';
import { MUSCLE_DISPLAY_NAMES, ZONE_MAPPING } from '@/types/anatomy';

interface SorenessTrackerProps {
  logDate?: string;
  onSuccess?: () => void;
  onCancel?: () => void;
  className?: string;
}

type SorenessLevel = 0 | 1 | 2 | 3 | 4 | 5;

const SORENESS_LEVELS: Array<{ value: SorenessLevel; label: string; color: string }> = [
  { value: 0, label: 'None', color: 'bg-slate-100 text-slate-800 border-slate-200' },
  { value: 1, label: 'Minimal', color: 'bg-emerald-100 text-emerald-800 border-emerald-200' },
  { value: 2, label: 'Mild', color: 'bg-teal-100 text-teal-800 border-teal-200' },
  { value: 3, label: 'Moderate', color: 'bg-yellow-100 text-yellow-800 border-yellow-200' },
  { value: 4, label: 'Significant', color: 'bg-orange-100 text-orange-800 border-orange-200' },
  { value: 5, label: 'Severe', color: 'bg-red-100 text-red-800 border-red-200' },
];

export function SorenessTracker({ logDate, onSuccess, onCancel, className }: SorenessTrackerProps) {
  const [selectedMuscles, setSelectedMuscles] = useState<MuscleGroup[]>([]);
  const [sorenessLevels, setSorenessLevels] = useState<Record<MuscleGroup, SorenessLevel>>({} as Record<MuscleGroup, SorenessLevel>);
  const [fullBodyDefaultLevel, setFullBodyDefaultLevel] = useState<SorenessLevel>(1);
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const logSorenessMutation = useLogSoreness();

  const toggleMuscle = (muscle: MuscleGroup) => {
    setSelectedMuscles((prev) => {
      if (prev.includes(muscle)) {
        const next = prev.filter((m) => m !== muscle);
        const newLevels = { ...sorenessLevels };
        delete newLevels[muscle];
        setSorenessLevels(newLevels);
        return next;
      } else {
        return [...prev, muscle];
      }
    });
  };

  const toggleFullBody = () => {
    const allMuscles = ZONE_MAPPING['full body'];
    const isAllSelected = allMuscles.every((m: MuscleGroup) => selectedMuscles.includes(m));
    
    if (isAllSelected) {
      setSelectedMuscles([]);
      setSorenessLevels({} as Record<MuscleGroup, SorenessLevel>);
    } else {
      setSelectedMuscles(allMuscles);
      const newLevels = { ...sorenessLevels };
      allMuscles.forEach((m: MuscleGroup) => {
        newLevels[m] = fullBodyDefaultLevel;
      });
      setSorenessLevels(newLevels as Record<MuscleGroup, SorenessLevel>);
    }
  };

  const setMuscleSorenessLevel = (muscle: MuscleGroup, level: SorenessLevel) => {
    setSorenessLevels((prev) => ({
      ...prev,
      [muscle]: level,
    }));
  };

  const clearAll = () => {
    setSelectedMuscles([]);
    setSorenessLevels({} as Record<MuscleGroup, SorenessLevel>);
    setNotes('');
  };

  const handleSubmit = async () => {
    if (selectedMuscles.length === 0) return;

    const musclesWithoutLevel = selectedMuscles.filter((m) => !sorenessLevels[m]);
    if (musclesWithoutLevel.length > 0) {
      alert('Please select a soreness level for all selected muscles');
      return;
    }

    setIsSubmitting(true);
    try {
      const promises = selectedMuscles.map((muscle) =>
        logSorenessMutation.mutateAsync({
          log_date: logDate,
          body_part: muscle,
          soreness_1_5: sorenessLevels[muscle],
          notes: notes || undefined,
        })
      );

      await Promise.all(promises);
      clearAll();
      onSuccess?.();
    } catch (error) {
      console.error('Failed to log soreness:', error);
      alert('Failed to log soreness. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card className={className}>
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-semibold text-foreground">Muscle Soreness Tracker</h2>
            <p className="text-sm text-foreground-muted mt-1">
              Select sore muscles and rate your discomfort level
            </p>
          </div>
          {onCancel && (
            <Button variant="ghost" size="icon" onClick={onCancel}>
              <X className="w-5 h-5" />
            </Button>
          )}
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          <div className="flex flex-col items-center">
            <div className="w-full mb-4 flex items-center gap-2">
              <Button
                type="button"
                variant={selectedMuscles.length === ZONE_MAPPING['full body'].length ? 'cta' : 'outline'}
                onClick={toggleFullBody}
                className="flex-1"
              >
                <User className="w-4 h-4 mr-2" />
                {selectedMuscles.length === ZONE_MAPPING['full body'].length ? 'Deselect All' : 'Select Full Body'}
              </Button>
              <div className="flex items-center gap-2 bg-background-card border border-border rounded-md px-3 py-2">
                <label htmlFor="fullBodyLevel" className="text-sm font-medium text-foreground whitespace-nowrap">
                  Level:
                </label>
                <select
                  id="fullBodyLevel"
                  value={fullBodyDefaultLevel}
                  onChange={(e) => setFullBodyDefaultLevel(Number(e.target.value) as SorenessLevel)}
                  className="bg-background-input border border-border rounded px-2 py-1 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
                >
                  {SORENESS_LEVELS.map((level) => (
                    <option key={level.value} value={level.value}>
                      {level.value} - {level.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <HumanBodyMap
              selectedMuscles={selectedMuscles}
              onToggleMuscle={toggleMuscle}
              className="w-full"
            />
          </div>

          <div className="flex flex-col">
            <MuscleList
              selectedMuscles={selectedMuscles}
              onToggleMuscle={toggleMuscle}
              className="flex-1 overflow-y-auto max-h-96"
            />

            {selectedMuscles.length > 0 && (
              <div className="mt-4 space-y-3">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Soreness Levels
                  </label>
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {selectedMuscles.map((muscle) => (
                      <div key={muscle} className="flex items-center gap-2">
                        <span className="text-sm text-foreground w-32 truncate">
                          {MUSCLE_DISPLAY_NAMES[muscle]}
                        </span>
                        <div className="flex gap-1 flex-1">
                          {SORENESS_LEVELS.map((level) => (
                            <button
                              key={level.value}
                              type="button"
                              onClick={() => setMuscleSorenessLevel(muscle, level.value)}
                              className={cn(
                                'flex-1 px-2 py-1 text-xs rounded-md border transition-colors',
                                sorenessLevels[muscle] === level.value
                                  ? level.color
                                  : 'bg-background-card text-foreground-muted hover:bg-background-secondary'
                              )}
                            >
                              {level.value}
                            </button>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <label htmlFor="notes" className="block text-sm font-medium text-foreground mb-2">
                    Notes (optional)
                  </label>
                  <textarea
                    id="notes"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Add any additional notes about your soreness..."
                    rows={3}
                    className="w-full px-3 py-2 bg-background-input border border-border rounded-lg text-sm text-foreground placeholder-foreground-subtle focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-none"
                  />
                </div>
              </div>
            )}

            <div className="flex gap-2 mt-4">
              <Button
                type="button"
                variant="outline"
                onClick={clearAll}
                disabled={selectedMuscles.length === 0 || isSubmitting}
                className="flex-1"
              >
                <RotateCcw className="w-4 h-4 mr-2" />
                Clear All
              </Button>
              <Button
                type="button"
                onClick={handleSubmit}
                disabled={selectedMuscles.length === 0 || isSubmitting}
                className="flex-1"
              >
                {isSubmitting ? (
                  'Submitting...'
                ) : (
                  <>
                    <Check className="w-4 h-4 mr-2" />
                    Submit Report
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

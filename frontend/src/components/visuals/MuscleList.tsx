import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { MuscleGroup, BodyZone } from '@/types/anatomy';
import { ZONE_MAPPING, BODY_ZONE_LABELS, MUSCLE_DISPLAY_NAMES } from '@/types/anatomy';

interface MuscleListProps {
  selectedMuscles: MuscleGroup[];
  onToggleMuscle: (muscle: MuscleGroup) => void;
  className?: string;
}

const ZONES_ORDER: BodyZone[] = [
  'shoulder',
  'anterior upper',
  'posterior upper',
  'core',
  'anterior lower',
  'posterior lower',
];

export function MuscleList({ selectedMuscles, onToggleMuscle, className }: MuscleListProps) {
  const [expandedZones, setExpandedZones] = useState<Set<BodyZone>>(new Set(ZONES_ORDER));

  const toggleZone = (zone: BodyZone) => {
    setExpandedZones((prev) => {
      const next = new Set(prev);
      if (next.has(zone)) {
        next.delete(zone);
      } else {
        next.add(zone);
      }
      return next;
    });
  };

  const isZoneSelected = (zone: BodyZone) => {
    return ZONE_MAPPING[zone].some((muscle) => selectedMuscles.includes(muscle));
  };

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      {ZONES_ORDER.map((zone) => {
        const muscles = ZONE_MAPPING[zone];
        const isExpanded = expandedZones.has(zone);
        const isSelected = isZoneSelected(zone);
        const selectedCount = muscles.filter((m) => selectedMuscles.includes(m)).length;

        return (
          <div key={zone} className="border border-border rounded-lg overflow-hidden">
            <button
              type="button"
              onClick={() => toggleZone(zone)}
              className={cn(
                'w-full px-4 py-3 flex items-center justify-between bg-background-card',
                'hover:bg-background-secondary transition-colors',
                isSelected && 'border-l-2 border-l-accent'
              )}
            >
              <div className="flex items-center gap-2">
                {isExpanded ? (
                  <ChevronDown className="w-4 h-4 text-foreground-muted" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-foreground-muted" />
                )}
                <span className="font-medium text-foreground">
                  {BODY_ZONE_LABELS[zone]}
                </span>
                {selectedCount > 0 && (
                  <span className="text-xs bg-accent/10 text-accent px-2 py-0.5 rounded-full">
                    {selectedCount}
                  </span>
                )}
              </div>
            </button>

            {isExpanded && (
              <div className="px-4 py-2 bg-background-secondary space-y-1">
                {muscles.map((muscle) => (
                  <button
                    key={muscle}
                    type="button"
                    onClick={() => onToggleMuscle(muscle)}
                    className={cn(
                      'w-full px-3 py-2 rounded-md text-sm text-left flex items-center justify-between',
                      'transition-colors',
                      selectedMuscles.includes(muscle)
                        ? 'bg-accent text-white'
                        : 'bg-background-card text-foreground hover:bg-background-elevated'
                    )}
                  >
                    <span>{MUSCLE_DISPLAY_NAMES[muscle]}</span>
                    {selectedMuscles.includes(muscle) && (
                      <span className="text-xs opacity-75">Selected</span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

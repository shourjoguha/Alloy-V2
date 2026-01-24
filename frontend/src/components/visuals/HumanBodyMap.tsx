import { useState, useCallback, memo } from 'react';
import { cn } from '@/lib/utils';
import type { MuscleGroup } from '@/types/anatomy';

interface HumanBodyMapProps {
  selectedMuscles: MuscleGroup[];
  onToggleMuscle: (muscle: MuscleGroup) => void;
  className?: string;
}

type BodyView = 'front' | 'back';

const MUSCLE_COLORS = {
  unselected: '#1E293B',
  selected: '#F59E0B',
  hover: '#D97706',
} as const;

interface MusclePathProps {
  id: MuscleGroup;
  pathData: string;
  isSelected: boolean;
  onClick: () => void;
  ariaLabel: string;
}

const MusclePath = memo(({ id, pathData, isSelected, onClick, ariaLabel }: MusclePathProps) => {
  return (
    <path
      id={id}
      d={pathData}
      fill={isSelected ? MUSCLE_COLORS.selected : MUSCLE_COLORS.unselected}
      className="transition-colors duration-200 cursor-pointer hover:fill-[#D97706] active:scale-95"
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        onClick();
      }}
      aria-label={ariaLabel}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
      style={{ touchAction: 'manipulation' }}
    />
  );
});

MusclePath.displayName = 'MusclePath';

const FRONT_MUSCLES: Array<{ id: MuscleGroup; path: string; label: string }> = [
  {
    id: 'front_delts',
    path: 'M85 95 L95 100 L105 95 L100 105 Z',
    label: 'Front Delts',
  },
  {
    id: 'chest',
    path: 'M70 100 L90 95 L110 95 L130 100 L125 125 L75 125 Z',
    label: 'Chest',
  },
  {
    id: 'biceps',
    path: 'M65 130 L70 160 L80 165 L85 130 Z M115 130 L120 165 L130 160 L135 130 Z',
    label: 'Biceps',
  },
  {
    id: 'forearms',
    path: 'M70 170 L75 210 L85 215 L82 170 Z M115 170 L118 215 L125 210 L130 170 Z',
    label: 'Forearms',
  },
  {
    id: 'core',
    path: 'M80 130 L120 130 L125 180 L75 180 Z',
    label: 'Core',
  },
  {
    id: 'obliques',
    path: 'M70 125 L80 130 L75 180 L65 175 Z M130 125 L135 175 L125 180 L120 130 Z',
    label: 'Obliques',
  },
  {
    id: 'quadriceps',
    path: 'M75 185 L95 180 L95 280 L70 285 Z M105 180 L125 185 L130 285 L105 280 Z',
    label: 'Quadriceps',
  },
  {
    id: 'hip_flexors',
    path: 'M70 180 L80 175 L95 180 L90 185 Z M110 185 L120 180 L130 175 L125 185 Z',
    label: 'Hip Flexors',
  },
  {
    id: 'adductors',
    path: 'M95 185 L105 185 L105 275 L95 275 Z',
    label: 'Adductors',
  },
  {
    id: 'calves',
    path: 'M70 290 L80 285 L85 350 L70 355 Z M120 285 L130 290 L130 355 L115 350 Z',
    label: 'Calves',
  },
];

const BACK_MUSCLES: Array<{ id: MuscleGroup; path: string; label: string }> = [
  {
    id: 'side_delts',
    path: 'M70 95 L80 100 L90 95 L85 105 Z M110 95 L120 100 L130 95 L125 105 Z',
    label: 'Side Delts',
  },
  {
    id: 'rear_delts',
    path: 'M60 100 L70 105 L75 100 L65 95 Z M125 100 L130 95 L140 100 L135 105 Z',
    label: 'Rear Delts',
  },
  {
    id: 'lats',
    path: 'M65 110 L75 105 L85 110 L90 145 L70 150 Z M115 110 L125 105 L135 110 L130 150 L110 145 Z',
    label: 'Lats',
  },
  {
    id: 'upper_back',
    path: 'M85 100 L95 95 L105 95 L115 100 L110 140 L90 140 Z',
    label: 'Upper Back',
  },
  {
    id: 'triceps',
    path: 'M65 155 L70 185 L80 190 L85 155 Z M115 155 L120 190 L130 185 L135 155 Z',
    label: 'Triceps',
  },
  {
    id: 'forearms',
    path: 'M65 195 L70 235 L80 240 L77 195 Z M120 195 L123 240 L130 235 L135 195 Z',
    label: 'Forearms',
  },
  {
    id: 'lower_back',
    path: 'M80 150 L100 145 L120 150 L125 185 L75 185 Z',
    label: 'Lower Back',
  },
  {
    id: 'glutes',
    path: 'M70 190 L85 185 L115 185 L130 190 L125 220 L75 220 Z',
    label: 'Glutes',
  },
  {
    id: 'hamstrings',
    path: 'M70 225 L85 220 L90 320 L65 325 Z M110 220 L125 225 L135 325 L110 320 Z',
    label: 'Hamstrings',
  },
  {
    id: 'calves',
    path: 'M65 330 L75 325 L80 390 L65 395 Z M125 325 L135 330 L135 395 L120 390 Z',
    label: 'Calves',
  },
];

export function HumanBodyMap({ selectedMuscles, onToggleMuscle, className }: HumanBodyMapProps) {
  const [view, setView] = useState<BodyView>('front');

  const handleToggle = useCallback(
    (muscle: MuscleGroup) => {
      onToggleMuscle(muscle);
    },
    [onToggleMuscle]
  );

  const muscles = view === 'front' ? FRONT_MUSCLES : BACK_MUSCLES;

  return (
    <div className={cn('flex flex-col items-center', className)}>
      <div className="flex gap-2 mb-4">
        <button
          type="button"
          onClick={() => setView('front')}
          className={cn(
            'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
            view === 'front'
              ? 'bg-cta text-white'
              : 'bg-background-input text-foreground hover:bg-background-secondary'
          )}
        >
          Front
        </button>
        <button
          type="button"
          onClick={() => setView('back')}
          className={cn(
            'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
            view === 'back'
              ? 'bg-cta text-white'
              : 'bg-background-input text-foreground hover:bg-background-secondary'
          )}
        >
          Back
        </button>
      </div>

      <svg
        viewBox="0 0 200 420"
        className="w-full max-w-xs h-auto"
        xmlns="http://www.w3.org/2000/svg"
        role="img"
        aria-label={`Human body ${view} view - click to select muscles`}
      >
        <g>
          {muscles.map((muscle) => (
            <MusclePath
              key={muscle.id}
              id={muscle.id}
              pathData={muscle.path}
              isSelected={selectedMuscles.includes(muscle.id)}
              onClick={() => handleToggle(muscle.id)}
              ariaLabel={muscle.label}
            />
          ))}
        </g>
      </svg>

      <div className="mt-4 flex gap-4 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: MUSCLE_COLORS.unselected }} />
          <span className="text-foreground-muted">Normal</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: MUSCLE_COLORS.selected }} />
          <span className="text-foreground-muted">Sore</span>
        </div>
      </div>
    </div>
  );
}

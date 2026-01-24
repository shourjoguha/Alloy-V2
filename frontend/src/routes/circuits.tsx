import { useState } from 'react';
import { createFileRoute, Link } from '@tanstack/react-router';
import { Flame, Clock, ListChecks, ChevronDown, ChevronRight, Edit } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/common/Spinner';
import { useCircuits } from '@/api/circuits';
import { CircuitType, type CircuitTemplate } from '@/types';

export const Route = createFileRoute('/circuits')({
  component: CircuitsPage,
});

type CircuitFilter = 'all' | CircuitType;

const CIRCUIT_FILTERS: { key: CircuitFilter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: CircuitType.ROUNDS_FOR_TIME, label: 'Rounds for time' },
  { key: CircuitType.AMRAP, label: 'AMRAP' },
  { key: CircuitType.EMOM, label: 'EMOM' },
  { key: CircuitType.CHIPPER, label: 'Chipper' },
  { key: CircuitType.LADDER, label: 'Ladder' },
  { key: CircuitType.TABATA, label: 'Tabata' },
  { key: CircuitType.STATION, label: 'Station' },
];

function CircuitsPage() {
  const [filter, setFilter] = useState<CircuitFilter>('all');
  const { data: circuits, isLoading } = useCircuits(filter);

  if (isLoading) {
    return (
      <div className="container-app py-6 flex justify-center">
        <Spinner size="sm" />
      </div>
    );
  }

  return (
    <div className="container-app py-6 space-y-4 animate-fade-in">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Circuits</h1>
      </div>

      <div className="flex gap-2 overflow-x-auto pb-1">
        {CIRCUIT_FILTERS.map((f) => (
          <Button
            key={f.key}
            size="sm"
            variant={filter === f.key ? 'cta' : 'secondary'}
            onClick={() => setFilter(f.key)}
            className="whitespace-nowrap"
          >
            {f.label}
          </Button>
        ))}
      </div>

      {!circuits || circuits.length === 0 ? (
        <Card className="p-6 text-center">
          <div className="text-foreground-muted">No circuits found for this filter.</div>
        </Card>
      ) : (
        <div className="space-y-3">
          {circuits.map((circuit) => (
            <CircuitCard key={circuit.id} circuit={circuit} />
          ))}
        </div>
      )}
    </div>
  );
}

interface CircuitExercise {
  original?: string;
  movement_id?: number | null;
  movement_name?: string | null;
  reps?: number | null;
  distance_meters?: number | null;
  duration_seconds?: number | null;
  rest_seconds?: number | null;
  notes?: string | null;
  metric_type?: string | null;
  rx_weight_male?: number | null;
  rx_weight_female?: number | null;
}

interface CircuitCardProps {
  circuit: CircuitTemplate;
}

function CircuitCard({ circuit }: CircuitCardProps) {
  const [expanded, setExpanded] = useState(false);

  const formatType = (type: CircuitType) => type.replace(/_/g, ' ');

  const exercises = (circuit.exercises_json ?? []) as CircuitExercise[];
  const workoutExercises = exercises.filter(
    (ex) =>
      ex.movement_id != null ||
      (ex.movement_name && ex.movement_name.trim().length > 0) ||
      (ex.original && ex.original.trim().length > 0)
  );

  const description = circuit.description || '';
  let metaTokens: string[] = [];
  let stimulusText: string | undefined;

  if (description) {
    const parts = description.split('\n\n');
    const first = parts[0] || '';
    const rest = parts.slice(1).join('\n\n');
    const hasMeta =
      first.includes('Time Cap:') ||
      first.includes('Rounds:') ||
      first.includes('Interval:');

    if (hasMeta) {
      metaTokens = first.split('|').map((t) => t.trim()).filter(Boolean);
      stimulusText = rest.trim() || undefined;
    } else {
      stimulusText = description;
    }
  }

  const lowerTokens = metaTokens.map((t) => t.toLowerCase());
  const timeIdx = lowerTokens.findIndex((t) => t.startsWith('time cap'));
  const roundsIdx = lowerTokens.findIndex((t) => t.startsWith('rounds'));
  const intervalIdx = lowerTokens.findIndex((t) => t.startsWith('interval'));

  const timeToken = timeIdx >= 0 ? metaTokens[timeIdx] : undefined;
  const roundsToken = roundsIdx >= 0 ? metaTokens[roundsIdx] : undefined;
  const intervalToken = intervalIdx >= 0 ? metaTokens[intervalIdx] : undefined;

  const formatExerciseScheme = (ex: CircuitExercise): string => {
    const metric = ex.metric_type?.toLowerCase() ?? '';

    if (ex.reps === 999 && ex.notes && ex.notes.toLowerCase().includes('max')) {
      if (metric === 'calories') {
        return 'max cals';
      }
      return 'max reps';
    }

    if (metric === 'time' && ex.duration_seconds) {
      const total = ex.duration_seconds;
      if (total % 60 === 0) {
        return `${total / 60} min`;
      }
      return `${total}s`;
    }

    if (metric === 'distance' && ex.distance_meters) {
      const meters = ex.distance_meters;
      if (meters >= 1000 && meters % 1000 === 0) {
        return `${meters / 1000} km`;
      }
      return `${meters} m`;
    }

    if (metric === 'calories' && ex.reps) {
      return `${ex.reps} cal`;
    }

    if (ex.reps) {
      return `${ex.reps} reps`;
    }

    return '';
  };

  return (
    <Card className="p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <button
          type="button"
          className="flex flex-1 items-start gap-2 text-left"
          onClick={() => setExpanded((prev) => !prev)}
        >
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-foreground-muted mt-0.5" />
          ) : (
            <ChevronRight className="h-4 w-4 text-foreground-muted mt-0.5" />
          )}
          <div className="space-y-1 flex-1">
            <div className="flex items-center gap-2">
              <h2 className="font-medium">{circuit.name}</h2>
              <span className="inline-flex items-center rounded-full bg-accent/10 px-2 py-0.5 text-[10px] font-medium text-accent uppercase tracking-wide">
                {formatType(circuit.circuit_type)}
              </span>
            </div>
            {(timeToken || roundsToken || intervalToken) && (
              <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-foreground-muted">
                {timeToken && (
                  <span className="inline-flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {timeToken.replace(/time cap[:]?/i, '').trim()}
                  </span>
                )}
                {roundsToken && (
                  <span className="inline-flex items-center gap-1">
                    <ListChecks className="h-3 w-3" />
                    {roundsToken.replace(/rounds[:]?/i, '').trim()}
                  </span>
                )}
                {intervalToken && (
                  <span className="inline-flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {intervalToken.replace(/interval[:]?/i, '').trim()}
                  </span>
                )}
              </div>
            )}
            {workoutExercises.length > 0 && (
              <div className="space-y-1 text-xs">
                {workoutExercises.map((ex, index) => {
                  const name = (ex.movement_name || ex.original || '').trim();
                  const scheme = formatExerciseScheme(ex);
                  if (!name && !scheme) return null;
                  return (
                    <div key={`${name}-${index}`} className="flex items-baseline gap-2">
                      <span className="text-foreground-muted">{index + 1}.</span>
                      <span className="text-foreground">
                        {scheme && <span className="font-medium mr-1">{scheme}</span>}
                        {name}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </button>
        <div className="flex flex-col items-end gap-1 text-xs text-foreground-muted">
          <span className="inline-flex items-center gap-1">
            <Flame className="h-3 w-3" />
            Level {circuit.difficulty_tier}
          </span>
        </div>
      </div>

      {circuit.tags && circuit.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {circuit.tags.map((tag) => (
            <span
              key={tag}
              className="rounded-full border border-border px-2 py-0.5 text-[10px] text-foreground-muted"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {expanded && (
        <div className="space-y-3 pt-1">
          {stimulusText && (
            <p className="text-xs text-foreground-muted whitespace-pre-line border-t border-border pt-2">
              {stimulusText}
            </p>
          )}
          
          {import.meta.env.VITE_ADMIN_API_TOKEN && (
            <div className="flex justify-end pt-2 border-t border-border">
              <Button asChild size="sm" variant="secondary" className="h-7 text-xs gap-1.5">
                <Link 
                  to="/admin/circuits/$circuitId" 
                  params={{ circuitId: String(circuit.id) }}
                >
                  <Edit className="h-3 w-3" />
                  Edit Circuit
                </Link>
              </Button>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

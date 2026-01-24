import { useState } from 'react';
import { createFileRoute, Link } from '@tanstack/react-router';
import { Trash, ArrowUp, ArrowDown } from 'lucide-react';
import { useCircuitAdmin, useUpdateCircuitAdmin } from '@/api/circuits';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/common/Spinner';

export const Route = createFileRoute('/admin/circuits/$circuitId')({
  component: AdminCircuitEditorPage,
});

interface EditableExercise {
  movement_name?: string | null;
  reps?: number | null;
  duration_seconds?: number | null;
  distance_meters?: number | null;
  rest_seconds?: number | null;
  rx_weight_male?: number | null;
  rx_weight_female?: number | null;
  metric_type?: string | null;
  notes?: string | null;
  original?: string | null;
}

function normalizeExercises(exercises: unknown[]): EditableExercise[] {
  return (exercises ?? []).map((raw) => {
    const ex = raw as Record<string, unknown>;
    return {
      movement_name: (ex.movement_name as string) ?? '',
      reps: (ex.reps as number) ?? null,
      duration_seconds: (ex.duration_seconds as number) ?? null,
      distance_meters: (ex.distance_meters as number) ?? null,
      rest_seconds: (ex.rest_seconds as number) ?? null,
      rx_weight_male: (ex.rx_weight_male as number) ?? null,
      rx_weight_female: (ex.rx_weight_female as number) ?? null,
      metric_type: (ex.metric_type as string) ?? 'reps',
      notes: (ex.notes as string) ?? '',
      original: (ex.original as string) ?? '',
    };
  });
}

function AdminCircuitEditorPage() {
  const { circuitId } = Route.useParams();
  const numericId = Number(circuitId);
  const { data, isLoading, error } = useCircuitAdmin(numericId);
  const [localExercises, setLocalExercises] = useState<EditableExercise[] | null>(null);
  const updateMutation = useUpdateCircuitAdmin(numericId);

  if (isLoading) {
    return (
      <div className="container-app py-6 flex justify-center">
        <Spinner size="sm" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="container-app py-6">
        <Card className="p-6 space-y-3">
          <h1 className="text-lg font-semibold">Admin Circuit Editor</h1>
          <p className="text-sm text-foreground-muted">Unable to load circuit.</p>
          <Link to="/circuits" className="text-accent text-sm hover:underline">
            Back to circuits
          </Link>
        </Card>
      </div>
    );
  }

  const exercises = localExercises ?? normalizeExercises(data.exercises_json ?? []);

  const handleChange = (index: number, field: keyof EditableExercise, value: string) => {
    const updated = exercises.map((ex, i) => {
      if (i !== index) return ex;
      if (field === 'reps' || field === 'duration_seconds' || field === 'distance_meters' || field === 'rest_seconds' || field === 'rx_weight_male' || field === 'rx_weight_female') {
        const num = value === '' ? null : Number(value);
        return { ...ex, [field]: Number.isNaN(num) ? null : num };
      }
      return { ...ex, [field]: value };
    });
    setLocalExercises(updated);
  };

  const handleAddRow = () => {
    const next: EditableExercise = {
      movement_name: '',
      reps: null,
      duration_seconds: null,
      distance_meters: null,
      rest_seconds: null,
      rx_weight_male: null,
      rx_weight_female: null,
      metric_type: 'reps',
      notes: '',
      original: '',
    };
    setLocalExercises((prev) => (prev ?? exercises).concat(next));
  };

  const handleMoveUp = (index: number) => {
    if (index === 0) return;
    const updated = [...exercises];
    [updated[index - 1], updated[index]] = [updated[index], updated[index - 1]];
    setLocalExercises(updated);
  };

  const handleMoveDown = (index: number) => {
    if (index === exercises.length - 1) return;
    const updated = [...exercises];
    [updated[index + 1], updated[index]] = [updated[index], updated[index + 1]];
    setLocalExercises(updated);
  };

  const handleDeleteRow = (index: number) => {
    const updated = exercises.filter((_, i) => i !== index);
    setLocalExercises(updated);
  };

  const handleSave = () => {
    const payload = exercises.map((ex) => ({
      movement_name: ex.movement_name || '',
      reps: ex.reps,
      duration_seconds: ex.duration_seconds,
      distance_meters: ex.distance_meters,
      rest_seconds: ex.rest_seconds,
      rx_weight_male: ex.rx_weight_male,
      rx_weight_female: ex.rx_weight_female,
      metric_type: ex.metric_type || 'reps',
      notes: ex.notes,
      original: ex.original,
    }));
    updateMutation.mutate({ exercises_json: payload });
  };

  return (
    <div className="container-app py-6 space-y-4">
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <h1 className="text-lg font-semibold">Admin Circuit Editor</h1>
          <p className="text-xs text-foreground-muted">
            {data.name} · {data.circuit_type}
          </p>
        </div>
        <Link to="/circuits" className="text-accent text-xs hover:underline">
          Back to circuits
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card className="p-4 space-y-3">
          <h2 className="text-sm font-medium">Raw Workout Text</h2>
          {data.raw_workout ? (
            <pre className="text-xs text-foreground-muted whitespace-pre-wrap max-h-[500px] overflow-y-auto bg-background-elevated rounded-md p-3 border border-border">
              {data.raw_workout}
            </pre>
          ) : (
            <p className="text-xs text-foreground-muted">
              No raw workout text available for this circuit.
            </p>
          )}
        </Card>

        <Card className="p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium">Exercises</h2>
            <Button size="sm" variant="secondary" onClick={handleAddRow}>
              Add movement
            </Button>
          </div>

          <div className="space-y-2 max-h-[500px] overflow-y-auto">
            {exercises.length === 0 && (
              <p className="text-xs text-foreground-muted">No movements defined yet.</p>
            )}

            {exercises.map((ex, index) => (
              <div
                key={index}
                className="border border-border rounded-md p-3 space-y-2 bg-background-elevated"
              >
                <div className="flex items-center gap-2">
                  <div className="flex flex-col gap-0.5">
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-4 w-5 p-0"
                      onClick={() => handleMoveUp(index)}
                      disabled={index === 0}
                    >
                      <ArrowUp className="h-3 w-3" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-4 w-5 p-0"
                      onClick={() => handleMoveDown(index)}
                      disabled={index === exercises.length - 1}
                    >
                      <ArrowDown className="h-3 w-3" />
                    </Button>
                  </div>
                  <span className="text-[10px] text-foreground-muted min-w-[1.5rem]">#{index + 1}</span>
                  <input
                    type="text"
                    placeholder="Movement name"
                    value={ex.movement_name ?? ''}
                    onChange={(e) => handleChange(index, 'movement_name', e.target.value)}
                    className="flex-1 h-8 rounded-md bg-background border border-border px-2 text-xs focus:outline-none focus:border-accent"
                  />
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-8 w-8 p-0 text-error hover:text-error hover:bg-error/10"
                    onClick={() => handleDeleteRow(index)}
                    title="Delete movement"
                  >
                    <Trash className="h-4 w-4" />
                  </Button>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-[11px]">
                  <div className="space-y-1">
                    <label className="block text-foreground-muted">Reps</label>
                    <input
                      type="number"
                      value={ex.reps ?? ''}
                      onChange={(e) => handleChange(index, 'reps', e.target.value)}
                      className="w-full h-8 rounded-md bg-background border border-border px-2 text-xs focus:outline-none focus:border-accent"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="block text-foreground-muted">Duration (sec)</label>
                    <input
                      type="number"
                      value={ex.duration_seconds ?? ''}
                      onChange={(e) => handleChange(index, 'duration_seconds', e.target.value)}
                      className="w-full h-8 rounded-md bg-background border border-border px-2 text-xs focus:outline-none focus:border-accent"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="block text-foreground-muted">Distance (m)</label>
                    <input
                      type="number"
                      value={ex.distance_meters ?? ''}
                      onChange={(e) => handleChange(index, 'distance_meters', e.target.value)}
                      className="w-full h-8 rounded-md bg-background border border-border px-2 text-xs focus:outline-none focus:border-accent"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="block text-foreground-muted">Rest (sec)</label>
                    <input
                      type="number"
                      value={ex.rest_seconds ?? ''}
                      onChange={(e) => handleChange(index, 'rest_seconds', e.target.value)}
                      className="w-full h-8 rounded-md bg-background border border-border px-2 text-xs focus:outline-none focus:border-accent"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="block text-foreground-muted">RX Male</label>
                    <input
                      type="number"
                      value={ex.rx_weight_male ?? ''}
                      onChange={(e) => handleChange(index, 'rx_weight_male', e.target.value)}
                      className="w-full h-8 rounded-md bg-background border border-border px-2 text-xs focus:outline-none focus:border-accent"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="block text-foreground-muted">RX Female</label>
                    <input
                      type="number"
                      value={ex.rx_weight_female ?? ''}
                      onChange={(e) => handleChange(index, 'rx_weight_female', e.target.value)}
                      className="w-full h-8 rounded-md bg-background border border-border px-2 text-xs focus:outline-none focus:border-accent"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="block text-foreground-muted">Metric type</label>
                    <input
                      type="text"
                      value={ex.metric_type ?? ''}
                      onChange={(e) => handleChange(index, 'metric_type', e.target.value)}
                      className="w-full h-8 rounded-md bg-background border border-border px-2 text-xs focus:outline-none focus:border-accent"
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="block text-[11px] text-foreground-muted">Notes / original</label>
                  <textarea
                    value={ex.notes ?? ex.original ?? ''}
                    onChange={(e) => handleChange(index, 'notes', e.target.value)}
                    className="w-full min-h-[48px] rounded-md bg-background border border-border px-2 py-1 text-xs focus:outline-none focus:border-accent"
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="pt-2 flex justify-end">
            <Button
              size="sm"
              variant="cta"
              onClick={handleSave}
              disabled={updateMutation.isPending}
            >
              {updateMutation.isPending ? 'Saving...' : 'Save changes'}
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}

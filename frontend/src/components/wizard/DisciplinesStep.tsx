import { useProgramWizardStore, DISCIPLINES } from '@/stores/program-wizard-store';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';

export function DisciplinesStep() {
  const { disciplines, updateDisciplineWeight, getTotalDisciplineWeight, isDisciplinesValid } = useProgramWizardStore();
  const totalWeight = getTotalDisciplineWeight();
  const remaining = 10 - totalWeight;

  const getDisciplineWeight = (id: string) => {
    const found = disciplines.find((d) => d.discipline === id);
    return found?.weight ?? 0;
  };

  const handleWeightChange = (discipline: string, delta: number) => {
    const currentWeight = getDisciplineWeight(discipline);
    const newWeight = Math.max(0, Math.min(10, currentWeight + delta));
    
    // Don't allow total to exceed 10
    if (delta > 0 && totalWeight >= 10) return;
    
    updateDisciplineWeight(discipline, newWeight);
  };

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-xl font-bold">Training Style</h2>
        <p className="text-foreground-muted text-sm">
          Distribute 10 dollars across the training styles you enjoy. This influences exercise selection.
        </p>
      </div>

      {/* Progress indicator */}
      <Card variant="grouped" className="p-4">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium">Budget Remaining</span>
          <span className={cn(
            "text-lg font-bold",
            remaining === 0 ? "text-cta" : remaining < 0 ? "text-error" : "text-primary"
          )}>
            ${remaining}
          </span>
        </div>
        <div className="h-2 bg-background-input rounded-full overflow-hidden">
          <div
            className={cn(
              "h-full transition-all duration-300",
              totalWeight === 10 ? "bg-cta" : "bg-primary"
            )}
            style={{ width: `${Math.min(100, totalWeight * 10)}%` }}
          />
        </div>
      </Card>

      {/* Discipline cards */}
      <div className="grid gap-3">
        {DISCIPLINES.map((disc) => {
          const weight = getDisciplineWeight(disc.id);
          const isActive = weight > 0;
          const canAdd = totalWeight < 10;

          return (
            <Card
              key={disc.id}
              variant={isActive ? "selected" : "grouped"}
              className="p-4"
            >
              <div className="flex items-center gap-4">
                <div className="text-2xl">{disc.icon}</div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold">{disc.name}</h3>
                  <p className="text-xs text-foreground-muted">{disc.description}</p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleWeightChange(disc.id, -1)}
                    disabled={weight === 0}
                    className={cn(
                      "h-8 w-8 rounded-lg flex items-center justify-center text-lg font-bold transition-colors",
                      weight === 0
                        ? "bg-background-input text-foreground-subtle cursor-not-allowed"
                        : "bg-background-input hover:bg-primary hover:text-white"
                    )}
                  >
                    −
                  </button>
                  <div className={cn(
                    "w-10 h-10 rounded-lg flex items-center justify-center text-lg font-bold",
                    isActive ? "bg-primary text-white" : "bg-background-input text-foreground"
                  )}>
                    ${weight}
                  </div>
                  <button
                    onClick={() => handleWeightChange(disc.id, 1)}
                    disabled={!canAdd}
                    className={cn(
                      "h-8 w-8 rounded-lg flex items-center justify-center text-lg font-bold transition-colors",
                      !canAdd
                        ? "bg-background-input text-foreground-subtle cursor-not-allowed"
                        : "bg-background-input hover:bg-primary hover:text-white"
                    )}
                  >
                    +
                  </button>
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Validation message */}
      {!isDisciplinesValid() && totalWeight > 0 && (
        <p className="text-center text-sm text-foreground-muted">
          Distribute all $10 to continue (currently ${totalWeight})
        </p>
      )}

      {/* Skip hint */}
      <p className="text-center text-xs text-foreground-subtle">
        💡 Not sure? You can skip this and Jerome will decide based on your goals.
      </p>
    </div>
  );
}

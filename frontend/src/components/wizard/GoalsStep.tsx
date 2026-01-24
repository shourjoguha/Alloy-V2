import { Goal } from '@/types';
import { useProgramWizardStore } from '@/stores/program-wizard-store';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';

const GOALS = [
  { id: Goal.STRENGTH, name: 'Strength', description: 'Get stronger, lift heavier', icon: '🏋️' },
  { id: Goal.HYPERTROPHY, name: 'Hypertrophy', description: 'Build muscle mass', icon: '💪' },
  { id: Goal.ENDURANCE, name: 'Endurance', description: 'Improve stamina & work capacity', icon: '🫀' },
  { id: Goal.FAT_LOSS, name: 'Fat Loss', description: 'Optimize for body recomposition', icon: '🔥' },
  { id: Goal.MOBILITY, name: 'Mobility', description: 'Flexibility & movement quality', icon: '🧘' },
  { id: Goal.EXPLOSIVENESS, name: 'Explosiveness', description: 'Power & rate of force development', icon: '⚡' },
  { id: Goal.SPEED, name: 'Speed', description: 'Quickness & agility', icon: '🏃' },
] as const;

export function GoalsStep() {
  const { goals, updateGoalWeight, getTotalGoalWeight, isGoalsValid } = useProgramWizardStore();
  const totalWeight = getTotalGoalWeight();
  const remaining = 10 - totalWeight;

  const getGoalWeight = (goal: Goal) => {
    const found = goals.find((g) => g.goal === goal);
    return found?.weight ?? 0;
  };

  const handleWeightChange = (goal: Goal, delta: number) => {
    const currentWeight = getGoalWeight(goal);
    const newWeight = Math.max(0, Math.min(10, currentWeight + delta));
    
    // Don't allow total to exceed 10
    if (delta > 0 && totalWeight >= 10) return;
    
    // Don't allow more than 3 goals with weight > 0
    const activeGoals = goals.filter((g) => g.weight > 0);
    if (delta > 0 && currentWeight === 0 && activeGoals.length >= 3) return;
    
    updateGoalWeight(goal, newWeight);
  };

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-xl font-bold">What are your goals?</h2>
        <p className="text-foreground-muted text-sm">
          Distribute 10 dollars across 1-3 goals. This tells Jerome how to prioritize your training.
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
        {goals.length > 3 && (
          <p className="text-xs text-error mt-2">
            Maximum 3 goals allowed (currently {goals.length})
          </p>
        )}
      </Card>

      {/* Goal cards */}
      <div className="grid gap-3">
        {GOALS.map((goal) => {
          const weight = getGoalWeight(goal.id);
          const isActive = weight > 0;
          const canAdd = totalWeight < 10 && (isActive || goals.length < 3);

          return (
            <Card
              key={goal.id}
              variant={isActive ? "selected" : "grouped"}
              className="p-4"
            >
              <div className="flex items-center gap-4">
                <div className="text-2xl">{goal.icon}</div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold">{goal.name}</h3>
                  <p className="text-xs text-foreground-muted">{goal.description}</p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleWeightChange(goal.id, -1)}
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
                    onClick={() => handleWeightChange(goal.id, 1)}
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
      {!isGoalsValid() && totalWeight > 0 && (
        <p className="text-center text-sm text-foreground-muted">
          {goals.length === 0
            ? `Select 1-3 goals to begin`
            : goals.length > 3
            ? `Too many goals selected (max 3, currently ${goals.length})`
            : `Distribute all $10 (currently $${totalWeight})`
          }
        </p>
      )}
    </div>
  );
}

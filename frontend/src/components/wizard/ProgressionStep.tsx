import { ProgressionStyle } from '@/types';
import { useProgramWizardStore } from '@/stores/program-wizard-store';
import { Card } from '@/components/ui/card';

const PROGRESSION_STYLES = [
  {
    id: ProgressionStyle.DOUBLE_PROGRESSION,
    name: 'Double Progression',
    description: 'Add reps until you hit the top of the range, then add weight',
    example: '3x8-12 → add reps → 3x12 → add weight → 3x8',
    icon: '📈',
    recommended: true,
  },
  {
    id: ProgressionStyle.SINGLE_PROGRESSION,
    name: 'Single Progression',
    description: 'Add weight each session while keeping reps fixed',
    example: '3x5 @ 100 → 3x5 @ 105 → 3x5 @ 110',
    icon: '⬆️',
    recommended: false,
  },
  {
    id: ProgressionStyle.PAUSED_VARIATIONS,
    name: 'Paused Variations',
    description: 'Progress through tempo changes and pauses before adding weight',
    example: 'Tempo reps → Paused reps → Regular reps + weight',
    icon: '⏸️',
    recommended: false,
  },
  {
    id: ProgressionStyle.BUILD_TO_DROP,
    name: 'Build to Drop',
    description: 'Build up intensity, then drop and rebuild with higher volume',
    example: 'Week 1-3: Build → Week 4: Deload → Restart higher',
    icon: '🔄',
    recommended: false,
  },
] as const;

export function ProgressionStep() {
  const { progressionStyle, setProgressionStyle } = useProgramWizardStore();

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-xl font-bold">Progression Style</h2>
        <p className="text-foreground-muted text-sm">
          How should your training evolve over time?
        </p>
      </div>

      <div className="grid gap-3">
        {PROGRESSION_STYLES.map((style) => (
          <Card
            key={style.id}
            variant="interactive"
            selected={progressionStyle === style.id}
            onClick={() => setProgressionStyle(style.id)}
            className="p-4"
          >
            <div className="space-y-2">
              <div className="flex items-start gap-3">
                <div className="text-2xl">{style.icon}</div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">{style.name}</h3>
                    {style.recommended && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-cta/20 text-cta">
                        Recommended
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-foreground-muted mt-1">{style.description}</p>
                </div>
              </div>
              <div className="ml-10 pl-1 border-l-2 border-primary/30">
                <p className="text-xs text-primary font-mono">{style.example}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <Card variant="grouped" className="p-4">
        <p className="text-sm text-foreground-muted">
          💡 <strong>Not sure?</strong> Double Progression is the most flexible and works well for most goals.
          Jerome will also auto-regulate based on your logged performance.
        </p>
      </Card>
    </div>
  );
}

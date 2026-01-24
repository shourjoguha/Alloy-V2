import { useProgramWizardStore, COMMUNICATION_STYLES } from '@/stores/program-wizard-store';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';

export function CoachStep() {
  const { 
    communicationStyle, 
    setCommunicationStyle, 
    pushIntensity, 
    setPushIntensity,
    durationWeeks,
    setDurationWeeks,
  } = useProgramWizardStore();

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-xl font-bold">Meet Jerome</h2>
        <p className="text-foreground-muted text-sm">
          Customize how Jerome communicates with you.
        </p>
      </div>

      {/* Communication style */}
      <div className="space-y-3">
        <label className="text-sm font-medium">Communication Style</label>
        <div className="grid grid-cols-2 gap-3">
          {COMMUNICATION_STYLES.map((style) => (
            <Card
              key={style.id}
              variant="interactive"
              selected={communicationStyle === style.id}
              onClick={() => setCommunicationStyle(style.id)}
              className="p-4 text-center"
            >
              <div className="text-2xl mb-2">{style.icon}</div>
              <h4 className="font-semibold text-sm">{style.name}</h4>
              <p className="text-xs text-foreground-muted mt-1">{style.description}</p>
            </Card>
          ))}
        </div>
      </div>

      {/* Push intensity slider */}
      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <label className="text-sm font-medium">Push Intensity</label>
          <span className="text-sm text-primary font-bold">
            {pushIntensity === 1 && '🌿 Conservative'}
            {pushIntensity === 2 && '🌱 Moderate'}
            {pushIntensity === 3 && '⚖️ Balanced'}
            {pushIntensity === 4 && '🔥 Aggressive'}
            {pushIntensity === 5 && '💥 All Out'}
          </span>
        </div>
        <div className="space-y-2">
          <input
            type="range"
            min="1"
            max="5"
            value={pushIntensity}
            onChange={(e) => setPushIntensity(Number(e.target.value))}
            className="w-full h-2 rounded-lg appearance-none cursor-pointer bg-background-input accent-primary"
          />
          <div className="flex justify-between text-xs text-foreground-muted">
            <span>Play it safe</span>
            <span>Push your limits</span>
          </div>
        </div>
        <p className="text-xs text-foreground-muted text-center">
          {pushIntensity <= 2 && "Jerome will prioritize recovery and gradual progress"}
          {pushIntensity === 3 && "Jerome will balance progress and sustainability"}
          {pushIntensity >= 4 && "Jerome will push you harder but watch for overtraining"}
        </p>
      </div>

      {/* Program duration */}
      <div className="space-y-3">
        <label className="text-sm font-medium">Program Duration</label>
        <div className="grid grid-cols-4 gap-2">
          {[8, 10, 12].map((weeks) => (
            <button
              key={weeks}
              onClick={() => setDurationWeeks(weeks)}
              className={cn(
                "h-12 rounded-lg font-bold transition-all",
                durationWeeks === weeks
                  ? "bg-primary text-white"
                  : "bg-background-input hover:bg-background-secondary text-foreground"
              )}
            >
              {weeks}w
            </button>
          ))}
        </div>
        <p className="text-xs text-foreground-muted text-center">
          {durationWeeks === 8 && "Short-term focus block"}
          {durationWeeks === 10 && "Extended training cycle"}
          {durationWeeks === 12 && "Standard 3-month program (recommended)"}
        </p>
      </div>

      {/* Summary card */}
      <Card variant="selected" className="p-4">
        <div className="flex items-start gap-3">
          <div className="text-3xl">🤖</div>
          <div>
            <h4 className="font-semibold">Jerome is ready!</h4>
            <p className="text-sm text-foreground-muted mt-1">
              {communicationStyle === 'drill_sergeant' && "He'll be tough but fair. No excuses accepted."}
              {communicationStyle === 'encouraging' && "He'll support and motivate you every step of the way."}
              {communicationStyle === 'scientific' && "He'll explain the why behind every decision."}
              {communicationStyle === 'casual' && "He'll keep things fun and relaxed."}
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}

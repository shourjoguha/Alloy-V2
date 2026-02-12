import { createFileRoute, Link } from "@tanstack/react-router";
import { useRef, useEffect } from "react";
import { useProgram, useProgramGenerationStatus } from "@/api/programs";
import { Spinner } from "@/components/ui";
import { ProgramHeader, MicrocycleList, ProgramStats, SessionThumbnail } from "@/components/program";

export const Route = createFileRoute("/program/$programId")({
  component: RouteComponent,
});

function RouteComponent() {
  const { programId } = Route.useParams();
  const numericId = Number(programId);
  const { data, isLoading, error, refetch } = useProgram(numericId);
  
  // Poll for generation status when program is loaded
  const { data: generationStatus } = useProgramGenerationStatus(numericId, !!data);
  
  // Refetch program data when generation completes
  const isGenerating = (generationStatus?.in_progress_microcycles ?? 0) > 0;
  const wasGeneratingRef = useRef(false);

  useEffect(() => {
    if (isGenerating) {
      wasGeneratingRef.current = true;
    } else if (wasGeneratingRef.current && !isGenerating) {
      wasGeneratingRef.current = false;
      refetch();
    }
  }, [isGenerating, refetch]);

  if (!Number.isFinite(numericId)) {
    return (
      <div className="container mx-auto p-8">
        <div className="rounded-xl bg-background-card p-6 text-center">
          <div className="text-foreground-muted">Invalid program ID</div>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="container mx-auto p-8">
        <div className="rounded-xl bg-background-card p-6 text-center">
          <Spinner size="lg" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="container mx-auto p-8">
        <div className="rounded-xl bg-background-card p-6 text-center">
          <div className="text-destructive">
            {error ? "Failed to load program" : "Program not found"}
          </div>
        </div>
      </div>
    );
  }

  const { program, microcycles } = data;
  const activeMicrocycle = microcycles?.find((mc) => mc.status === "active");

  return (
    <div className="container mx-auto p-4 space-y-6">
      <div>
        <Link to="/" className="text-primary hover:underline text-sm">
          ← Back to Dashboard
        </Link>
      </div>

      <ProgramHeader program={program} />

      {isGenerating && (
        <div className="rounded-xl bg-primary/10 border border-primary/20 p-4">
          <div className="flex items-center gap-2">
            <Spinner size="sm" />
            <span className="text-sm text-primary">
              Generating program sessions... {generationStatus?.completed_microcycles ?? 0} of {generationStatus?.total_microcycles ?? 0} microcycles completed
            </span>
          </div>
        </div>
      )}

      <ProgramStats microcycles={microcycles ?? []} />

      {activeMicrocycle && (
        <div>
          <h2 className="text-lg font-semibold text-foreground mb-3">
            Current Week: Microcycle {activeMicrocycle.sequence_number}
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {activeMicrocycle.sessions.map((session) => (
              <SessionThumbnail
                key={session.id}
                session={session}
                onClick={() => console.log("Session clicked:", session.id)}
                size="sm"
              />
            ))}
          </div>
        </div>
      )}

      <div>
        <h2 className="text-lg font-semibold text-foreground mb-3">
          All Microcycles
        </h2>
        <MicrocycleList
          microcycles={microcycles ?? []}
          onMicrocycleClick={(id: number) => console.log("Microcycle clicked:", id)}
        />
      </div>
    </div>
  );
}

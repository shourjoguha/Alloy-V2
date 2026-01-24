import { createFileRoute } from '@tanstack/react-router';
import { ProgramsTab } from '@/components/settings/ProgramsTab';

export const Route = createFileRoute('/programs')({
  component: ProgramsPage,
});

function ProgramsPage() {
  return (
    <div className="container-app py-6">
      <ProgramsTab />
    </div>
  );
}

import { createFileRoute } from '@tanstack/react-router';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { ProfileTab } from '@/components/settings/ProfileTab';
import { ProgramsTab } from '@/components/settings/ProgramsTab';
import { FavoritesTab } from '@/components/settings/FavoritesTab';

export const Route = createFileRoute('/settings')({
  component: SettingsPage,
});

function SettingsPage() {
  return (
    <div className="container-app py-6 flex flex-col min-h-0">
      <h1 className="text-2xl font-bold text-foreground mb-6">Settings</h1>

      <Tabs defaultValue="profile" className="space-y-6 flex flex-col min-h-0">
        <TabsList className="w-full justify-start border-b border-border bg-transparent p-0">
          <TabsTrigger
            value="profile"
            className="rounded-none border-b-2 border-transparent px-4 py-2 text-sm font-medium text-foreground-muted data-[state=active]:border-primary data-[state=active]:text-foreground"
          >
            Profile & Stats
          </TabsTrigger>
          <TabsTrigger
            value="programs"
            className="rounded-none border-b-2 border-transparent px-4 py-2 text-sm font-medium text-foreground-muted data-[state=active]:border-primary data-[state=active]:text-foreground"
          >
            Programs
          </TabsTrigger>
          <TabsTrigger
            value="favorites"
            className="rounded-none border-b-2 border-transparent px-4 py-2 text-sm font-medium text-foreground-muted data-[state=active]:border-primary data-[state=active]:text-foreground"
          >
            Favorites
          </TabsTrigger>
        </TabsList>

        <TabsContent value="profile" className="mt-6 flex flex-col min-h-0">
          <ProfileTab />
        </TabsContent>

        <TabsContent value="programs" className="mt-6 flex flex-col min-h-0">
          <ProgramsTab />
        </TabsContent>

        <TabsContent value="favorites" className="mt-6 flex flex-col min-h-0">
          <FavoritesTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

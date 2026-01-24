import { ReactNode } from 'react';
import { Header } from './header';
import { BottomNav } from './bottom-nav';
import { BurgerMenu } from './burger-menu';
import { ToastContainer } from '@/components/ui/toast';

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex min-h-dvh flex-col bg-background">
      <Header />
      <main className="flex-1 overflow-y-auto pb-20">
        {children}
      </main>
      <BottomNav />
      <BurgerMenu />
      <ToastContainer />
    </div>
  );
}

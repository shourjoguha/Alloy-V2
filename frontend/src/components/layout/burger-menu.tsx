import { Link } from '@tanstack/react-router';
import { X, Users, Settings, BookOpen, Activity } from 'lucide-react';
import { useUIStore } from '@/stores/ui-store';
import { cn } from '@/lib/utils';

export function BurgerMenu() {
  const { isMenuOpen, setMenuOpen } = useUIStore();

  const menuItems = [
    { to: '/log/soreness', label: 'Log Soreness', icon: Activity },
    { to: '/library', label: 'Library', icon: BookOpen },
    { to: '/friends', label: 'Friends', icon: Users },
    { to: '/settings', label: 'Settings', icon: Settings },
  ];

  return (
    <>
      {/* Backdrop */}
      {isMenuOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
          onClick={() => setMenuOpen(false)}
        />
      )}

      {/* Menu */}
      <div
        className={cn(
          'fixed right-0 top-0 z-50 h-full w-80 max-w-[85vw] bg-background-elevated shadow-xl transition-transform duration-300 ease-in-out',
          isMenuOpen ? 'translate-x-0' : 'translate-x-full'
        )}
      >
        <div className="flex h-full flex-col">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-border p-4">
            <h2 className="text-lg font-semibold text-foreground">Menu</h2>
            <button
              onClick={() => setMenuOpen(false)}
              className="flex h-10 w-10 items-center justify-center rounded-lg text-foreground-muted transition-colors hover:bg-background hover:text-foreground"
              aria-label="Close menu"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Menu Items */}
          <nav className="flex-1 overflow-y-auto p-2">
            <ul className="space-y-1">
              {menuItems.map((item) => {
                const Icon = item.icon;
                return (
                  <li key={item.to}>
                    <Link
                      to={item.to}
                      onClick={() => setMenuOpen(false)}
                      className="flex items-center gap-3 rounded-lg px-4 py-3 text-foreground-muted transition-colors hover:bg-background hover:text-foreground"
                      activeProps={{
                        className: 'bg-background text-foreground',
                      }}
                    >
                      <Icon className="h-5 w-5" />
                      <span className="font-medium">{item.label}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>

          {/* Footer */}
          <div className="border-t border-border p-4">
            <div className="text-xs text-foreground-muted">
              <p>Gainsly v1.0</p>
              <p className="mt-1">Your AI Workout Coach</p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

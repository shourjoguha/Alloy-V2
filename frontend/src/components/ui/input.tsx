import * as React from 'react';
import { cn } from '@/lib/utils';

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
  variant?: 'default' | 'auth';
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, error, variant = 'default', ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          'flex w-full border ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 disabled:cursor-not-allowed disabled:opacity-50 transition-all duration-200',
          variant === 'default' && 'h-10 rounded-md bg-background-input px-3 py-2 text-sm focus-visible:ring-primary',
          variant === 'auth' && 'h-auto rounded-xl bg-[var(--color-background-secondary)] px-4 py-3.5 text-base focus-visible:ring-[var(--color-primary)] border-[var(--color-primary)] text-[var(--color-foreground)]',
          variant === 'auth' && 'rounded-[var(--radius-xl)]',
          error ? 'border-error focus-visible:ring-error' : 'border-input',
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = 'Input';

export { Input };

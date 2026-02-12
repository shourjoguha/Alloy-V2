import { forwardRef, ButtonHTMLAttributes } from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center whitespace-nowrap rounded-lg text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        primary: 'bg-primary text-white hover:bg-primary-hover active:scale-[0.98]',
        cta: 'bg-cta text-white hover:bg-cta-hover active:scale-[0.98]',
        secondary: 'bg-background-input text-foreground hover:bg-background-secondary active:scale-[0.98]',
        outline: 'border border-primary text-primary hover:bg-primary-muted active:scale-[0.98]',
        ghost: 'text-primary hover:bg-background-secondary',
        destructive: 'bg-error text-white hover:bg-error/90 active:scale-[0.98]',
        link: 'text-primary underline-offset-4 hover:underline',
        landing: 'bg-gradient-to-r from-[var(--color-background-secondary)] to-[var(--color-primary)] text-[var(--color-foreground)] rounded-full shadow-lg shadow-[var(--color-primary)]/50 hover:shadow-xl hover:shadow-[var(--color-primary)]/70 hover:scale-105 active:scale-100 border border-[var(--color-primary)]/30',
        auth: 'bg-gradient-to-r from-[var(--color-background-secondary)] to-[var(--color-primary)] text-[var(--color-foreground)] rounded-xl shadow-md shadow-[var(--color-primary)]/40 hover:shadow-lg hover:shadow-[var(--color-primary)]/60 hover:scale-[0.98] active:scale-95 border border-[var(--color-primary)]/20',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 rounded-md px-3 text-xs',
        lg: 'h-12 rounded-xl px-6 text-base',
        icon: 'h-10 w-10',
        landing: 'h-16 px-12 py-4 text-lg',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'default',
    },
  }
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  isLoading?: boolean;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, isLoading = false, children, disabled, type, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';

    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={disabled || isLoading}
        {...props}
        type={type || 'button'}
      >
        {isLoading ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            {children}
          </>
        ) : (
          children
        )}
      </Comp>
    );
  }
);
Button.displayName = 'Button';

export { Button };

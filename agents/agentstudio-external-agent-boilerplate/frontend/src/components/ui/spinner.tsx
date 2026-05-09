import { cn } from '@/lib/utils';

export type SpinnerProps = {
  className?: string;
};

export function Spinner({ className }: SpinnerProps): React.JSX.Element {
  return (
    <span
      aria-hidden="true"
      className={cn(
        'inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent',
        className
      )}
    />
  );
}

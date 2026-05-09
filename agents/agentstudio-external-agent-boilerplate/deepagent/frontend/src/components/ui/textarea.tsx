import * as React from 'react';

import { cn } from '@/lib/utils';

function Textarea({ className, ...props }: React.ComponentProps<'textarea'>): React.JSX.Element {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        'border-input focus-visible:border-ring focus-visible:ring-ring/50 rounded-lg border bg-transparent px-2.5 py-2 text-sm transition-colors focus-visible:ring-3 placeholder:text-muted-foreground flex w-full outline-none disabled:cursor-not-allowed disabled:opacity-50 resize-y min-h-[80px]',
        className
      )}
      {...props}
    />
  );
}

export { Textarea };

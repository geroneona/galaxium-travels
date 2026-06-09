import { cn } from '@/lib/utils';

export type ChatContainerRootProps = {
  children: React.ReactNode;
  className?: string;
} & React.HTMLAttributes<HTMLDivElement>;

export type ChatContainerContentProps = {
  children: React.ReactNode;
  className?: string;
} & React.HTMLAttributes<HTMLDivElement>;

export type ChatContainerScrollAnchorProps = {
  className?: string;
  ref?: React.RefObject<HTMLDivElement>;
} & React.HTMLAttributes<HTMLDivElement>;

function ChatContainerRoot({ children, className, ...props }: ChatContainerRootProps): React.JSX.Element {
  return (
    <div className={cn('flex flex-col overflow-y-auto', className)} role="log" {...props}>
      {children}
    </div>
  );
}

function ChatContainerContent({
  children,
  className,
  ...props
}: ChatContainerContentProps): React.JSX.Element {
  return (
    <div className={cn('flex-1 flex w-full flex-col overflow-y-auto', className)} {...props}>
      {children}
    </div>
  );
}

function ChatContainerScrollAnchor({
  className,
  ...props
}: ChatContainerScrollAnchorProps): React.JSX.Element {
  return (
    <div
      className={cn('h-px w-full shrink-0 scroll-mt-4', className)}
      aria-hidden="true"
      {...props}
    />
  );
}

export { ChatContainerRoot, ChatContainerContent, ChatContainerScrollAnchor };

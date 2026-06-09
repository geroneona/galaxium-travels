'use client';

import { ChatContainerContent, ChatContainerRoot } from '@/components/ui/chat-container';
import { Markdown } from '@/components/ui/markdown';
import { Message, MessageAvatar, MessageContent } from '@/components/ui/message';
import { Button } from '@/components/ui/button';
import { PromptInput, PromptInputTextarea, PromptInputActions } from '@/components/ui/prompt-input';
import { Spinner } from '@/components/ui/spinner';
import { useRef, useState } from 'react';
import { Send } from 'lucide-react';
import { sendA2AMessage } from '@/lib/a2a-client';

type A2AChatProps = {
  agentCard: Record<string, unknown> | null;
  suggestions?: string[];
  agentStatus?: 'loading' | 'ready' | 'error';
  authRequired?: boolean;
  isAuthenticated?: boolean;
};

function getErrorMessage(error: unknown): string {
  if (error instanceof Error && typeof error.message === 'string' && error.message.length > 0) {
    return error.message;
  }
  if (typeof error === 'string' && error.length > 0) {
    return error;
  }
  if (error != null && typeof error === 'object') {
    const maybeMessage = (error as { message?: unknown }).message;
    if (typeof maybeMessage === 'string' && maybeMessage.length > 0) {
      return maybeMessage;
    }
  }
  try {
    return String(error);
  } catch {
    return 'unknown error';
  }
}

function createContextId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `ctx-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function A2AChat({
  agentCard,
  suggestions = [],
  agentStatus = 'ready',
  authRequired = false,
  isAuthenticated = true,
}: A2AChatProps): React.JSX.Element {
  const [messages, setMessages] = useState<Array<{ id: number; role: string; content: string }>>(
    []
  );
  const contextIdRef = useRef<string>(createContextId());
  const [isStreaming, setIsStreaming] = useState(false);
  const [promptValue, setPromptValue] = useState('');
  const isConnecting = agentStatus === 'loading';
  const hasAuth = !authRequired || isAuthenticated;
  const isAvailable = agentStatus === 'ready' && Boolean(agentCard) && hasAuth;
  const isBusy = isStreaming || isConnecting;
  const transportLabel = isAvailable
    ? (agentCard?.preferredTransport as string) ?? 'auto'
    : isConnecting
    ? 'connecting'
    : 'unavailable';
  const statusLabel = isConnecting
    ? 'connecting'
    : !hasAuth
    ? 'auth-required'
    : !isAvailable
    ? 'unavailable'
    : isStreaming
    ? 'streaming'
    : 'ready';

  async function sendPromptAndReply(text: string): Promise<void> {
    const newId = messages.length + 1;
    setMessages((prev) => [...prev, { id: newId, role: 'user', content: text }]);
    setPromptValue('');
    setIsStreaming(true);
    try {
      const res = await sendA2AMessage(text, undefined, {
        preferredTransport: agentCard?.preferredTransport as string,
        contextId: contextIdRef.current,
      });
      const reply = res?.text ?? '';
      const replyId = messages.length + 2;
      if (reply && reply.trim().length > 0) {
        setMessages((prev) => [...prev, { id: replyId, role: 'assistant', content: reply }]);
      } else {
        let details = 'unknown error';
        try {
          if (res != null && 'raw' in res && res.raw != null) {
            const raw = res.raw as unknown;
            if (raw instanceof Error) {
              details = raw.message;
            } else {
              const rawObj = raw as Record<string, unknown>;
              if (typeof rawObj.status === 'number' && typeof rawObj.statusText === 'string') {
                details = `${rawObj.status} ${rawObj.statusText}`;
              } else if (typeof raw === 'string') {
                details = raw;
              } else {
                details = JSON.stringify(raw).slice(0, 200);
              }
            }
          }
        } catch (e) {
          details = String(e);
        }
        setMessages((prev) => [
          ...prev,
          { id: replyId, role: 'assistant', content: `Error: ${details}` },
        ]);
      }
    } catch (e) {
      const errId = messages.length + 2;
      const msg = getErrorMessage(e);
      setMessages((prev) => [
        ...prev,
        { id: errId, role: 'assistant', content: `Error: ${msg}` },
      ]);
    } finally {
      setIsStreaming(false);
    }
  }

  function handleSubmit(): void {
    if (promptValue.trim().length === 0 || !isAvailable || isBusy) {
      return;
    }
    void sendPromptAndReply(promptValue);
  }

  return (
    <div className="flex h-full min-h-0 w-full flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
      <header className="flex flex-wrap items-start justify-between gap-6 border-b border-slate-200 bg-white px-6 py-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
            Conversation
          </div>
          <div className="mt-2 text-lg font-semibold text-slate-900">Live chat</div>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-600">
            <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 font-medium">
              Transport: {transportLabel}
            </span>
            <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 font-medium">
              Status: {statusLabel}
            </span>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-700">
          <div className="min-w-[120px]">
            <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
              Session
            </div>
            <div className="mt-1 font-medium">
              {isAvailable ? (isStreaming ? 'Live stream' : 'Idle') : 'Offline'}
            </div>
          </div>
          <div className="min-w-[120px]">
            <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
              Messages
            </div>
            <div className="mt-1 font-medium">{messages.length}</div>
          </div>
        </div>
      </header>

      <ChatContainerRoot
        className="flex-1 min-h-0 overflow-hidden"
        aria-busy={isBusy}
        aria-live="polite"
      >
        <ChatContainerContent className="h-full min-h-0 space-y-4 overflow-y-auto px-6 py-6">
          {messages.length === 0 && (
            <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-8 text-center animate-fade-up">
              {isConnecting && (
                <div className="mx-auto flex w-fit items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-600">
                  <Spinner className="h-3 w-3 text-slate-500" />
                  Connecting to agent...
                </div>
              )}
              <div className="mt-3 text-lg font-semibold text-slate-900">
                {isConnecting ? 'Preparing the chat' : 'Start a conversation'}
              </div>
              <p className="mt-2 text-sm text-slate-500">
                {isConnecting
                  ? 'Fetching the agent card and verifying connectivity.'
                  : 'Ask about available skills, test routing, or validate your A2A deployment.'}
              </p>
              {suggestions.length > 0 && (
                <div className="mt-4 flex flex-wrap justify-center gap-2 text-xs">
                  {suggestions.slice(0, 4).map((suggestion) => (
                    <button
                      key={suggestion}
                      className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-slate-600 transition hover:border-slate-300 hover:text-slate-900 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-300 disabled:opacity-60"
                      onClick={() => setPromptValue(suggestion)}
                      disabled={!isAvailable || isBusy}
                      type="button"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {messages.map((message) => {
            const isAssistant = message.role === 'assistant';

            return (
              <Message
                key={message.id}
                className={
                  message.role === 'user'
                    ? 'justify-end animate-fade-up'
                    : 'justify-start animate-fade-up'
                }
                style={{ animationDelay: `${message.id * 70}ms` }}
              >
                {isAssistant && (
                  <MessageAvatar src="/avatars/agent.svg" alt="AI Assistant" fallback="AI" />
                )}
                <div className="max-w-[85%] flex-1 sm:max-w-[75%]">
                  {isAssistant ? (
                    <div data-testid="answer-bubble" className="prose rounded-2xl border border-slate-100 bg-slate-50 p-4 text-slate-700 shadow-sm">
                      <Markdown>{message.content}</Markdown>
                    </div>
                  ) : (
                    <MessageContent className="rounded-full bg-slate-900 px-4 py-2 text-white shadow-sm">
                      {message.content}
                    </MessageContent>
                  )}
                </div>
              </Message>
            );
          })}
          {isStreaming && (
            <Message className="justify-start animate-fade-up" style={{ animationDelay: '80ms' }}>
              <MessageAvatar src="/avatars/agent.svg" alt="AI Assistant" fallback="AI" />
              <div className="max-w-[85%] flex-1 sm:max-w-[75%]">
                <div className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3 text-slate-600 shadow-sm">
                  <div className="flex items-center gap-2 text-sm">
                    <Spinner className="h-4 w-4 text-slate-500" />
                    Assistant is responding...
                  </div>
                </div>
              </div>
            </Message>
          )}
        </ChatContainerContent>
      </ChatContainerRoot>

      <div className="border-t border-slate-200 bg-white px-6 py-4">
        <PromptInput
          value={promptValue}
          onValueChange={setPromptValue}
          onSubmit={handleSubmit}
          isLoading={isStreaming}
          disabled={!isAvailable || isConnecting}
          className="rounded-full border border-slate-200 bg-white px-4 py-3 shadow-sm"
        >
          <PromptInputTextarea
            placeholder={
              isConnecting
                ? 'Connecting to agent...'
                : !hasAuth
                ? 'Authenticate first to start chatting...'
                : isAvailable
                ? 'Send a message to your agent...'
                : 'Agent unavailable. Check backend.'
            }
            disabled={!isAvailable || isConnecting}
            className="text-sm text-slate-900 placeholder:text-slate-400"
          />
          <PromptInputActions>
            {isStreaming && (
              <div className="hidden items-center gap-2 text-xs text-slate-500 sm:flex">
                <Spinner className="h-3 w-3 text-slate-500" />
                Sending...
              </div>
            )}
            <Button
              size="icon"
              aria-label="Send message"
              onClick={handleSubmit}
              title="Send message"
              className="rounded-full bg-slate-900 text-white shadow-sm hover:bg-slate-800"
              disabled={!isAvailable || isBusy}
            >
              <Send className="h-4 w-4" />
            </Button>
          </PromptInputActions>
        </PromptInput>
        <div className="mt-2 text-xs text-slate-400">
          Press Enter to send, Shift+Enter for a new line.
        </div>
      </div>
    </div>
  );
}

export default A2AChat;

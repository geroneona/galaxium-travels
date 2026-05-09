import { useCallback, useEffect, useRef, useState } from 'react';

import A2AChat from '@/components/a2a-chat';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import { clearAgentCardCache, loadAgentCard } from '@/lib/agent-card';
import {
  initKeycloakAuth,
  isKeycloakConfigured,
  loginWithKeycloak,
  logoutFromKeycloak,
} from '@/lib/keycloak';

type AgentStatus = 'loading' | 'ready' | 'error';

export function App(): React.JSX.Element {
  const _envUrl = (import.meta as unknown as { env?: Record<string, string> }).env
    ?.VITE_BACKEND_URL;
  const backendUrl = _envUrl ?? '';
  const keycloakEnabled = isKeycloakConfigured();
  const [agentCard, setAgentCard] = useState<Record<string, unknown> | null>(null);
  const [agentStatus, setAgentStatus] = useState<AgentStatus>('loading');
  const [agentError, setAgentError] = useState<string | null>(null);
  const [lastUpdated] = useState<Date | null>(null);
  // If Keycloak is not enabled, user is authenticated by default (no auth required)
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(!keycloakEnabled);
  const [isKeycloakAuthenticated, setIsKeycloakAuthenticated] = useState(false);
  const [isAuthLoading, setIsAuthLoading] = useState(false);
  const statusMeta = {
    loading: { label: 'Loading', dot: 'bg-orange-400' },
    ready: { label: 'Ready', dot: 'bg-emerald-500' },
    error: { label: 'Down', dot: 'bg-rose-500' },
  }[agentStatus];
  const mountedRef = useRef(true);
  const securitySchemes =
    agentCard != null &&
    agentCard.securitySchemes != null &&
    typeof agentCard.securitySchemes === 'object'
      ? (agentCard.securitySchemes as Record<string, unknown>)
      : {};
  const skills = Array.isArray(agentCard?.skills) ? (agentCard!.skills as unknown[]) : [];

  const requiresBearerAuth = Object.values(securitySchemes).some((scheme: unknown) => {
    if (scheme == null || typeof scheme !== 'object') {
      return false;
    }
    const s = scheme as Record<string, unknown>;
    return (
      (s.type === 'http' || s.type === 'HTTP') &&
      typeof s.scheme === 'string' &&
      (s.scheme.toLowerCase() === 'bearer' || s.scheme === 'Bearer')
    );
  });
  const showAuthOverlay = keycloakEnabled && !isAuthenticated;
  const capabilityExamples = skills
    .flatMap((skill: unknown): string[] => {
      if (skill == null) {
        return [] as string[];
      }
      const s = skill as Record<string, unknown>;
      const examples = s.examples ?? s.example ?? [];
      if (Array.isArray(examples)) {
        return examples as string[];
      }
      if (typeof examples === 'string') {
        return [examples];
      }
      return [] as string[];
    })
    .map((example): string => {
      if (typeof example === 'string') {
        return example.trim();
      }
      return '';
    })
    .filter((x) => x.length > 0);
  const avatarSrc = agentCard?.icon !== undefined ? agentCard.icon : '/avatars/agent.svg';
  const agentSummary =
    agentStatus === 'loading'
      ? 'Fetching agent card details.'
      : agentStatus === 'error'
      ? 'Agent is currently unavailable.'
      : agentCard?.description ?? 'Connected to an A2A-compatible agent card.';
  const lastUpdatedLabel = lastUpdated ? lastUpdated.toLocaleString() : '—';

  const fetchAgentCard = useCallback(
    async (clearCache = false): Promise<void> => {
      try {
        if (clearCache) {
          clearAgentCardCache(backendUrl);
        }
        setAgentStatus('loading');
        setAgentError(null);
        const card = await loadAgentCard(backendUrl);
        if (!mountedRef.current) {
          return;
        }
        if (card != null) {
          setAgentCard(card as Record<string, unknown>);
          setAgentStatus('ready');
        } else {
          setAgentCard(null);
          setAgentStatus('error');
          setAgentError(`Unable to load agent card from ${backendUrl}`);
        }
      } catch (err) {
        if (!mountedRef.current) {
          return;
        }
        setAgentCard(null);
        setAgentStatus('error');
        setAgentError(String(err ?? 'Unknown error'));
      }
    },
    [backendUrl]
  );

  useEffect((): (() => void) => {
    mountedRef.current = true;
    const run = async (): Promise<void> => {
      await fetchAgentCard();
    };
    void run();

    return () => {
      mountedRef.current = false;
    };
  }, [fetchAgentCard]);

  useEffect((): (() => void) | void => {
    if (!keycloakEnabled) {
      return;
    }

    let active = true;
    void initKeycloakAuth()
      .then((authenticated) => {
        if (!active) {
          return;
        }
        setIsKeycloakAuthenticated(authenticated);
        setIsAuthenticated(authenticated);
      })
      .finally(() => {
        if (active) {
          setIsAuthLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [keycloakEnabled]);

  async function handleKeycloakLogin(): Promise<void> {
    setIsAuthLoading(true);
    await loginWithKeycloak();
  }

  async function handleKeycloakLogout(): Promise<void> {
    setIsAuthLoading(true);
    await logoutFromKeycloak();
  }

  const authenticationPanel = keycloakEnabled ? (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
        Authentication
      </div>
      <div className="mt-3 text-sm text-slate-600">
        Authenticate with Keycloak to access the console.
      </div>
      <div className="mt-4 flex items-center gap-3">
        <Button type="button" size="sm" onClick={handleKeycloakLogin} disabled={isAuthLoading}>
          Authenticate with Keycloak
        </Button>
        {isAuthLoading && (
          <div className="flex items-center text-xs text-slate-500">
            <Spinner className="mr-1 h-3 w-3 text-slate-500" />
            Redirecting...
          </div>
        )}
      </div>
    </div>
  ) : null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100 text-slate-900">
      <div className="mx-auto flex min-h-screen max-w-6xl flex-col gap-6 px-4 py-8 sm:px-6 lg:px-8">
        {!showAuthOverlay && (
          <header className="flex flex-wrap items-center justify-between gap-4 animate-fade-up">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                Agentic Chat UI
              </div>
              <h1 className="mt-2 text-3xl font-semibold text-slate-900 sm:text-4xl">
                A2A Frontend Console
              </h1>
              <p className="mt-2 max-w-2xl text-sm text-slate-500">
                A chat surface for your A2A-compatible agents with live agent card discovery and
                streaming-ready messaging.
              </p>
            </div>
          </header>
        )}

        {showAuthOverlay ? (
          <main className="flex flex-1 items-center justify-center animate-fade-up [animation-delay:120ms]">
            <section className="w-full max-w-md">{authenticationPanel}</section>
          </main>
        ) : (
          <main className="grid flex-1 min-h-0 gap-6 lg:grid-cols-12 animate-fade-up [animation-delay:120ms]">
            <section className="min-h-0 lg:col-span-8 xl:col-span-9">
              <A2AChat
                agentCard={agentCard}
                suggestions={capabilityExamples}
                agentStatus={agentStatus}
                authRequired={requiresBearerAuth}
                isAuthenticated={isAuthenticated}
              />
            </section>
            <aside className="lg:col-span-4 xl:col-span-3">
              <div className="flex h-full flex-col gap-4">
                {isKeycloakAuthenticated && (
                  <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                    <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                      Authentication
                    </div>
                    <div className="mt-3 text-sm text-slate-600">Signed in with Keycloak.</div>
                    <div className="mt-4">
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={handleKeycloakLogout}
                        disabled={isAuthLoading}
                      >
                        Logout
                      </Button>
                    </div>
                  </div>
                )}

                <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                    Agent Card
                  </div>
                  {agentStatus === 'ready' && agentCard && (
                    <div className="mt-4 flex items-start gap-3">
                      <div className="relative">
                        <img
                          src={avatarSrc as string}
                          alt={(agentCard?.name as string) ?? 'Agent'}
                          className="h-12 w-12 rounded-2xl border border-white/80 object-cover shadow-sm"
                        />
                        <span
                          className={`absolute -bottom-1 -right-1 h-3.5 w-3.5 rounded-full border-2 border-white ${statusMeta.dot}`}
                          role="status"
                          aria-label={`Agent status: ${statusMeta.label}`}
                          title={`Agent status: ${statusMeta.label}`}
                        />
                      </div>
                      <div>
                        <div className="flex flex-wrap items-center gap-2 text-base font-semibold text-slate-900">
                          <span>{(agentCard?.name as string) ?? 'Agent'}</span>
                          <span className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                            <span
                              className={`h-1.5 w-1.5 rounded-full ${statusMeta.dot}`}
                              aria-hidden="true"
                            />
                            {statusMeta.label}
                          </span>
                        </div>
                        <div className="mt-1 text-xs text-slate-600">{agentSummary as string}</div>
                        <div className="mt-1 text-[11px] uppercase tracking-[0.14em] text-slate-400">
                          Updated {lastUpdatedLabel}
                        </div>
                      </div>
                    </div>
                  )}
                  {agentStatus === 'loading' && (
                    <div className="mt-4 space-y-4">
                      <div className="flex items-center gap-2 text-xs font-medium text-slate-600">
                        <Spinner className="h-3 w-3 text-slate-500" />
                        Loading agent card...
                      </div>
                      <div className="space-y-3 animate-pulse">
                        <div className="space-y-2">
                          <div className="h-3 w-32 rounded-full bg-slate-100" />
                          <div className="h-3 w-44 rounded-full bg-slate-100" />
                        </div>
                        <div className="space-y-2">
                          <div className="h-10 w-full rounded-lg bg-slate-100" />
                          <div className="h-10 w-full rounded-lg bg-slate-100" />
                          <div className="h-10 w-full rounded-lg bg-slate-100" />
                        </div>
                      </div>
                    </div>
                  )}

                  {agentStatus === 'error' && (
                    <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-3 py-3 text-sm text-amber-900">
                      <div className="font-medium">Agent is not available.</div>
                      <div className="mt-1 text-xs text-amber-900/80">
                        {agentError ?? 'Check the backend URL and server status.'}
                      </div>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        className="mt-3"
                        onClick={() => fetchAgentCard(true)}
                      >
                        Retry
                      </Button>
                    </div>
                  )}
                </div>

                {agentStatus === 'ready' && agentCard && (
                  <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                    <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                      Session
                    </div>
                    <div className="mt-3 space-y-2 text-sm text-slate-800">
                      <div className="flex items-center justify-between">
                        <span>Backend</span>
                        <span className="font-medium text-slate-900">{backendUrl}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Transport</span>
                        <span className="font-medium text-slate-900">A2A</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Mode</span>
                        <span className="font-medium text-slate-900">Local</span>
                      </div>
                    </div>
                    <div className="mt-4 rounded-xl bg-slate-50 px-3 py-2 text-xs text-slate-600">
                      Tip: update <span className="font-semibold">VITE_BACKEND_URL</span> to target
                      a deployed agent.
                    </div>
                  </div>
                )}
              </div>
            </aside>
          </main>
        )}

        {!showAuthOverlay && (
          <footer className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400 animate-fade-up [animation-delay:200ms]">
            <span>Built with Tailwind and A2A protocol UI components.</span>
          </footer>
        )}
      </div>
    </div>
  );
}

export default App;

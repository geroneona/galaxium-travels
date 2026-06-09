import { useCallback, useEffect, useRef, useState } from 'react';
import { ChevronDown, ChevronRight, Plus, Trash2, Send, LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Spinner } from '@/components/ui/spinner';
import { streamA2AMessage } from '@/lib/a2a-client';
import {
  initKeycloakAuth,
  isKeycloakConfigured,
  loginWithKeycloak,
  logoutFromKeycloak,
} from '@/lib/keycloak';
import { cn } from '@/lib/utils';
import { loadAgentCard } from './lib/agent-card';


// ── Types ──────────────────────────────────────────────────────────────────────

type CV = {
  id: string;
  name: string;
  content: string;
  expanded: boolean;
};

type JobDescription = {
  id: string;
  title: string;
  description: string;
  expanded: boolean;
};

type QAEntry = {
  id: string;
  question: string;
  answer: string;
  loading: boolean;
  reasoning: string[];
};

// ── Helpers ────────────────────────────────────────────────────────────────────

function uid(): string {
  return Math.random().toString(36).slice(2, 10);
}

function buildContextMessage(question: string, cvs: CV[], jobs: JobDescription[]): string {
  const cvSection =
    cvs.length > 0
      ? cvs
          .map((cv) => `### CV: ${cv.name || '(unnamed)'}\n${cv.content || '(no content)'}`)
          .join('\n\n')
      : '(none)';

  const jobSection =
    jobs.length > 0
      ? jobs
          .map(
            (j) =>
              `### Job Description: ${j.title || '(no title)'}\n${j.description || '(no description)'}`
          )
          .join('\n\n')
      : '(none)';

  return `${question}\n\n---\n\n## CVs\n\n${cvSection}\n\n## Job Descriptions\n\n${jobSection}`;
}

// ── Sub-components ─────────────────────────────────────────────────────────────

type CVItemProps = {
  cv: CV;
  onChange: (updated: CV) => void;
  onDelete: (id: string) => void;
};

function CVItem({ cv, onChange, onDelete }: CVItemProps): React.JSX.Element {
  return (
    <div className="border border-border rounded-lg overflow-hidden bg-card">
      <div className="flex items-center gap-2 px-3 py-2">
        <button
          type="button"
          className="text-muted-foreground hover:text-foreground flex-shrink-0 focus:outline-none"
          onClick={() => onChange({ ...cv, expanded: !cv.expanded })}
          aria-label={cv.expanded ? 'Collapse CV' : 'Expand CV'}
        >
          {cv.expanded ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
        </button>
        <Input
          value={cv.name}
          onChange={(e) => onChange({ ...cv, name: e.target.value })}
          placeholder="Person's name"
          className="flex-1 h-7 text-sm"
        />
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => onDelete(cv.id)}
          aria-label="Delete CV"
          className="flex-shrink-0 text-muted-foreground hover:text-destructive"
        >
          <Trash2 className="size-4" />
        </Button>
      </div>
      {cv.expanded && (
        <div className="px-3 pb-3">
          <Textarea
            value={cv.content}
            onChange={(e) => onChange({ ...cv, content: e.target.value })}
            placeholder="Paste CV content here…"
            className="min-h-[120px] text-sm"
          />
        </div>
      )}
    </div>
  );
}

type JobItemProps = {
  job: JobDescription;
  onChange: (updated: JobDescription) => void;
  onDelete: (id: string) => void;
};

function JobItem({ job, onChange, onDelete }: JobItemProps): React.JSX.Element {
  return (
    <div className="border border-border rounded-lg overflow-hidden bg-card">
      <div className="flex items-center gap-2 px-3 py-2">
        <button
          type="button"
          className="text-muted-foreground hover:text-foreground flex-shrink-0 focus:outline-none"
          onClick={() => onChange({ ...job, expanded: !job.expanded })}
          aria-label={job.expanded ? 'Collapse job description' : 'Expand job description'}
        >
          {job.expanded ? (
            <ChevronDown className="size-4" />
          ) : (
            <ChevronRight className="size-4" />
          )}
        </button>
        <Input
          value={job.title}
          onChange={(e) => onChange({ ...job, title: e.target.value })}
          placeholder="Position title"
          className="flex-1 h-7 text-sm"
        />
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => onDelete(job.id)}
          aria-label="Delete job description"
          className="flex-shrink-0 text-muted-foreground hover:text-destructive"
        >
          <Trash2 className="size-4" />
        </Button>
      </div>
      {job.expanded && (
        <div className="px-3 pb-3">
          <Textarea
            value={job.description}
            onChange={(e) => onChange({ ...job, description: e.target.value })}
            placeholder="Paste job description here…"
            className="min-h-[120px] text-sm"
          />
        </div>
      )}
    </div>
  );
}

type QAEntryCardProps = {
  entry: QAEntry;
};

function QAEntryCard({ entry }: QAEntryCardProps): React.JSX.Element {
  const [reasoningOpen, setReasoningOpen] = useState(false);

  useEffect(() => {
    // Auto-expand reasoning panel when streaming starts
    if (entry.loading && entry.reasoning.length > 0) {
      setReasoningOpen(true);
    }
    // Auto-collapse when the agent finishes
    if (!entry.loading) {
      setReasoningOpen(false);
    }
  }, [entry.loading, entry.reasoning.length]);

  return (
    <div className="space-y-2">
      {/* Question bubble */}
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-primary text-primary-foreground px-4 py-2.5 text-sm whitespace-pre-wrap">
          {entry.question}
        </div>
      </div>

      {/* Reasoning steps */}
      {entry.reasoning.length > 0 && (
        <div className="flex justify-start">
          <div className="max-w-[90%] w-full">
            <button
              type="button"
              onClick={() => setReasoningOpen((o) => !o)}
              className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground mb-1 focus:outline-none"
            >
              {reasoningOpen ? (
                <ChevronDown className="size-3" />
              ) : (
                <ChevronRight className="size-3" />
              )}
              Reasoning ({entry.reasoning.length} step
              {entry.reasoning.length === 1 ? '' : 's'})
              {entry.loading && <Spinner className="size-3 ml-1" />}
            </button>
            {reasoningOpen && (
              <div className="space-y-1.5 border-l-2 border-border pl-3 max-h-72 overflow-y-auto">
                {entry.reasoning.map((step, i) => (
                  <div
                    key={`step-${i}`}
                    className="text-xs text-muted-foreground whitespace-pre-wrap bg-muted/50 rounded p-2"
                  >
                    {step}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Answer bubble */}
      <div className="flex justify-start">
        <div
          data-testid="answer-bubble"
          data-loading={entry.loading}
          className={cn(
            'max-w-[80%] rounded-2xl rounded-tl-sm bg-muted px-4 py-2.5 text-sm whitespace-pre-wrap',
            entry.loading && 'text-muted-foreground'
          )}
        >
          {entry.loading ? (
            <span className="flex items-center gap-2">
              <Spinner className="size-3" />
              {entry.reasoning.length > 0 ? 'Finalizing…' : 'Thinking…'}
            </span>
          ) : (
            entry.answer
          )}
        </div>
      </div>
    </div>
  );
}

// ── Login overlay ──────────────────────────────────────────────────────────────

function LoginOverlay(): React.JSX.Element {
  const [loading, setLoading] = useState(false);

  async function handleLogin(): Promise<void> {
    setLoading(true);
    await loginWithKeycloak();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
      <div className="flex flex-col items-center gap-4 p-8 rounded-2xl border border-border bg-card shadow-lg max-w-sm w-full text-center">
        <div className="text-2xl font-semibold">Recruitment Assistant</div>
        <p className="text-muted-foreground text-sm">Please sign in to continue.</p>
        <Button onClick={() => { void handleLogin(); }} disabled={loading} className="w-full">
          {loading ? <Spinner className="mr-2" /> : null}
          Sign in
        </Button>
      </div>
    </div>
  );
}

// ── Main App ───────────────────────────────────────────────────────────────────

const metaEnv = (import.meta as unknown as { env?: Record<string, string> }).env;
const DEFAULT_BACKEND = metaEnv?.VITE_BACKEND_URL ?? '';
const cardPromise = loadAgentCard(DEFAULT_BACKEND);

export function App(): React.JSX.Element {
  const keycloakEnabled = isKeycloakConfigured();
  const [isAuthenticated, setIsAuthenticated] = useState(!keycloakEnabled);
  const [cvs, setCvs] = useState<CV[]>([]);
  const [jobs, setJobs] = useState<JobDescription[]>([]);
  const [qaHistory, setQaHistory] = useState<QAEntry[]>([]);
  const [question, setQuestion] = useState('');
  const [isSending, setIsSending] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  

  // Keycloak init
  useEffect(() => {
    if (!keycloakEnabled) {
      return;
    }
    void initKeycloakAuth().then((authenticated) => {
      setIsAuthenticated(authenticated);
    });
  }, [keycloakEnabled]);

  // CV handlers
  const addCV = useCallback((): void => {
    setCvs((prev) => [...prev, { id: uid(), name: '', content: '', expanded: false }]);
  }, []);

  const updateCV = useCallback((updated: CV): void => {
    setCvs((prev) => prev.map((cv) => (cv.id === updated.id ? updated : cv)));
  }, []);

  const deleteCV = useCallback((id: string): void => {
    setCvs((prev) => prev.filter((cv) => cv.id !== id));
  }, []);

  // Job handlers
  const addJob = useCallback((): void => {
    setJobs((prev) => [
      ...prev,
      { id: uid(), title: '', description: '', expanded: false },
    ]);
  }, []);

  const updateJob = useCallback((updated: JobDescription): void => {
    setJobs((prev) => prev.map((j) => (j.id === updated.id ? updated : j)));
  }, []);

  const deleteJob = useCallback((id: string): void => {
    setJobs((prev) => prev.filter((j) => j.id !== id));
  }, []);

  // Ask question
  const handleSubmit = useCallback(async (): Promise<void> => {
    const trimmed = question.trim();
    if (!trimmed || isSending) {
      return;
    }

    const entryId = uid();
    const newEntry: QAEntry = {
      id: entryId,
      question: trimmed,
      answer: '',
      loading: true,
      reasoning: [],
    };

    setQaHistory((prev) => [...prev, newEntry]);
    setQuestion('');
    setIsSending(true);

    try {
      const contextMessage = buildContextMessage(trimmed, cvs, jobs);
      const result = await streamA2AMessage(
        contextMessage,
        DEFAULT_BACKEND || location.origin,
        await cardPromise,
        (step: string) => {
          setQaHistory((prev) =>
            prev.map((e) =>
              e.id === entryId ? { ...e, reasoning: [...e.reasoning, step] } : e
            )
          );
        },
      );
      const answer =
        result.text.trim().length > 0 ? result.text.trim() : '(No response from the agent)';

      setQaHistory((prev) =>
        prev.map((e) => (e.id === entryId ? { ...e, answer, loading: false } : e))
      );
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : String(err);
      setQaHistory((prev) =>
        prev.map((e) =>
          e.id === entryId ? { ...e, answer: `Error: ${errMsg}`, loading: false } : e
        )
      );
    } finally {
      setIsSending(false);
    }
  }, [question, isSending, cvs, jobs]);

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>): void {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void handleSubmit();
    }
  }

  // Keycloak not authenticated – show login overlay
  if (keycloakEnabled && !isAuthenticated) {
    return <LoginOverlay />;
  }

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card px-6 py-3 flex items-center justify-between">
        <h1 className="text-base font-semibold">Recruitment Assistant</h1>
        {keycloakEnabled && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => { void logoutFromKeycloak(); }}
            className="gap-1.5 text-muted-foreground"
          >
            <LogOut className="size-4" />
            Sign out
          </Button>
        )}
      </header>

      {/* Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left panel – CVs and Job Descriptions */}
        <aside className="w-80 xl:w-96 flex-shrink-0 border-r border-border flex flex-col overflow-y-auto">
          {/* CVs section */}
          <section className="p-4 border-b border-border">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold">CVs</h2>
              <Button variant="outline" size="sm" onClick={addCV} className="gap-1">
                <Plus className="size-3.5" />
                Add CV
              </Button>
            </div>
            <div className="space-y-2">
              {cvs.length === 0 && (
                <p className="text-xs text-muted-foreground py-1">No CVs added yet.</p>
              )}
              {cvs.map((cv) => (
                <CVItem key={cv.id} cv={cv} onChange={updateCV} onDelete={deleteCV} />
              ))}
            </div>
          </section>

          {/* Job Descriptions section */}
          <section className="p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold">Job Descriptions</h2>
              <Button variant="outline" size="sm" onClick={addJob} className="gap-1">
                <Plus className="size-3.5" />
                Add Job
              </Button>
            </div>
            <div className="space-y-2">
              {jobs.length === 0 && (
                <p className="text-xs text-muted-foreground py-1">No job descriptions added yet.</p>
              )}
              {jobs.map((job) => (
                <JobItem key={job.id} job={job} onChange={updateJob} onDelete={deleteJob} />
              ))}
            </div>
          </section>
        </aside>

        {/* Right panel – Q&A */}
        <main className="flex-1 flex flex-col min-h-0">
          {/* History */}
          <div className="flex-1 overflow-y-auto px-6 py-4 flex flex-col">
            {qaHistory.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center text-muted-foreground gap-2">
                <p className="text-sm">Add CVs and job descriptions on the left, then ask a question about them.</p>
                <p className="text-xs">e.g. "Which candidate is the best fit for the Software Engineer role?"</p>
              </div>
            ) : (
              <div className="flex-1 flex flex-col justify-end">
                <div className="space-y-6 max-w-2xl mx-auto w-full">
                  {qaHistory.map((entry) => (
                    <QAEntryCard key={entry.id} entry={entry} />
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Question input */}
          <div className="border-t border-border px-6 py-4 bg-card">
            <div className="max-w-2xl mx-auto flex gap-2 items-end">
              <Textarea
                ref={textareaRef}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question about the CVs and job descriptions… (Enter to send, Shift+Enter for new line)"
                className="flex-1 min-h-[60px] max-h-[160px] resize-none text-sm"
                disabled={isSending}
              />
              <Button
                onClick={() => { void handleSubmit(); }}
                disabled={isSending || question.trim().length === 0}
                size="icon"
                className="flex-shrink-0 mb-0.5"
                aria-label="Send"
              >
                {isSending ? <Spinner className="size-4" /> : <Send className="size-4" />}
              </Button>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;

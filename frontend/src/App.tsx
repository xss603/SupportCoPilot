import React, { useEffect, useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Sidebar, NavTab } from './components/Sidebar';
import { Header } from './components/Header';
import { CommandCenter } from './components/CommandCenter';
import { TriageQueue } from './components/TriageQueue';
import { SplitPaneWorkbench } from './components/SplitPaneWorkbench';
import { CloneTicketModal } from './components/CloneTicketModal';
import { KnowledgeExplorer } from './components/KnowledgeExplorer';
import { SettingsView } from './components/SettingsView';
import { DocsDriftRadar } from './components/DocsDriftRadar';
import { AuditLogView } from './components/AuditLogView';
import { CommandPalette, PaletteItem } from './components/CommandPalette';
import { ShortcutsHelp } from './components/ShortcutsHelp';
import { useToast } from './components/Toaster';
import {
  fetchIssues,
  fetchIssueDetail,
  fetchStats,
  approveActions,
  rejectTriage,
  cloneIssue,
  reTriageIssue,
  syncIssues,
} from './api';
import { IssueListItem, IssueDetail } from './types';

export const App: React.FC = () => {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);

  const [currentTab, setCurrentTab] = useState<NavTab>('command_center');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedIssueId, setSelectedIssueId] = useState<string | undefined>();
  const [cloneModalIssue, setCloneModalIssue] = useState<IssueDetail | undefined>();

  // Fetch Dashboard Stats
  const { data: stats, isFetching: isStatsFetching, refetch: refetchStats } = useQuery({
    queryKey: ['stats'],
    queryFn: fetchStats,
    refetchInterval: 10000,
  });

  // Fetch Issues List
  const {
    data: issues = [],
    isLoading: isIssuesLoading,
    isFetching: isIssuesFetching,
    refetch: refetchIssues,
  } = useQuery({
    queryKey: ['issues', statusFilter, searchQuery],
    queryFn: () => fetchIssues({ status: statusFilter || undefined, search: searchQuery || undefined }),
    refetchInterval: 8000,
  });

  // Fetch Selected Issue Detail
  const activeIssueId = selectedIssueId || (issues.length > 0 ? issues[0].id : undefined);
  const { data: issueDetail, isLoading: isDetailLoading } = useQuery({
    queryKey: ['issueDetail', activeIssueId],
    queryFn: () => (activeIssueId ? fetchIssueDetail(activeIssueId) : Promise.reject()),
    enabled: !!activeIssueId && currentTab === 'triage_queue',
  });

  // Approve Mutation
  const approveMutation = useMutation({
    mutationFn: ({
      issueId,
      editedReply,
      customLabels,
    }: {
      issueId: string;
      editedReply?: string;
      customLabels?: string[];
    }) => approveActions(issueId, { edited_reply: editedReply, custom_labels: customLabels }),
    onSuccess: () => {
      toast('success', 'Actions approved and executed');
      queryClient.invalidateQueries({ queryKey: ['issues'] });
      queryClient.invalidateQueries({ queryKey: ['issueDetail'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
    onError: () => toast('error', 'Approval failed'),
  });

  // Reject Mutation
  const rejectMutation = useMutation({
    mutationFn: ({ issueId, reason }: { issueId: string; reason?: string }) =>
      rejectTriage(issueId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['issues'] });
      queryClient.invalidateQueries({ queryKey: ['issueDetail'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
  });

  // Clone Mutation
  const cloneMutation = useMutation({
    mutationFn: (payload: {
      target_project_id: number;
      new_title?: string;
      additional_context?: string;
      inherit_labels?: boolean;
    }) => {
      if (!cloneModalIssue) throw new Error('No issue selected for clone');
      return cloneIssue(cloneModalIssue.id, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['issues'] });
      queryClient.invalidateQueries({ queryKey: ['issueDetail'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
  });

  // Re-Triage Mutation
  const reTriageMutation = useMutation({
    mutationFn: (issueId: string) => reTriageIssue(issueId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['issueDetail'] });
      queryClient.invalidateQueries({ queryKey: ['issues'] });
    },
  });

  const paletteItems = useMemo<PaletteItem[]>(() => [
    { id: 't1', group: 'Go to', label: 'Command Center', hint: '1', run: () => setCurrentTab('command_center') },
    { id: 't2', group: 'Go to', label: 'Triage Queue', hint: '2', run: () => setCurrentTab('triage_queue') },
    { id: 't3', group: 'Go to', label: 'Knowledge Explorer', hint: '3', run: () => setCurrentTab('knowledge') },
    { id: 't4', group: 'Go to', label: 'Docs Drift Radar', hint: '4', run: () => setCurrentTab('drift') },
    { id: 't5', group: 'Go to', label: 'Audit Log', hint: '5', run: () => setCurrentTab('audit') },
    { id: 't6', group: 'Go to', label: 'Guardrails & Rules', hint: '6', run: () => setCurrentTab('settings') },
    { id: 'f1', group: 'Filter', label: 'Show all issues', run: () => { setStatusFilter(''); setCurrentTab('triage_queue'); } },
    { id: 'p', group: 'Action', label: 'Pull new issues from GitLab', run: () => pullMutation.mutate() },
    { id: 'r', group: 'Action', label: 'Refresh data', run: () => { handleManualRefresh(); toast('info', 'Refreshing…'); } },
    { id: 'h', group: 'Help', label: 'Keyboard shortcuts', hint: '?', run: () => setHelpOpen(true) },
    ...issues.slice(0, 15).map((i: IssueListItem) => ({
      id: 'i' + i.id, group: 'Issue', label: i.title ?? String(i.id),
      run: () => { setSelectedIssueId(i.id); setCurrentTab('triage_queue'); },
    })),
  // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [issues]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setPaletteOpen((o) => !o); return; }
      const el = e.target as HTMLElement;
      if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable || e.metaKey || e.ctrlKey) return;
      if (e.key === '/') { e.preventDefault(); document.getElementById('global-search')?.focus(); }
      else if (e.key === '?') setHelpOpen(true);
      else if (e.key === 'Escape') { setHelpOpen(false); setPaletteOpen(false); }
      else if (['1', '2', '3', '4', '5', '6'].includes(e.key)) setCurrentTab((['command_center', 'triage_queue', 'knowledge', 'drift', 'audit', 'settings'] as NavTab[])[+e.key - 1]);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const pullMutation = useMutation({
    mutationFn: () => syncIssues(),
    onSuccess: (r) => {
      toast('success', r.new > 0 ? `Pulled ${r.new} new issue${r.new > 1 ? 's' : ''} (${r.fetched} open) — triage running` : `No new issues (${r.fetched} open checked)`);
      queryClient.invalidateQueries({ queryKey: ['issues'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
      // triage runs in background; refresh again shortly
      setTimeout(() => { queryClient.invalidateQueries({ queryKey: ['issues'] }); queryClient.invalidateQueries({ queryKey: ['stats'] }); }, 8000);
    },
    onError: (e: unknown) => toast('error', e instanceof Error ? e.message : 'GitLab pull failed'),
  });

  const handleManualRefresh = () => {
    refetchStats();
    refetchIssues();
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background">
      {/* Left Navigation Sidebar */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        pendingCount={stats?.pending_approvals_count}
      />

      {/* Main Content Pane */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Top Header */}
        <Header
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onRefresh={handleManualRefresh}
          onPull={() => pullMutation.mutate()}
          isPulling={pullMutation.isPending}
          isFetching={isIssuesFetching || isStatsFetching}
        />

        {/* Dynamic View Display */}
        <main className="flex-1 overflow-hidden">
          {currentTab === 'command_center' && (
            <CommandCenter
              stats={stats}
              onNavigateToQueue={() => setCurrentTab('triage_queue')}
            />
          )}

          {currentTab === 'triage_queue' && (
            <div className="flex h-full w-full">
              {/* Left Column: Triage Queue Table */}
              <div className="w-[360px] min-w-[320px] max-w-[420px] h-full">
                <TriageQueue
                  issues={issues}
                  selectedIssueId={activeIssueId}
                  onSelectIssue={(i: IssueListItem) => setSelectedIssueId(i.id)}
                  statusFilter={statusFilter}
                  onStatusFilterChange={setStatusFilter}
                  isLoading={isIssuesLoading}
                />
              </div>

              {/* Right Column: Split-Pane Workbench */}
              <SplitPaneWorkbench
                issue={issueDetail}
                isLoading={isDetailLoading}
                onApprove={async (id, reply, labels) => {
                  await approveMutation.mutateAsync({ issueId: id, editedReply: reply, customLabels: labels });
                }}
                onReject={async (id, reason) => {
                  await rejectMutation.mutateAsync({ issueId: id, reason });
                }}
                onOpenCloneModal={(issue) => setCloneModalIssue(issue)}
                onReTriage={async (id) => {
                  await reTriageMutation.mutateAsync(id);
                }}
              />
            </div>
          )}

          {currentTab === 'knowledge' && <KnowledgeExplorer />}

          {currentTab === 'drift' && <DocsDriftRadar />}

          {currentTab === 'audit' && <AuditLogView />}

          {currentTab === 'settings' && <SettingsView />}
        </main>
      </div>

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} items={paletteItems} />
      <ShortcutsHelp open={helpOpen} onClose={() => setHelpOpen(false)} />
      {/* Ticket Cloning Modal */}
      <CloneTicketModal
        issue={cloneModalIssue}
        isOpen={!!cloneModalIssue}
        onClose={() => setCloneModalIssue(undefined)}
        onClone={async (payload) => {
          await cloneMutation.mutateAsync(payload);
        }}
      />
    </div>
  );
};

export default App;

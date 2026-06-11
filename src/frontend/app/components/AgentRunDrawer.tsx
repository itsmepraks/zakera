'use client'

import { CheckCircle2, Clock, ShieldAlert, XCircle } from 'lucide-react'
import type { AgentRun } from '../lib/api'

interface AgentRunDrawerProps {
  runs: AgentRun[]
  activeRun: AgentRun | null
  onSelectRun: (runId: string) => void
  onApprove: (runId: string, approvalId: string) => void
  onReject: (runId: string, approvalId: string) => void
}

const statusStyles: Record<string, string> = {
  completed: 'text-emerald-700 bg-emerald-50 border-emerald-200',
  running: 'text-blue-700 bg-blue-50 border-blue-200',
  waiting_for_approval: 'text-amber-700 bg-amber-50 border-amber-200',
  failed: 'text-red-700 bg-red-50 border-red-200',
  rejected: 'text-gray-700 bg-gray-50 border-gray-200',
}

function StatusIcon({ status }: { status: string }) {
  if (status === 'completed') return <CheckCircle2 className="w-4 h-4" />
  if (status === 'failed' || status === 'rejected') return <XCircle className="w-4 h-4" />
  if (status === 'waiting_for_approval') return <ShieldAlert className="w-4 h-4" />
  return <Clock className="w-4 h-4" />
}

export default function AgentRunDrawer({
  runs,
  activeRun,
  onSelectRun,
  onApprove,
  onReject,
}: AgentRunDrawerProps) {
  const pendingApprovals =
    activeRun?.approvals?.filter((approval) => approval.status === 'pending') || []

  return (
    <aside className="w-96 border-l border-gray-200 bg-white flex flex-col">
      <div className="px-4 py-3 border-b border-gray-200">
        <h2 className="font-semibold text-gray-900">Agent Runs</h2>
        <p className="text-xs text-gray-500 mt-1">Observable activity for this conversation</p>
      </div>

      <div className="border-b border-gray-200 max-h-56 overflow-y-auto">
        {runs.length === 0 ? (
          <div className="p-4 text-sm text-gray-500">No runs yet.</div>
        ) : (
          runs.map((run) => (
            <button
              key={run.id}
              onClick={() => onSelectRun(run.id)}
              className={`w-full text-left px-4 py-3 border-b border-gray-100 hover:bg-gray-50 ${
                activeRun?.id === run.id ? 'bg-blue-50' : ''
              }`}
            >
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-medium text-gray-900 truncate">
                  {run.model_name}
                </span>
                <span
                  className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs border rounded-full ${
                    statusStyles[run.status] || statusStyles.running
                  }`}
                >
                  <StatusIcon status={run.status} />
                  {run.status.replaceAll('_', ' ')}
                </span>
              </div>
              <div className="mt-1 text-xs text-gray-500">
                {run.created_at ? new Date(run.created_at).toLocaleString() : run.id.slice(0, 8)}
              </div>
            </button>
          ))
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {!activeRun ? (
          <div className="text-sm text-gray-500">Select a run to inspect its trace.</div>
        ) : (
          <div className="space-y-4">
            {pendingApprovals.length > 0 && (
              <div className="border border-amber-200 bg-amber-50 rounded-lg p-3">
                <div className="text-sm font-medium text-amber-900">Approval required</div>
                {pendingApprovals.map((approval) => (
                  <div key={approval.id} className="mt-3">
                    <div className="text-sm text-amber-800">{approval.reason}</div>
                    <div className="mt-3 flex gap-2">
                      <button
                        onClick={() => onApprove(activeRun.id, approval.id)}
                        className="px-3 py-1.5 text-sm bg-amber-700 text-white rounded-md hover:bg-amber-800"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => onReject(activeRun.id, approval.id)}
                        className="px-3 py-1.5 text-sm bg-white border border-amber-300 text-amber-800 rounded-md hover:bg-amber-100"
                      >
                        Reject
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <ol className="space-y-2">
              {(activeRun.steps || []).map((step) => (
                <li key={step.id} className="border border-gray-200 rounded-lg p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-gray-900 truncate">
                        {step.label}
                      </div>
                      <div className="text-xs text-gray-500">
                        {step.step_type}
                        {step.tool_name ? ` · ${step.tool_name}` : ''}
                      </div>
                    </div>
                    <span className="text-xs text-gray-500">{step.status}</span>
                  </div>
                  {step.detail && (
                    <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap text-xs bg-gray-50 border border-gray-100 rounded-md p-2 text-gray-700">
                      {step.detail}
                    </pre>
                  )}
                  {step.error && (
                    <div className="mt-2 text-xs text-red-700">{step.error}</div>
                  )}
                </li>
              ))}
            </ol>
          </div>
        )}
      </div>
    </aside>
  )
}

/**
 * AgentThinkingPanel — renders the agent's chain-of-thought as a collapsible
 * panel that animates each reasoning step as it arrives in real time.
 *
 * Props:
 *   steps           — ThinkingStep[] from useAgentThinking
 *   status          — AgentThinkingStatus from useAgentThinking
 *   elapsedLabel    — formatted elapsed time string
 *   activeStepIndex — index of the currently executing step (-1 if none)
 *   onCancel        — optional callback to cancel inference mid-flight
 *   defaultExpanded — whether the panel starts open (default: true)
 */

import React, { useCallback, useState } from 'react';
import type { ThinkingStep, AgentThinkingStatus } from '../hooks/useAgentThinking';
import styles from './AgentThinkingPanel.module.css';

// ---------------------------------------------------------------------------
// Icon helpers
// ---------------------------------------------------------------------------

const StepIcon: React.FC<{ status: ThinkingStep['status'] }> = ({ status }) => {
  if (status === 'active') {
    return (
      <span className={styles.spinnerIcon} aria-label="In progress">
        &#9696;
      </span>
    );
  }
  if (status === 'done') {
    return (
      <span className={styles.doneIcon} aria-label="Done">
        &#10003;
      </span>
    );
  }
  if (status === 'error') {
    return (
      <span className={styles.errorIcon} aria-label="Error">
        &#10007;
      </span>
    );
  }
  return (
    <span className={styles.pendingIcon} aria-label="Pending">
      &#9675;
    </span>
  );
};

// ---------------------------------------------------------------------------
// Single step row
// ---------------------------------------------------------------------------

interface StepRowProps {
  step: ThinkingStep;
  isActive: boolean;
}

const StepRow: React.FC<StepRowProps> = ({ step, isActive }) => {
  const [expanded, setExpanded] = useState(false);

  const durationLabel =
    step.finishedAt > 0
      ? `${((step.finishedAt - step.startedAt) / 1000).toFixed(2)}s`
      : null;

  const toggleExpand = useCallback(() => setExpanded((v) => !v), []);

  return (
    <li
      className={`${styles.stepRow} ${
        isActive ? styles.stepRowActive : ''
      } ${step.status === 'error' ? styles.stepRowError : ''} ${
        step.status === 'done' ? styles.stepRowDone : ''
      }`}
      aria-current={isActive ? 'step' : undefined}
    >
      <div className={styles.stepHeader}>
        <StepIcon status={step.status} />

        <span className={styles.stepLabel}>
          {step.tool ? (
            <>
              <span className={styles.toolBadge}>{step.tool}</span>{' '}
            </>
          ) : null}
          {step.label}
        </span>

        <div className={styles.stepMeta}>
          {step.tokens !== undefined && (
            <span className={styles.tokenBadge}>{step.tokens} tok</span>
          )}
          {durationLabel && (
            <span className={styles.durationLabel}>{durationLabel}</span>
          )}
          {step.detail && (
            <button
              className={styles.expandBtn}
              onClick={toggleExpand}
              aria-expanded={expanded}
              aria-label={expanded ? 'Collapse detail' : 'Expand detail'}
            >
              {expanded ? '▲' : '▼'}
            </button>
          )}
        </div>
      </div>

      {expanded && step.detail && (
        <pre className={styles.stepDetail}>{step.detail}</pre>
      )}
    </li>
  );
};

// ---------------------------------------------------------------------------
// Status header
// ---------------------------------------------------------------------------

const statusLabel: Record<AgentThinkingStatus, string> = {
  idle: 'Idle',
  thinking: 'Thinking…',
  streaming: 'Composing response…',
  done: 'Done',
  error: 'Error',
};

// ---------------------------------------------------------------------------
// Main panel
// ---------------------------------------------------------------------------

export interface AgentThinkingPanelProps {
  steps: ThinkingStep[];
  status: AgentThinkingStatus;
  elapsedLabel: string;
  activeStepIndex: number;
  onCancel?: () => void;
  defaultExpanded?: boolean;
  className?: string;
}

export const AgentThinkingPanel: React.FC<AgentThinkingPanelProps> = ({
  steps,
  status,
  elapsedLabel,
  activeStepIndex,
  onCancel,
  defaultExpanded = true,
  className = '',
}) => {
  const [panelOpen, setPanelOpen] = useState(defaultExpanded);

  const toggle = useCallback(() => setPanelOpen((v) => !v), []);

  if (status === 'idle' && steps.length === 0) {
    return null;
  }

  const isInProgress = status === 'thinking' || status === 'streaming';

  return (
    <section
      className={`${styles.panel} ${
        isInProgress ? styles.panelActive : ''
      } ${status === 'error' ? styles.panelError : ''} ${className}`}
      aria-label="Agent reasoning panel"
      role="region"
    >
      {/* ---------------------------------------------------------------- */}
      {/* Header */}
      {/* ---------------------------------------------------------------- */}
      <div className={styles.panelHeader}>
        <div className={styles.panelTitle}>
          {isInProgress && (
            <span className={styles.pulsingDot} aria-hidden="true" />
          )}
          <span className={styles.panelTitleText}>
            {statusLabel[status]}
          </span>
          {isInProgress && (
            <span className={styles.elapsedLabel}>{elapsedLabel}</span>
          )}
          {status === 'done' && steps.length > 0 && (
            <span className={styles.elapsedLabel}>
              {steps.length} step{steps.length !== 1 ? 's' : ''} · {elapsedLabel}
            </span>
          )}
        </div>

        <div className={styles.panelControls}>
          {isInProgress && onCancel && (
            <button
              className={styles.cancelBtn}
              onClick={onCancel}
              aria-label="Cancel agent inference"
            >
              Stop
            </button>
          )}
          <button
            className={styles.collapseBtn}
            onClick={toggle}
            aria-expanded={panelOpen}
            aria-label={panelOpen ? 'Collapse thinking panel' : 'Expand thinking panel'}
          >
            {panelOpen ? '▲' : '▼'}
          </button>
        </div>
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* Step list */}
      {/* ---------------------------------------------------------------- */}
      {panelOpen && steps.length > 0 && (
        <ol className={styles.stepList} aria-label="Reasoning steps">
          {steps.map((step, idx) => (
            <StepRow
              key={step.id}
              step={step}
              isActive={idx === activeStepIndex}
            />
          ))}
        </ol>
      )}

      {panelOpen && steps.length === 0 && isInProgress && (
        <p className={styles.waitingText}>Initialising agent…</p>
      )}
    </section>
  );
};

export default AgentThinkingPanel;

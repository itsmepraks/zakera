/**
 * ToolIntegration Component
 * Integrates tool system with the chat interface
 */

import React, { useState } from 'react';
import { Wrench, X, Maximize2, Minimize2 } from 'lucide-react';
import { Tool, ToolExecutionResult } from '@/types/tools.types';
import { ToolSelector } from './ToolSelector';
import { ToolExecutionPanel } from './ToolExecutionPanel';
import { ToolHistory } from './ToolHistory';
import './ToolIntegration.css';

interface ToolIntegrationProps {
  onToolResult?: (result: ToolExecutionResult) => void;
  initialView?: 'selector' | 'execution' | 'history';
  embedded?: boolean;
}

export const ToolIntegration: React.FC<ToolIntegrationProps> = ({
  onToolResult,
  initialView = 'selector',
  embedded = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [currentView, setCurrentView] = useState<'selector' | 'execution' | 'history'>(
    initialView
  );
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  const handleToolSelect = (tool: Tool) => {
    setSelectedTool(tool);
    setCurrentView('execution');
  };

  const handleExecutionComplete = (result: ToolExecutionResult) => {
    onToolResult?.(result);
    // Optionally switch to history view
    // setCurrentView('history');
  };

  const handleReExecute = (toolName: string, parameters: Record<string, any>) => {
    // Find the tool and pre-fill parameters
    // This would require fetching tool info
    setCurrentView('execution');
  };

  const handleClose = () => {
    setIsOpen(false);
  };

  const renderContent = () => {
    switch (currentView) {
      case 'selector':
        return (
          <ToolSelector
            onToolSelect={handleToolSelect}
            selectedTool={selectedTool}
            compact={!isExpanded}
          />
        );
      case 'execution':
        return selectedTool ? (
          <ToolExecutionPanel
            tool={selectedTool}
            onExecutionComplete={handleExecutionComplete}
          />
        ) : (
          <div className="no-tool-selected">
            <p>Please select a tool first</p>
            <button onClick={() => setCurrentView('selector')} className="select-tool-btn">
              Select Tool
            </button>
          </div>
        );
      case 'history':
        return <ToolHistory onReExecute={handleReExecute} autoRefresh />;
      default:
        return null;
    }
  };

  if (embedded) {
    // Embedded mode - always visible
    return (
      <div className="tool-integration embedded">
        <div className="integration-header">
          <div className="view-tabs">
            <button
              className={`view-tab ${currentView === 'selector' ? 'active' : ''}`}
              onClick={() => setCurrentView('selector')}
            >
              Tools
            </button>
            <button
              className={`view-tab ${currentView === 'execution' ? 'active' : ''}`}
              onClick={() => setCurrentView('execution')}
              disabled={!selectedTool}
            >
              Execute
            </button>
            <button
              className={`view-tab ${currentView === 'history' ? 'active' : ''}`}
              onClick={() => setCurrentView('history')}
            >
              History
            </button>
          </div>
        </div>
        <div className="integration-content">{renderContent()}</div>
      </div>
    );
  }

  // Floating panel mode
  return (
    <>
      {/* Floating Action Button */}
      {!isOpen && (
        <button
          className="tool-fab"
          onClick={() => setIsOpen(true)}
          aria-label="Open tools"
        >
          <Wrench className="icon" />
        </button>
      )}

      {/* Floating Panel */}
      {isOpen && (
        <div className={`tool-integration floating ${isExpanded ? 'expanded' : ''}`}>
          <div className="integration-header">
            <div className="view-tabs">
              <button
                className={`view-tab ${currentView === 'selector' ? 'active' : ''}`}
                onClick={() => setCurrentView('selector')}
              >
                Tools
              </button>
              <button
                className={`view-tab ${currentView === 'execution' ? 'active' : ''}`}
                onClick={() => setCurrentView('execution')}
                disabled={!selectedTool}
              >
                Execute
              </button>
              <button
                className={`view-tab ${currentView === 'history' ? 'active' : ''}`}
                onClick={() => setCurrentView('history')}
              >
                History
              </button>
            </div>
            <div className="header-actions">
              <button
                className="action-btn"
                onClick={() => setIsExpanded(!isExpanded)}
                aria-label={isExpanded ? 'Minimize' : 'Maximize'}
              >
                {isExpanded ? <Minimize2 className="icon" /> : <Maximize2 className="icon" />}
              </button>
              <button className="action-btn" onClick={handleClose} aria-label="Close">
                <X className="icon" />
              </button>
            </div>
          </div>
          <div className="integration-content">{renderContent()}</div>
        </div>
      )}
    </>
  );
};

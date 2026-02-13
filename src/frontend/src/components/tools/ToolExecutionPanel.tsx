/**
 * ToolExecutionPanel Component
 * Allows users to execute tools with dynamic parameter forms
 */

import React, { useState, useEffect } from 'react';
import {
  Play,
  Loader2,
  CheckCircle,
  XCircle,
  Copy,
  Clock,
  AlertCircle,
} from 'lucide-react';
import { Tool, ToolExecutionResult, ToolParameter } from '@/types/tools.types';
import { toolService } from '@/services/toolService';
import './ToolExecutionPanel.css';

interface ToolExecutionPanelProps {
  tool: Tool;
  onExecutionComplete?: (result: ToolExecutionResult) => void;
  initialParameters?: Record<string, any>;
}

export const ToolExecutionPanel: React.FC<ToolExecutionPanelProps> = ({
  tool,
  onExecutionComplete,
  initialParameters = {},
}) => {
  const [parameters, setParameters] = useState<Record<string, any>>(initialParameters);
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState<ToolExecutionResult | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    // Initialize parameters with defaults
    const defaultParams: Record<string, any> = {};
    tool.parameters.forEach((param) => {
      if (param.default !== undefined) {
        defaultParams[param.name] = param.default;
      }
    });
    setParameters({ ...defaultParams, ...initialParameters });
  }, [tool, initialParameters]);

  const validateParameter = (param: ToolParameter, value: any): string | null => {
    if (param.required && (value === undefined || value === null || value === '')) {
      return `${param.name} is required`;
    }

    if (value === undefined || value === null || value === '') {
      return null;
    }

    // Type validation
    switch (param.type) {
      case 'number':
        if (isNaN(Number(value))) {
          return `${param.name} must be a number`;
        }
        if (param.min !== undefined && Number(value) < param.min) {
          return `${param.name} must be at least ${param.min}`;
        }
        if (param.max !== undefined && Number(value) > param.max) {
          return `${param.name} must be at most ${param.max}`;
        }
        break;
      case 'string':
        if (param.pattern) {
          const regex = new RegExp(param.pattern);
          if (!regex.test(String(value))) {
            return `${param.name} format is invalid`;
          }
        }
        break;
      case 'boolean':
        if (typeof value !== 'boolean' && value !== 'true' && value !== 'false') {
          return `${param.name} must be true or false`;
        }
        break;
    }

    return null;
  };

  const validateAllParameters = (): boolean => {
    const newErrors: Record<string, string> = {};
    tool.parameters.forEach((param) => {
      const error = validateParameter(param, parameters[param.name]);
      if (error) {
        newErrors[param.name] = error;
      }
    });
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleParameterChange = (paramName: string, value: any) => {
    setParameters((prev) => ({ ...prev, [paramName]: value }));
    // Clear error for this field
    if (errors[paramName]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[paramName];
        return newErrors;
      });
    }
  };

  const handleExecute = async () => {
    if (!validateAllParameters()) {
      return;
    }

    setExecuting(true);
    setResult(null);

    try {
      const executionResult = await toolService.executeTool(tool.name, parameters);
      setResult(executionResult);
      onExecutionComplete?.(executionResult);
    } catch (error) {
      const errorResult: ToolExecutionResult = {
        success: false,
        error: error instanceof Error ? error.message : 'Execution failed',
        timestamp: new Date().toISOString(),
        tool_name: tool.name,
        parameters,
      };
      setResult(errorResult);
      onExecutionComplete?.(errorResult);
    } finally {
      setExecuting(false);
    }
  };

  const handleCopyResult = () => {
    if (result?.result) {
      navigator.clipboard.writeText(JSON.stringify(result.result, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const renderParameterInput = (param: ToolParameter) => {
    const value = parameters[param.name] ?? '';
    const hasError = !!errors[param.name];

    switch (param.type) {
      case 'boolean':
        return (
          <div className="parameter-input">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={value === true || value === 'true'}
                onChange={(e) => handleParameterChange(param.name, e.target.checked)}
                className="checkbox-input"
              />
              <span>{param.name}</span>
              {param.required && <span className="required">*</span>}
            </label>
            <p className="param-description">{param.description}</p>
          </div>
        );

      case 'number':
        return (
          <div className="parameter-input">
            <label className="input-label">
              {param.name}
              {param.required && <span className="required">*</span>}
            </label>
            <input
              type="number"
              value={value}
              onChange={(e) => handleParameterChange(param.name, parseFloat(e.target.value))}
              min={param.min}
              max={param.max}
              className={`text-input ${hasError ? 'error' : ''}`}
              placeholder={param.description}
            />
            <p className="param-description">{param.description}</p>
            {hasError && <p className="error-text">{errors[param.name]}</p>}
          </div>
        );

      case 'array':
      case 'object':
        return (
          <div className="parameter-input">
            <label className="input-label">
              {param.name}
              {param.required && <span className="required">*</span>}
            </label>
            <textarea
              value={typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
              onChange={(e) => {
                try {
                  const parsed = JSON.parse(e.target.value);
                  handleParameterChange(param.name, parsed);
                } catch {
                  handleParameterChange(param.name, e.target.value);
                }
              }}
              className={`textarea-input ${hasError ? 'error' : ''}`}
              placeholder={`Enter JSON ${param.type}`}
              rows={4}
            />
            <p className="param-description">{param.description}</p>
            {hasError && <p className="error-text">{errors[param.name]}</p>}
          </div>
        );

      default:
        // String or enum
        if (param.enum && param.enum.length > 0) {
          return (
            <div className="parameter-input">
              <label className="input-label">
                {param.name}
                {param.required && <span className="required">*</span>}
              </label>
              <select
                value={value}
                onChange={(e) => handleParameterChange(param.name, e.target.value)}
                className={`select-input ${hasError ? 'error' : ''}`}
              >
                <option value="">Select...</option>
                {param.enum.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
              <p className="param-description">{param.description}</p>
              {hasError && <p className="error-text">{errors[param.name]}</p>}
            </div>
          );
        }

        return (
          <div className="parameter-input">
            <label className="input-label">
              {param.name}
              {param.required && <span className="required">*</span>}
            </label>
            <input
              type="text"
              value={value}
              onChange={(e) => handleParameterChange(param.name, e.target.value)}
              className={`text-input ${hasError ? 'error' : ''}`}
              placeholder={param.description}
            />
            <p className="param-description">{param.description}</p>
            {hasError && <p className="error-text">{errors[param.name]}</p>}
          </div>
        );
    }
  };

  return (
    <div className="tool-execution-panel">
      <div className="panel-header">
        <h3 className="panel-title">Execute: {tool.name}</h3>
      </div>

      <div className="panel-content">
        {/* Parameters Form */}
        <div className="parameters-form">
          <h4 className="form-title">Parameters</h4>
          {tool.parameters.length === 0 ? (
            <p className="no-params-message">
              This tool doesn't require any parameters.
            </p>
          ) : (
            <div className="parameters-list">
              {tool.parameters.map((param) => (
                <div key={param.name}>{renderParameterInput(param)}</div>
              ))}
            </div>
          )}
        </div>

        {/* Execute Button */}
        <div className="execute-actions">
          <button
            onClick={handleExecute}
            disabled={executing}
            className="execute-btn"
            aria-label="Execute tool"
          >
            {executing ? (
              <>
                <Loader2 className="icon animate-spin" />
                Executing...
              </>
            ) : (
              <>
                <Play className="icon" />
                Execute Tool
              </>
            )}
          </button>
        </div>

        {/* Result Display */}
        {result && (
          <div className={`result-container ${result.success ? 'success' : 'error'}`}>
            <div className="result-header">
              <div className="result-status">
                {result.success ? (
                  <>
                    <CheckCircle className="icon success" />
                    <span>Success</span>
                  </>
                ) : (
                  <>
                    <XCircle className="icon error" />
                    <span>Failed</span>
                  </>
                )}
              </div>
              <div className="result-meta">
                {result.execution_time && (
                  <span className="execution-time">
                    <Clock className="icon" />
                    {result.execution_time.toFixed(2)}s
                  </span>
                )}
                {result.success && (
                  <button
                    onClick={handleCopyResult}
                    className="copy-btn"
                    aria-label="Copy result"
                  >
                    <Copy className="icon" />
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                )}
              </div>
            </div>

            <div className="result-content">
              {result.error ? (
                <div className="error-display">
                  <AlertCircle className="icon" />
                  <span>{result.error}</span>
                </div>
              ) : (
                <pre className="result-data">
                  {JSON.stringify(result.result, null, 2)}
                </pre>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

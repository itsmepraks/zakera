/**
 * MessageRenderer Component
 * 
 * Renders chat messages with rich formatting including:
 * - Markdown rendering
 * - Code syntax highlighting
 * - Copy-to-clipboard for code blocks
 * - Math equations
 * - Tables, lists, and more
 */

import React, { useCallback, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import './MessageRenderer.css';

interface MessageRendererProps {
  content: string;
  role: 'user' | 'assistant' | 'system';
  theme?: 'light' | 'dark';
}

interface CodeBlockProps {
  inline?: boolean;
  className?: string;
  children: React.ReactNode;
  theme: 'light' | 'dark';
}

const CodeBlock: React.FC<CodeBlockProps> = React.memo(({ 
  inline, 
  className, 
  children, 
  theme 
}) => {
  const [copied, setCopied] = useState(false);
  
  const match = /language-(\w+)/.exec(className || '');
  const language = match ? match[1] : '';
  const code = String(children).replace(/\n$/, '');
  
  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy code:', err);
    }
  }, [code]);
  
  if (inline) {
    return (
      <code className="inline-code">
        {children}
      </code>
    );
  }
  
  return (
    <div className="code-block-wrapper">
      <div className="code-block-header">
        <span className="code-language">
          {language || 'text'}
        </span>
        <button
          className="copy-button"
          onClick={handleCopy}
          aria-label="Copy code to clipboard"
          title={copied ? 'Copied!' : 'Copy code'}
        >
          {copied ? (
            <span className="copy-icon copied">✓ Copied</span>
          ) : (
            <span className="copy-icon">📋 Copy</span>
          )}
        </button>
      </div>
      <SyntaxHighlighter
        language={language}
        style={theme === 'dark' ? oneDark : oneLight}
        showLineNumbers={true}
        wrapLines={true}
        customStyle={{
          margin: 0,
          borderRadius: '0 0 8px 8px',
          fontSize: '14px',
        }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
});

CodeBlock.displayName = 'CodeBlock';

export const MessageRenderer: React.FC<MessageRendererProps> = React.memo(({
  content,
  role,
  theme = 'light'
}) => {
  return (
    <div className={`message-renderer message-${role}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          code({ inline, className, children, ...props }) {
            return (
              <CodeBlock
                inline={inline}
                className={className}
                theme={theme}
                {...props}
              >
                {children}
              </CodeBlock>
            );
          },
          a({ href, children, ...props }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="markdown-link"
                {...props}
              >
                {children}
                <span className="external-link-icon">↗</span>
              </a>
            );
          },
          table({ children, ...props }) {
            return (
              <div className="table-wrapper">
                <table className="markdown-table" {...props}>
                  {children}
                </table>
              </div>
            );
          },
          blockquote({ children, ...props }) {
            return (
              <blockquote className="markdown-blockquote" {...props}>
                <div className="blockquote-indicator" />
                {children}
              </blockquote>
            );
          },
          h1({ children, ...props }) {
            return <h1 className="markdown-h1" {...props}>{children}</h1>;
          },
          h2({ children, ...props }) {
            return <h2 className="markdown-h2" {...props}>{children}</h2>;
          },
          h3({ children, ...props }) {
            return <h3 className="markdown-h3" {...props}>{children}</h3>;
          },
          ul({ children, ...props }) {
            return <ul className="markdown-list" {...props}>{children}</ul>;
          },
          ol({ children, ...props }) {
            return <ol className="markdown-list" {...props}>{children}</ol>;
          },
          li({ children, ...props }) {
            return <li className="markdown-list-item" {...props}>{children}</li>;
          },
          p({ children, ...props }) {
            return <p className="markdown-paragraph" {...props}>{children}</p>;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
});

MessageRenderer.displayName = 'MessageRenderer';

export default MessageRenderer;

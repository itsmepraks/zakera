import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { CodeBlock } from './CodeBlock';
import 'katex/dist/katex.min.css';

interface MessageContentProps {
  content: string;
  role: 'user' | 'assistant';
}

export const MessageContent: React.FC<MessageContentProps> = ({ content, role }) => {
  return (
    <div className="prose prose-sm md:prose-base max-w-none dark:prose-invert">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          code({ node, inline, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '');
            const language = match ? match[1] : '';
            const codeString = String(children).replace(/\n$/, '');

            if (!inline && language) {
              return (
                <CodeBlock
                  code={codeString}
                  language={language}
                  showLineNumbers={codeString.split('\n').length > 5}
                />
              );
            }

            return (
              <code
                className="px-1.5 py-0.5 rounded-md bg-gray-100 dark:bg-gray-800 text-sm font-mono"
                {...props}
              >
                {children}
              </code>
            );
          },
          pre({ children }) {
            return <>{children}</>;
          },
          a({ href, children, ...props }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 dark:text-blue-400 hover:underline"
                {...props}
              >
                {children}
              </a>
            );
          },
          table({ children }) {
            return (
              <div className="overflow-x-auto my-4">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  {children}
                </table>
              </div>
            );
          },
          th({ children, ...props }) {
            return (
              <th
                className="px-4 py-2 bg-gray-50 dark:bg-gray-800 text-left text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider"
                {...props}
              >
                {children}
              </th>
            );
          },
          td({ children, ...props }) {
            return (
              <td
                className="px-4 py-2 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100"
                {...props}
              >
                {children}
              </td>
            );
          },
          blockquote({ children }) {
            return (
              <blockquote className="border-l-4 border-blue-500 pl-4 py-2 my-4 italic bg-blue-50 dark:bg-blue-900/20">
                {children}
              </blockquote>
            );
          },
          ul({ children }) {
            return (
              <ul className="list-disc list-inside space-y-1 my-2">
                {children}
              </ul>
            );
          },
          ol({ children }) {
            return (
              <ol className="list-decimal list-inside space-y-1 my-2">
                {children}
              </ol>
            );
          },
          h1({ children }) {
            return (
              <h1 className="text-2xl font-bold mt-6 mb-4 text-gray-900 dark:text-gray-100">
                {children}
              </h1>
            );
          },
          h2({ children }) {
            return (
              <h2 className="text-xl font-bold mt-5 mb-3 text-gray-900 dark:text-gray-100">
                {children}
              </h2>
            );
          },
          h3({ children }) {
            return (
              <h3 className="text-lg font-semibold mt-4 mb-2 text-gray-900 dark:text-gray-100">
                {children}
              </h3>
            );
          },
          p({ children }) {
            return (
              <p className="my-2 text-gray-800 dark:text-gray-200 leading-relaxed">
                {children}
              </p>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

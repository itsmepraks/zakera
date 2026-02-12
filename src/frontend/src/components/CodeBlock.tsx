import React, { useState } from 'react';
import { Check, Copy, FileCode } from 'lucide-react';
import Prism from 'prismjs';
import 'prismjs/themes/prism-tomorrow.css';

// Import common language syntaxes
import 'prismjs/components/prism-javascript';
import 'prismjs/components/prism-typescript';
import 'prismjs/components/prism-python';
import 'prismjs/components/prism-java';
import 'prismjs/components/prism-c';
import 'prismjs/components/prism-cpp';
import 'prismjs/components/prism-csharp';
import 'prismjs/components/prism-go';
import 'prismjs/components/prism-rust';
import 'prismjs/components/prism-ruby';
import 'prismjs/components/prism-php';
import 'prismjs/components/prism-swift';
import 'prismjs/components/prism-kotlin';
import 'prismjs/components/prism-sql';
import 'prismjs/components/prism-bash';
import 'prismjs/components/prism-json';
import 'prismjs/components/prism-yaml';
import 'prismjs/components/prism-markdown';
import 'prismjs/components/prism-jsx';
import 'prismjs/components/prism-tsx';

interface CodeBlockProps {
  code: string;
  language: string;
  fileName?: string;
  showLineNumbers?: boolean;
}

const LANGUAGE_DISPLAY_NAMES: Record<string, string> = {
  javascript: 'JavaScript',
  typescript: 'TypeScript',
  python: 'Python',
  java: 'Java',
  c: 'C',
  cpp: 'C++',
  csharp: 'C#',
  go: 'Go',
  rust: 'Rust',
  ruby: 'Ruby',
  php: 'PHP',
  swift: 'Swift',
  kotlin: 'Kotlin',
  sql: 'SQL',
  bash: 'Bash',
  json: 'JSON',
  yaml: 'YAML',
  markdown: 'Markdown',
  jsx: 'JSX',
  tsx: 'TSX',
  html: 'HTML',
  css: 'CSS',
};

export const CodeBlock: React.FC<CodeBlockProps> = ({
  code,
  language,
  fileName,
  showLineNumbers = false,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy code:', err);
    }
  };

  // Highlight code using Prism
  const highlightedCode = React.useMemo(() => {
    try {
      const grammar = Prism.languages[language];
      if (grammar) {
        return Prism.highlight(code, grammar, language);
      }
      return code;
    } catch (error) {
      console.error('Syntax highlighting error:', error);
      return code;
    }
  }, [code, language]);

  const lines = code.split('\n');
  const displayLanguage = LANGUAGE_DISPLAY_NAMES[language] || language.toUpperCase();

  return (
    <div className="my-4 rounded-lg overflow-hidden border border-gray-700 bg-[#2d2d2d] shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#1e1e1e] border-b border-gray-700">
        <div className="flex items-center gap-2">
          <FileCode className="w-4 h-4 text-gray-400" />
          {fileName ? (
            <span className="text-sm text-gray-300 font-mono">{fileName}</span>
          ) : (
            <span className="text-xs px-2 py-0.5 rounded bg-blue-600/20 text-blue-400 font-medium">
              {displayLanguage}
            </span>
          )}
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-2 py-1 text-xs text-gray-400 hover:text-gray-200 hover:bg-gray-700 rounded transition-colors"
          aria-label="Copy code"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5" />
              Copied!
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              Copy
            </>
          )}
        </button>
      </div>

      {/* Code Content */}
      <div className="relative overflow-x-auto">
        <pre className="p-4 text-sm leading-relaxed">
          <code
            className={`language-${language} block`}
            style={{ fontFamily: 'Menlo, Monaco, "Courier New", monospace' }}
          >
            {showLineNumbers ? (
              <table className="w-full border-collapse">
                <tbody>
                  {lines.map((line, index) => {
                    const lineNumber = index + 1;
                    // Extract the highlighted content for this line
                    const lineContent = line;

                    return (
                      <tr key={index}>
                        <td className="pr-4 text-right select-none text-gray-500 align-top">
                          <span className="inline-block min-w-[2ch]">
                            {lineNumber}
                          </span>
                        </td>
                        <td className="text-gray-200">
                          <span
                            dangerouslySetInnerHTML={{
                              __html: Prism.highlight(
                                lineContent,
                                Prism.languages[language] || {},
                                language
                              ),
                            }}
                          />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            ) : (
              <span
                className="text-gray-200"
                dangerouslySetInnerHTML={{ __html: highlightedCode }}
              />
            )}
          </code>
        </pre>
      </div>
    </div>
  );
};

import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { API_BASE } from '../../config';

const HelpGuide = ({ onBackToMenu }) => {
  const [content, setContent] = useState('');
  const [title, setTitle] = useState('Paydirt User Guide');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchGuide = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/guide`);
        if (!response.ok) {
          throw new Error('Failed to load guide');
        }
        const data = await response.json();
        setContent(data.content);
        setTitle(data.title);
        setIsLoading(false);
      } catch (err) {
        setError(err.message);
        setIsLoading(false);
      }
    };

    fetchGuide();
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-400">Loading guide...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-red-500 mb-4">Error Loading Guide</h2>
          <p className="text-gray-400 mb-8">{error}</p>
          <button
            onClick={onBackToMenu}
            className="px-8 py-4 bg-gray-700 text-white rounded-lg font-bold hover:bg-gray-600 transition-all"
          >
            BACK TO MENU
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      {/* Header */}
      <div className="sticky top-0 bg-gray-800 border-b border-gray-700 px-6 py-4 flex justify-between items-center z-10">
        <h1 className="text-2xl font-bold">{title}</h1>
        <button
          onClick={onBackToMenu}
          className="px-6 py-2 bg-gray-700 text-white rounded-lg font-bold hover:bg-gray-600 transition-all"
        >
          BACK TO MENU
        </button>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="prose prose-invert prose-lg max-w-none 
          prose-headings:text-gray-100 
          prose-h1:text-4xl prose-h1:font-bold prose-h1:border-b prose-h1:border-gray-700 prose-h1:pb-4 prose-h1:mb-6
          prose-h2:text-2xl prose-h2:font-bold prose-h2:text-blue-400 prose-h2:mt-8 prose-h2:mb-4
          prose-h3:text-xl prose-h3:font-semibold prose-h3:text-gray-200
          prose-h4:text-lg prose-h4:font-semibold
          prose-p:text-gray-300 prose-p:leading-relaxed
          prose-a:text-blue-400 prose-a:hover:text-blue-300
          prose-strong:text-white
          prose-code:text-green-400 prose-code:bg-gray-800 prose-code:px-1 prose-code:rounded
          prose-pre:bg-gray-800 prose-pre:border prose-pre:border-gray-700
          prose-ul:text-gray-300
          prose-ol:text-gray-300
          prose-li:marker:text-gray-500
          prose-table:border-collapse
          prose-th:bg-gray-800 prose-th:border prose-th:border-gray-700 prose-th:px-4 prose-th:py-2 prose-th:text-left
          prose-td:border prose-td:border-gray-700 prose-td:px-4 prose-td:py-2
          prose-hr:border-gray-700"
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-gray-700 px-6 py-4 text-center">
        <button
          onClick={onBackToMenu}
          className="px-8 py-3 bg-blue-600 text-white rounded-lg font-bold hover:bg-blue-700 transition-all"
        >
          BACK TO MENU
        </button>
      </div>
    </div>
  );
};

export default HelpGuide;

import React, { useState, useRef } from 'react';
import './index.css';

interface AnalysisResults {
  syntax_check: string;
  pylint_results: string;
  original_test_results: string;
  original_test_success: boolean;
  logical_fix_explanation: string;
  fixed_code: string;
  fixed_test_results: string;
  fixed_test_success: boolean;
}

interface ResultBoxProps {
  title: string;
  content: string;
  showIndicators?: boolean;
  emoji?: string;
}

const CodeAnalysisHub: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [results, setResults] = useState<AnalysisResults | null>(null);
  const [error, setError] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile && selectedFile.name.endsWith('.py')) {
      setFile(selectedFile);
      setError('');
    } else {
      setError('Please select a Python (.py) file');
      setFile(null);
    }
  };

  const uploadFile = async () => {
    if (!file) {
      setError('Please select a file first');
      return;
    }

    setIsAnalyzing(true);
    setError('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data: AnalysisResults = await response.json();
      setResults(data);
    } catch (err) {
      setError(`Analysis failed: ${(err as Error).message}`);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const ResultBox: React.FC<ResultBoxProps> = ({ 
    title, 
    content, 
    showIndicators = false, 
    emoji = "📊" 
  }) => (
    <div className="response-box">
      <h2 className="response-box-title">
        <span className="response-box-emoji">{emoji}</span>
        {title}
      </h2>
      <pre className="response-box-content">
        {content}
      </pre>
      {showIndicators && (
        <div className="indicators-container">
          <span className="success-indicator">
            ✓ Tests Passed
          </span>
          <span className="fail-indicator">
            ✗ Issues Found
          </span>
        </div>
      )}
    </div>
  );

  return (
    <div className="app-container">
      <div className="animated-background" />
      
      <div className="floating-elements">
        <div className="floating-element floating-element-1" />
        <div className="floating-element floating-element-2" />
      </div>

      <div className="content-wrapper">
        <div className="chat-card">
          <div className="top-border-gradient" />

          <h1 className="chat-header">
            Code Analysis Hub
            <div className="header-underline" />
          </h1>

          <div className="message-box">
            <div className="message-icon">💡</div>
            Upload your Python file and get instant feedback with smart suggestions and automated fixes!
          </div>

          <div className="file-upload">
            <input
              ref={fileInputRef}
              type="file"
              accept=".py"
              onChange={handleFileChange}
              className="file-input"
            />
            <button
              onClick={uploadFile}
              disabled={isAnalyzing || !file}
              className={`upload-button ${isAnalyzing || !file ? 'disabled' : ''}`}
            >
              {isAnalyzing && <div className="loading-spinner" />}
              {isAnalyzing ? 'Analyzing...' : 'Analyze Code'}
            </button>
          </div>

          {error && (
            <div className="error-box">
              <div className="error-icon">⚠️</div>
              {error}
            </div>
          )}

          {results ? (
            <div className="results-container">
              <ResultBox 
                title="Syntax Check" 
                content={results.syntax_check}
                emoji="🔍"
              />
              
              <ResultBox 
                title="Code Style" 
                content={results.pylint_results}
                emoji="✨"
              />
              
              <ResultBox 
                title="Original Tests" 
                content={results.original_test_results}
                emoji="🧪"
              />
              
              <ResultBox 
                title="Suggestions" 
                content={results.logical_fix_explanation}
                emoji="💭"
              />
              
              <ResultBox 
                title="Fixed Code" 
                content={results.fixed_code}
                emoji="🔧"
              />
              
              <ResultBox 
                title="Fixed Tests" 
                content={results.fixed_test_results}
                emoji="✅"
              />
            </div>
          ) : (
            <div className="placeholder-results">
              <ResultBox 
                title="Analysis Results" 
                content="Your analysis results will appear here..."
                showIndicators={true}
              />
              
              <ResultBox 
                title="Code Quality" 
                content="Code style and quality metrics will be displayed here..."
                emoji="📈"
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CodeAnalysisHub;
import React, { useEffect, useState, useRef } from 'react';

interface LogsTerminalProps {
  onBack: () => void;
}

export const LogsTerminal: React.FC<LogsTerminalProps> = ({ onBack }) => {
  const [logs, setLogs] = useState<string[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  const fetchLogs = () => {
    fetch('http://localhost:8000/api/logs')
      .then(res => res.json())
      .then(data => setLogs(data.logs || []))
      .catch(err => console.error(err));
  };

  useEffect(() => {
    fetchLogs();
    // Auto-refresh logs every 3 seconds while viewing
    const interval = setInterval(fetchLogs, 3000);
    return () => clearInterval(interval);
  }, []);

  // Always scroll to the bottom when new logs arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  const clearLogs = async () => {
    const confirm = window.confirm("Are you sure you want to clear system logs?");
    if (confirm) {
      await fetch('http://localhost:8000/api/logs/clear', { method: 'POST' });
      fetchLogs();
    }
  };

  return (
    <div className="center-wrapper p-4 md:p-8">
      <div className="w-full max-w-3xl flex justify-between mb-4 text-xs font-mono drop-shadow-md">
        <button onClick={onBack} className="text-yellow-400 hover:text-white transition-colors">
          &lt; BACK TO TITLE
        </button>
      </div>

      <div className="magic-terminal">
        <div className="magic-terminal-header">
          <div className="terminal-dot dot-red" />
          <div className="terminal-dot dot-yellow" />
          <div className="terminal-dot dot-green" />
          <span className="ml-4 text-xs text-gray-400 font-mono">bash - ai_system_logs</span>
        </div>
        
        <div className="magic-terminal-body custom-scrollbar" ref={scrollRef}>
          {logs.length === 0 ? (
            <div className="text-gray-500 italic">No system logs recorded yet...</div>
          ) : (
            logs.map((log, index) => (
              <div key={index} className="mb-1 whitespace-pre-wrap break-words">
                <span className="text-[#3b8eea] font-bold mr-2">➜</span>
                {log}
              </div>
            ))
          )}
        </div>
      </div>

      <div className="mt-8">
        <button 
          onClick={clearLogs}
          className="retro-btn !bg-red-900 !border-red-500 !text-white text-xs hover:!bg-red-600"
        >
          CLEAR ALL LOGS
        </button>
      </div>
    </div>
  );
};
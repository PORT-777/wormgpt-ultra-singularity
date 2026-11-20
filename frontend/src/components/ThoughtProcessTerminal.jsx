import React, { useEffect, useRef } from 'react';

/**
 * ThoughtProcessTerminal
 * يعرض سلسلة العمليات (التركيز، تنفيذ الأدوات، الملاحظات) في شكل Terminal سينمائي.
 * @param {Array} logs - مصفوفة من الكائنات تحتوي على {type, message, timestamp}
 */
const ThoughtProcessTerminal = ({ logs }) => {
  const scrollRef = useRef(null);

  // التمرير التلقائي لأسفل عند إضافة سجلات جديدة
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  const getIcon = (type) => {
    switch (type) {
      case 'thought': return '🧠';
      case 'tool': return '🛠️';
      case 'observation': return '🔍';
      case 'error': return '❌';
      case 'success': return '✅';
      default: return '⚙️';
    }
  };

  const getTextColor = (type) => {
    switch (type) {
      case 'error': return 'text-red-500';
      case 'success': return 'text-green-500';
      case 'tool': return 'text-red-400';
      case 'thought': return 'text-red-200';
      default: return 'text-gray-400';
    }
  };

  return (
    <div className="flex flex-col h-full w-full bg-[#050505] border border-[#8B0000] rounded-lg overflow-hidden font-mono text-xs shadow-[0_0_20px_rgba(204,0,0,0.2)]">
      {/* Header */}
      <div className="bg-[#0A0A0A] px-4 py-2 border-b border-[#8B0000] flex justify-between items-center">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-[#CC0000] animate-pulse"></div>
          <span className="text-[#FF4444] font-bold tracking-widest uppercase text-[10px]">
            Intelligence Engine Core
          </span>
        </div>
        <span className="text-[#8B0000] text-[10px]">STATUS: ACTIVE</span>
      </div>

      {/* Terminal Content */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-2 scrollbar-thin scrollbar-thumb-[#8B0000] scrollbar-track-[#050505]"
      >
        {logs.length === 0 && (
          <div className="text-[#444] italic text-center mt-10">Waiting for intelligence stream...</div>
        )}

        {logs.map((log, index) => (
          <div key={index} className="flex gap-3 animate-in fade-in slide-in-from-left-2 duration-300">
            <span className="text-[#444] shrink-0">
              [{new Date(log.timestamp).toLocaleTimeString([], {hour12: false, hour: '2-digit', minute:'2-digit', second:'2-digit'})}]
            </span>
            <span className="shrink-0">{getIcon(log.type)}</span>
            <span className={`${getTextColor(log.type)} break-all leading-relaxed`}>
              {log.message}
            </span>
          </div>
        ))}
      </div>

      {/* Footer/Status Bar */}
      <div className="bg-[#0A0A0A] px-4 py-1 border-t border-[#8B0000] text-[9px] text-[#444] flex justify-between">
        <span>CPU: 12%</span>
        <span>MEMORY: 1.4GB</span>
        <span>LATENCY: 24ms</span>
      </div>
    </div>
  );
};

export default ThoughtProcessTerminal;
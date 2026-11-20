import React, { useState, useEffect, useCallback, useRef } from 'react';
import Icon from './Icon.jsx';
import { t } from '../ui/i18n.js';

const API_BASE = '/api';

/**
 * WorkspacePanel Component
 * Man: Advanced File System & Terminal Interface
 */
export default function WorkspacePanel({ notify }) {
  const [workspaces, setWorkspaces] = useState([]);
  const [activeWs, setActiveWs] = useState(null);
  const [currentDir, setCurrentDir] = useState('/');
  const [fileList, setFileList] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
  const [cmdInput, setCmdInput] = useState('');
  const [cmdOutput, setCmdOutput] = useState('');
  const [loading, setLoading] = useState(true);
  const [tree, setTree] = useState("");

  // API Helper
  const api = useCallback(async (path, opts = {}) => {
    const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
    const tok = localStorage.getItem("🔥😈 PORT 777 EVIL ☠️👹_token");
    if (tok) headers.Authorization = `Bearer ${tok}`;
    
    const res = await fetch(path, { ...opts, headers });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || errData.message || `HTTP ${res.status}`);
    }
    return res.json();
  }, []);

  // Load Workspaces
  const loadWorkspaces = useCallback(async () => {
    try {
      const data = await api("/api/workspace/list");
      setWorkspaces(data.workspaces || []);
    } catch (e) {
      notify("فشل تحميل مساحات العمل", "error");
    } finally {
      setLoading(false);
    }
  }, [api, notify]);

  useEffect(() => { loadWorkspaces(); }, [loadWorkspaces]);

  // Directory Navigation
  const browseDir = async (wsId, dir) => {
    setIsBusy(true);
    try {
      const data = await api("/api/workspace/files/list", {
        method: "POST",
        body: JSON.stringify({ workspace_id: wsId, directory: dir })
      });
      setFileList(data.items || []);
      setCurrentDir(dir);
      // Update tree view
      const treeData = await api("/api/workspace/tree", {
        method: "POST",
        body: JSON.stringify({ workspace_id: wsId, directory: dir, max_depth: 3 })
      });
      setTree(treeData.tree || "");
    } catch (e) {
      notify("فشل التصفح", "error");
    } finally {
      setIsBusy(false);
    }
  };

  const selectWorkspace = async (wsId) => {
    setIsBusy(true);
    setActiveWs(wsId);
    try {
      await browseDir(wsId, '/');
    } catch (e) {
      notify("فشل اختيار المساحة", "error");
    } finally {
      setIsBusy(false);
    }
  };

  // File Operations
  const openFile = async (wsId, path) => {
    setIsBusy(true);
    try {
      const data = await api("/api/workspace/files/read", {
        method: "POST",
        body: JSON.stringify({ workspace_id: wsId, file_path: path })
      });
      setSelectedFile(path);
      setFileContent(data.content || '');
      setIsEditing(false);
    } catch (e) {
      notify("فشل فتح الملف", "error");
    } finally {
      setIsBusy(false);
    }
  };

  const saveFile = async () => {
    if (!selectedFile || !activeWs) return;
    setIsBusy(true);
    try {
      await api("/api/workspace/files/write", {
method: "POST",
        body: JSON.stringify({ workspace_id: activeWs, file_path: selectedFile, content: fileContent })
      });
      notify("تم الحفظ", "ok");
      setIsEditing(false);
      await browseDir(activeWs, currentDir);
    } catch (e) {
      notify("فشل الحفظ", "error");
    } finally {
      setIsBusy(false);
    }
  };

  // Terminal
  const runCommand = async (e) => {
    if (e.key !== 'Enter' || !cmdInput.trim()) return;
    const cmd = cmdInput;
    setCmdInput('');
    setCmdOutput(prev => prev + `\n> ${cmd}\n`);
    setIsBusy(true);
    try {
      const data = await api("/api/workspace/command/execute", {
        method: "POST",
        body: JSON.stringify({ workspace_id: activeWs, command: cmd, cwd: currentDir })
      });
      setCmdOutput(prev => prev + data.stdout + (data.stderr ? `\n[ERR] ${data.stderr}` : ''));
    } catch (err) {
      setCmdOutput(prev => prev + `\n[ERR] ${err.message}\n`);
    } finally {
      setIsBusy(false);
    }
  };

  if (loading) return <div className="p-4 text-red-500 animate-pulse">Loading...</div>;

  return (
    <div className="flex h-full w-full bg-[#0A0A0A] text-gray-300 font-mono text-xs overflow-hidden border-l border-[#8B0000]">
      {/* Left Sidebar: Workspaces */}
      <div className="w-48 flex flex-col border-r border-[#222] bg-[#050505]">
        <div className="p-3 border-b border-[#222] text-[#FF4444] font-bold uppercase text-[10px]">Workspaces</div>
        <div className="flex-1 overflow-y-auto">
          {workspaces.map(ws => (
            <div 
              key={ws.workspace_id}
              onClick={() => selectWorkspace(ws.workspace_id)}
              className={`px-3 py-2 cursor-pointer hover:bg-[#1A1A1A] transition-colors ${activeWs === ws.workspace_id ? 'bg-[#CC0000]/20 text-[#FF4444] border-l-2 border-[#CC0000]' : ''}`}
            >
              <Icon name="folder" size={12} className="inline mr-2" />
              <span className="truncate">{ws.workspace_id}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Center: File Browser & Editor */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {activeWs ? (
          <>
            {/* File Explorer Breadcrumb/List */}
            <div className="h-10 bg-[#0D0D0D] border-b border-[#222] flex items-center px-4 justify-between text-[11px]">
              <div className="text-gray-500">Path: <span className="text-gray-300">{currentDir}</span></div>
              <div className="flex gap-2">
                <button onClick={() => browseDir(activeWs, '..')} className="hover:text-white">Parent</button>
                <button onClick={() => browseDir(activeWs, currentDir)} className="hover:text-white">Refresh</button>
              </div>
            </div>

            <div className="flex-1 flex overflow-hidden">
              {/* File List Column */}
              <div className="w-56 border-r border-[#222] bg-[#0A0A0A] overflow-y-auto">
                {fileList.map(file => (
                  <div 
                    key={file.name}
                    onClick={() => file.type === 'directory' ? browseDir(activeWs, file.name) : openFile(activeWs, file.name)}
                    className={`px-4 py-1.5 flex items-center gap-2 cursor-pointer hover:bg-[#1A1A1A] ${selectedFile === file.name ? 'bg-[#CC0000]/10 text-[#FF4444]' : ''}`}
                  >
                    <Icon name={file.type === 'directory' ? 'folder' : 'file'} size={14} className={file.type === 'directory' ? 'text-blue-400' : 'text-gray-500'} />
                    <span className="truncate">{file.name}</span>
                  </div>
                ))}
              </div>

              {/* Editor Column */}
              <div className="flex-1 flex flex-col bg-[#050505]">
                {selectedFile ? (
                  <>
                    <div className="p-2 border-b border-[#222] flex justify-between items-center bg-[#0A0A0A]">
                      <span className="text-[#FF4444] text-[11px]">{selectedFile}</span>
                      {isEditing ? (
                        <button onClick={saveFile} className="bg-[#CC0000] text-white px-3 py-0.5 rounded text-[10px]">Save</button>
                      ) : (
                        <button onClick={() => setIsEditing(true)} className="bg-[#222] px-3 py-0.5 rounded text-[10px]">Edit</button>
                      )}
                    </div>
                    <div className="flex-1 overflow-auto">
                      {isEditing ? (
                        <textarea
                          className="w-full h-full bg-transparent p-4 outline-none text-gray-300 resize-none font-mono text-sm"
                          value={fileContent}
                          onChange={(e) => setFileContent(e.target.value)}
                        />
                      ) : (
                        <pre className="p-4 text-sm text-gray-300 whitespace-pre-wrap font-mono">{fileContent}</pre>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="flex-1 flex items-center justify-center text-gray-600 italic text-xs">
                    Select a file to view/edit
                  </div>
                )}
              </div>
            </div>

            {/* Terminal Area */}
            <div className="h-48 border-t border-[#8B0000] bg-[#000] flex flex-col">
              <div className="px-3 py-1 bg-[#0A0A0A] border-b border-[#222] text-[10px] text-[#8B0000] font-bold uppercase">Terminal</div>
              <div className="flex-1 overflow-y-auto p-2 font-mono text-[11px]">
                {cmdOutput && <pre className="text-green-500 whitespace-pre-wrap">{cmdOutput}</pre>}
              </div>
              <div className="p-2 bg-[#0A0A0A] flex items-center gap-2">
                <span className="text-[#CC0000] font-bold">❯</span>
                <input
                  className="flex-1 bg-transparent outline-none text-white text-xs"
                  value={cmdInput}
                  onChange={(e) => setCmdInput(e.target.value)}
                  onKeyDown={runCommand}
                  placeholder="Execute shell command..."
                  disabled={!activeWs || isBusy}
                />
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-600 italic text-sm">
            No workspace active. Please attach a directory.
          </div>
        )}
      </div>
    </div>
  );
}
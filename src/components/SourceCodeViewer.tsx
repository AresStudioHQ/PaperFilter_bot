import React, { useState, useEffect } from 'react';
import { Copy, Check, Download, ShieldCheck, Cpu, Database, Globe, Key, FileText, FileCode } from 'lucide-react';

export const SourceCodeViewer: React.FC = () => {
  const [files, setFiles] = useState<Record<string, string>>({});
  const [selectedFile, setSelectedFile] = useState<string>('bot.py');
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/files')
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          setFiles(data.files);
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const fileMeta: Record<string, { desc: string; icon: any; tag: string }> = {
    'bot.py': { desc: 'Telegram Bot 主程式與 Webhook/OAuth2 回呼服務', icon: Cpu, tag: '主入口' },
    'search_engine.py': { desc: 'arXiv + PubMed + Semantic Scholar + CrossRef 全球 4 大庫檢索引擎與 AI 導讀', icon: FileCode, tag: '搜尋核心' },
    'gdrive_sync.py': { desc: 'Google Drive OAuth2 授權、雙軌筆記與 references.bib 雲端維護', icon: Key, tag: '雲端歸檔' },
    'database.py': { desc: 'SQLite/Turso 14張資料表架構與使用者偏好/配額/快取/文獻庫管理器', icon: Database, tag: '資料持久層' },
    'requirements.txt': { desc: 'Python 執行環境與相關套件相依性清單', icon: FileText, tag: '相依套件' },
    'README.md': { desc: '完整專案架構說明、本機測試與 Render 雲端部署指南', icon: FileText, tag: '說明文件' },
    '.env.example': { desc: '環境變數設定範本 (Token / API Keys / OAuth)', icon: Key, tag: '環境配置' },
  };

  const handleCopyCode = () => {
    const code = files[selectedFile] || '';
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = (fileName: string, content: string) => {
    const element = document.createElement('a');
    const file = new Blob([content], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = fileName;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <div className="space-y-6">
      {/* Overview Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <span className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <ShieldCheck className="w-4 h-4" />
            </span>
            <h2 className="text-xl font-bold text-white">PaperFilterBot 雲端系統後端架構</h2>
          </div>
          <p className="text-xs text-slate-400">
            Render 雲端服務與本機同步執行的 Python 微服務模組清單。
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => {
              Object.entries(files).forEach(([name, content]) => {
                handleDownload(name, String(content));
              });
            }}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold flex items-center space-x-1.5 shadow-md shadow-indigo-600/30 transition-colors cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" />
            <span>下載所有後端原始檔案</span>
          </button>
        </div>
      </div>

      {/* Code Browser Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* File Selector Sidebar */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 space-y-1.5 h-fit">
          <span className="text-xs font-bold text-slate-400 px-2 py-1 block">後端模組清單</span>
          {Object.keys(fileMeta).map((fileName) => {
            const meta = fileMeta[fileName];
            const Icon = meta?.icon || FileCode;
            const isSelected = selectedFile === fileName;
            return (
              <button
                key={fileName}
                onClick={() => setSelectedFile(fileName)}
                className={`w-full text-left p-2.5 rounded-lg text-xs font-medium transition-all flex items-center justify-between cursor-pointer ${
                  isSelected
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-300 hover:bg-slate-800'
                }`}
              >
                <div className="flex items-center space-x-2 truncate">
                  <Icon className="w-3.5 h-3.5 shrink-0" />
                  <span className="truncate font-mono">{fileName}</span>
                </div>
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${isSelected ? 'bg-indigo-700 text-white' : 'bg-slate-800 text-slate-400'}`}>
                  {meta?.tag}
                </span>
              </button>
            );
          })}
        </div>

        {/* Code Content Area */}
        <div className="lg:col-span-3 bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl flex flex-col">
          <div className="p-4 border-b border-slate-800 bg-slate-850 flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="flex items-center space-x-2">
                <span className="font-mono text-sm font-bold text-white">{selectedFile}</span>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                  {fileMeta[selectedFile]?.tag}
                </span>
              </div>
              <p className="text-xs text-slate-400">{fileMeta[selectedFile]?.desc}</p>
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={handleCopyCode}
                className="flex items-center space-x-1 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs border border-slate-700 transition-colors cursor-pointer"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? '已複製' : '複製代碼'}</span>
              </button>
              <button
                onClick={() => handleDownload(selectedFile, files[selectedFile] || '')}
                className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs border border-slate-700 transition-colors cursor-pointer"
                title="下載此檔案"
              >
                <Download className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="p-4 bg-slate-950 overflow-x-auto max-h-[600px] overflow-y-auto">
            {loading ? (
              <div className="py-20 text-center text-slate-500 text-xs">載入檔案中...</div>
            ) : (
              <pre className="font-mono text-xs text-slate-200 leading-relaxed select-all">
                {files[selectedFile] || '檔案內容為空'}
              </pre>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

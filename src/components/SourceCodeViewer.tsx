import React, { useState, useEffect } from 'react';
import { Copy, Check, Download, ShieldCheck, Cpu, Database, Globe, Key, FileText, FileCode } from 'lucide-react';
import { useI18n } from '../i18n';

export const SourceCodeViewer: React.FC<{ userLang?: string }> = ({ userLang = 'en' }) => {
  const { t } = useI18n(userLang);
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
    'bot.py': { desc: t('source_file_bot_desc'), icon: Cpu, tag: t('source_file_bot_tag') },
    'search_engine.py': { desc: t('source_file_search_desc'), icon: FileCode, tag: t('source_file_search_tag') },
    'gdrive_sync.py': { desc: t('source_file_gdrive_desc'), icon: Key, tag: t('source_file_gdrive_tag') },
    'database.py': { desc: t('source_file_db_desc'), icon: Database, tag: t('source_file_db_tag') },
    'requirements.txt': { desc: t('source_file_req_desc'), icon: FileText, tag: t('source_file_req_tag') },
    'README.md': { desc: t('source_file_readme_desc'), icon: FileText, tag: t('source_file_readme_tag') },
    '.env.example': { desc: t('source_file_env_desc'), icon: Key, tag: t('source_file_env_tag') },
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
            <h2 className="text-xl font-bold text-white">{t('source_title')}</h2>
          </div>
          <p className="text-xs text-slate-400">
            {t('source_sub')}
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
            <span>{t('source_btn_download')}</span>
          </button>
        </div>
      </div>

      {/* Code Browser Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* File Selector Sidebar */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 space-y-1.5 h-fit">
          <span className="text-xs font-bold text-slate-400 px-2 py-1 block">{t('source_sidebar_title')}</span>
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
                <span>{copied ? t('source_copied') : t('source_copy')}</span>
              </button>
              <button
                onClick={() => handleDownload(selectedFile, files[selectedFile] || '')}
                className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs border border-slate-700 transition-colors cursor-pointer"
                title={t('source_download_tooltip')}
              >
                <Download className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="p-4 bg-slate-950 overflow-x-auto max-h-[600px] overflow-y-auto">
            {loading ? (
              <div className="py-20 text-center text-slate-500 text-xs">{t('source_loading')}</div>
            ) : (
              <pre className="font-mono text-xs text-slate-200 leading-relaxed select-all">
                {files[selectedFile] || t('source_empty')}
              </pre>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

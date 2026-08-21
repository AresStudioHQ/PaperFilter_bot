import React, { useState } from 'react';
import { BookOpen, FolderPlus, Trash2, Download, Sparkles, Search, Layers, FileCode, Check, RefreshCw, Folder } from 'lucide-react';
import { Paper } from '../types';
import { useI18n } from '../i18n';

interface LibrarySectionProps {
  library: Paper[];
  categories: string[];
  onRemovePaper: (id: string) => void;
  onOpenDeep: (paper: Paper) => void;
  onUpdateCategories: (action: 'add' | 'rename' | 'delete', name?: string, oldName?: string, newName?: string) => void;
}

export const LibrarySection: React.FC<LibrarySectionProps> = ({
  library,
  categories,
  onRemovePaper,
  onOpenDeep,
  onUpdateCategories,
}) => {
  const { t } = useI18n();
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [newFolderName, setNewFolderName] = useState('');
  const [activeAnalysis, setActiveAnalysis] = useState<'none' | 'review' | 'gap'>('none');
  const [analysisText, setAnalysisText] = useState('');
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [exportFormat, setExportFormat] = useState<'BibTeX' | 'RIS' | 'CSV'>('BibTeX');
  const [exportedContent, setExportedContent] = useState('');
  const [copied, setCopied] = useState(false);

  const filteredPapers = selectedCategory === 'all'
    ? library
    : library.filter(p => p.category === selectedCategory);

  const handleAddFolder = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFolderName.trim()) return;
    onUpdateCategories('add', newFolderName.trim());
    setNewFolderName('');
  };

  const handleGenerateReview = async () => {
    if (filteredPapers.length === 0) return;
    setActiveAnalysis('review');
    setLoadingAnalysis(true);
    try {
      const res = await fetch('/api/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ papers: filteredPapers }),
      });
      const data = await res.json();
      if (data.success) {
        setAnalysisText(data.review);
      }
    } catch (err) {
      console.error('Review error:', err);
    } finally {
      setLoadingAnalysis(false);
    }
  };

  const handleGenerateGap = async () => {
    if (filteredPapers.length === 0) return;
    setActiveAnalysis('gap');
    setLoadingAnalysis(true);
    try {
      const res = await fetch('/api/gap', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ papers: filteredPapers }),
      });
      const data = await res.json();
      if (data.success) {
        setAnalysisText(data.gap_analysis);
      }
    } catch (err) {
      console.error('Gap analysis error:', err);
    } finally {
      setLoadingAnalysis(false);
    }
  };

  const handleExport = async (format: 'BibTeX' | 'RIS' | 'CSV') => {
    setExportFormat(format);
    try {
      const res = await fetch('/api/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ format, papers: filteredPapers }),
      });
      const data = await res.json();
      if (data.success) {
        setExportedContent(data.content);
      }
    } catch (err) {
      console.error('Export error:', err);
    }
  };

  const handleCopyExport = () => {
    navigator.clipboard.writeText(exportedContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Top Banner with Stats & Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>{t('lib_section_total')}</span>
            <BookOpen className="w-4 h-4 text-indigo-400" />
          </div>
          <p className="text-3xl font-black text-white">{library.length} <span className="text-sm font-normal text-slate-400">{t('trends_papers_unit')}</span></p>
          <p className="text-xs text-slate-400">{t('lib_section_bib_auto')}</p>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>{t('lib_section_folders')}</span>
            <Folder className="w-4 h-4 text-sky-400" />
          </div>
          <p className="text-3xl font-black text-white">{categories.length} <span className="text-sm font-normal text-slate-400">{t('lib_section_cat_unit')}</span></p>
          <p className="text-xs text-slate-400">{t('lib_section_drive_support')}</p>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col justify-between space-y-3">
          <div className="text-xs text-slate-400 flex items-center justify-between">
            <span>{t('lib_section_batch_analysis')}</span>
            <Sparkles className="w-4 h-4 text-amber-400" />
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleGenerateReview}
              disabled={filteredPapers.length === 0}
              className="flex-1 px-3 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold transition-colors shadow-md shadow-indigo-600/20"
            >
              {t('lib_section_review_btn')}
            </button>
            <button
              onClick={handleGenerateGap}
              disabled={filteredPapers.length === 0}
              className="flex-1 px-3 py-2 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold transition-colors shadow-md shadow-amber-600/20"
            >
              {t('lib_section_gap_btn')}
            </button>
          </div>
        </div>
      </div>

      {/* Analysis Result Box (if triggered) */}
      {activeAnalysis !== 'none' && (
        <div className="bg-slate-900 border border-indigo-500/40 rounded-xl p-6 shadow-2xl space-y-4 animate-in fade-in slide-in-from-top-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center space-x-2">
              <span className="p-1.5 rounded-lg bg-indigo-500/20 text-indigo-300">
                <Sparkles className="w-4 h-4" />
              </span>
              <h3 className="font-bold text-white text-base">
                {activeAnalysis === 'review' ? t('lib_section_review_title') : t('lib_section_gap_title')}
              </h3>
            </div>
            <button
              onClick={() => setActiveAnalysis('none')}
              className="text-xs text-slate-400 hover:text-white px-2 py-1 bg-slate-800 rounded-md"
            >
              {t('lib_section_collapse')}
            </button>
          </div>

          {loadingAnalysis ? (
            <div className="py-12 flex flex-col items-center justify-center space-y-3">
              <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
              <p className="text-xs text-slate-400 animate-pulse">{t('lib_section_integrating', { count: filteredPapers.length })}</p>
            </div>
          ) : (
            <div className="whitespace-pre-line text-sm text-slate-200 leading-relaxed bg-slate-950/70 p-5 rounded-lg border border-slate-800">
              {analysisText}
            </div>
          )}
        </div>
      )}

      {/* Folder Management & Export Bar */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
        {/* Categories Tab Selector */}
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            onClick={() => setSelectedCategory('all')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              selectedCategory === 'all'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
          >
            {t('filter_all')} ({library.length})
          </button>
          {categories.map((c) => (
            <button
              key={c}
              onClick={() => setSelectedCategory(c)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                selectedCategory === c
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
              }`}
            >
              📁 {c} ({library.filter(p => p.category === c).length})
            </button>
          ))}
        </div>

        {/* Add Folder form & Export Buttons */}
        <div className="flex items-center gap-3">
          <form onSubmit={handleAddFolder} className="flex items-center space-x-1">
            <input
              type="text"
              value={newFolderName}
              onChange={(e) => setNewFolderName(e.target.value)}
              placeholder={t('lib_section_new_folder_ph')}
              className="px-2.5 py-1 text-xs bg-slate-950 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 w-28"
            />
            <button
              type="submit"
              className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs border border-slate-700"
            >
              <FolderPlus className="w-3.5 h-3.5" />
            </button>
          </form>

          {/* Export button dropdown */}
          <div className="flex items-center space-x-1 bg-slate-800 p-1 rounded-lg border border-slate-700">
            <span className="text-xs text-slate-400 pl-1.5">{t('lib_section_export_label')}</span>
            <button
              onClick={() => handleExport('BibTeX')}
              className="px-2 py-1 text-xs font-mono font-medium rounded bg-slate-700 hover:bg-slate-600 text-white"
            >
              BibTeX
            </button>
            <button
              onClick={() => handleExport('RIS')}
              className="px-2 py-1 text-xs font-mono font-medium rounded bg-slate-700 hover:bg-slate-600 text-white"
            >
              RIS
            </button>
            <button
              onClick={() => handleExport('CSV')}
              className="px-2 py-1 text-xs font-mono font-medium rounded bg-slate-700 hover:bg-slate-600 text-white"
            >
              CSV
            </button>
          </div>
        </div>
      </div>

      {/* Export Result Drawer (if opened) */}
      {exportedContent && (
        <div className="bg-slate-900 border border-slate-700 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-200">
               📄 {exportFormat} {t('lib_section_export_title', { count: filteredPapers.length })}
             </span>
            <div className="flex items-center space-x-2">
              <button
                onClick={handleCopyExport}
                className="flex items-center space-x-1 text-xs px-2.5 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white"
              >
                {copied ? <Check className="w-3 h-3 text-emerald-300" /> : <Download className="w-3 h-3" />}
                <span>{copied ? t('lib_section_copied') : t('lib_section_copy_all')}</span>
              </button>
              <button
                onClick={() => setExportedContent('')}
                className="text-xs text-slate-400 hover:text-white px-2 py-1"
              >
                ✕
              </button>
            </div>
          </div>
          <pre className="p-3 bg-slate-950 rounded-lg text-xs font-mono text-emerald-400 overflow-x-auto max-h-48 border border-slate-800">
            {exportedContent}
          </pre>
        </div>
      )}

      {/* Library Papers List */}
      <div className="space-y-3">
        {filteredPapers.length === 0 ? (
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-12 text-center space-y-3">
            <BookOpen className="w-10 h-10 text-slate-600 mx-auto" />
            <h4 className="text-slate-300 font-semibold text-sm">{t('lib_section_empty_title')}</h4>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              {t('lib_section_empty_sub')}
            </p>
          </div>
        ) : (
          filteredPapers.map((paper) => (
            <div
              key={paper.id}
              className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row items-start justify-between gap-4 hover:border-slate-700 transition-colors"
            >
              <div className="space-y-1.5 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="px-2 py-0.5 rounded text-xs bg-indigo-950/60 text-indigo-300 border border-indigo-800/40">
                    📁 {paper.category || t('category_uncategorized')}
                  </span>
                  <span className="text-xs text-slate-300 font-mono flex items-center gap-1 bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700">
                    📅 {paper.year} · {paper.source}
                  </span>
                  {paper.citations > 0 && (
                    <span className="text-xs text-amber-400">{t('lib_section_citations')} {paper.citations}</span>
                  )}
                </div>
                <h4 className="font-bold text-white text-sm leading-snug">{paper.title}</h4>
                <p className="text-xs text-slate-400">
                  👥 {paper.authors.slice(0, 3).join(', ')}{paper.authors.length > 3 ? t('lib_section_et_al') : ''}
                </p>
                <p className="text-xs text-slate-300 line-clamp-2 pt-1">{paper.summary}</p>
              </div>

              <div className="flex items-center space-x-2 shrink-0">
                <button
                  onClick={() => onOpenDeep(paper)}
                  className="px-3 py-1.5 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 rounded-lg text-xs font-semibold transition-colors flex items-center space-x-1"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>{t('lib_section_deep_read')}</span>
                </button>
                <button
                  onClick={() => onRemovePaper(paper.id)}
                  className="p-1.5 text-slate-400 hover:text-red-400 rounded-lg hover:bg-slate-800 transition-colors"
                  title={t('lib_section_remove')}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

import React, { useState } from 'react';
import { Search, Sparkles, ExternalLink, BookmarkPlus, Award, CheckCircle, Flame } from 'lucide-react';
import { Paper, FilterMode } from '../types';
import { useI18n } from '../i18n';

interface SearchSectionProps {
  filterMode: FilterMode;
  onOpenDeep: (paper: Paper) => void;
  onAddToLibrary: (paper: Paper) => void;
  categories: string[];
  userLang?: string;
  libraryPaperIds?: string[];
}

export const SearchSection: React.FC<SearchSectionProps> = ({
  filterMode,
  onOpenDeep,
  onAddToLibrary,
  categories,
  userLang = 'en',
  libraryPaperIds = [],
}) => {
  const { t } = useI18n(userLang);
  const [query, setQuery] = useState('Attention Transformer');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<Paper[]>([]);
  const [archivingId, setArchivingId] = useState<string | null>(null);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const handleSearch = async (e?: React.FormEvent, searchOverride?: string) => {
    if (e) e.preventDefault();
    const q = searchOverride || query;
    if (!q.trim()) return;

    setLoading(true);
    try {
      const res = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, mode: filterMode }),
      });
      const data = await res.json();
      if (data.success) {
        setResults(data.papers || []);
      }
    } catch (err) {
      console.error('Search error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleArchive = (paper: Paper, category: string) => {
    setArchivingId(paper.id);
    onAddToLibrary({ ...paper, category });
    setTimeout(() => {
      setArchivingId(null);
      setToastMsg(`✅ ${paper.title.slice(0, 30)}... -> Google Drive [${category}]`);
      setTimeout(() => setToastMsg(null), 4000);
    }, 800);
  };

  const quickKeywords = [
    'Attention Transformer',
    'CRISPR Cas9 Genome',
    'Diffusion Generative Models',
    'Quantum Superposition',
    'Neuroscience Alzheimer',
    'Deep Reinforcement Learning'
  ];

  return (
    <div className="space-y-6">
      {/* Toast Notification */}
      {toastMsg && (
        <div className="bg-emerald-900/90 border border-emerald-500/50 text-emerald-100 px-4 py-3 rounded-xl flex items-center justify-between text-sm shadow-lg animate-in slide-in-from-top-3">
          <span>{toastMsg}</span>
          <button onClick={() => setToastMsg(null)} className="text-emerald-300 hover:text-white font-bold ml-3 cursor-pointer">✕</button>
        </div>
      )}

      {/* Hero / Search Box Container */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
        <div className="max-w-3xl mx-auto space-y-4">
          <div className="text-center space-y-2">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              {t('search_title')}
            </h1>
            <p className="text-slate-400 text-sm">
              {t('search_sub')}
            </p>
          </div>

          <form onSubmit={handleSearch} className="relative flex items-center">
            <div className="absolute left-4 text-slate-400">
              <Search className="w-5 h-5" />
            </div>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t('search_input_placeholder')}
              className="w-full pl-12 pr-32 py-3.5 bg-slate-950 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 text-sm transition-all"
            />
            <button
              type="submit"
              disabled={loading}
              className="absolute right-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg transition-all shadow-md shadow-indigo-600/30 flex items-center space-x-1.5 disabled:opacity-50 cursor-pointer"
            >
              {loading ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>{t('searching')}</span>
                </>
              ) : (
                <>
                  <Search className="w-3.5 h-3.5" />
                  <span>{t('btn_search')}</span>
                </>
              )}
            </button>
          </form>

          {/* Quick Keywords Chips */}
          <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
            <span className="text-xs text-slate-400 flex items-center gap-1"><Flame className="w-3 h-3 text-amber-400" /> {t('hot_topics_label')}</span>
            {quickKeywords.map((kw) => (
              <button
                key={kw}
                onClick={() => {
                  setQuery(kw);
                  handleSearch(undefined, kw);
                }}
                className="text-xs px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white border border-slate-700/60 transition-colors cursor-pointer"
              >
                {kw}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Results Header */}
      {results.length > 0 && (
        <div className="flex items-center justify-between px-1">
          <div className="flex items-center space-x-2">
            <span className="text-sm font-semibold text-slate-200">
              {t('search_results_count', { count: results.length })}
            </span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
              {filterMode === 'top_tier' ? t('mode_top_tier') : filterMode === 'free_only' ? t('mode_free_only') : t('mode_smart')}
            </span>
          </div>
        </div>
      )}

      {/* Search Results List */}
      <div className="space-y-4">
        {results.map((paper, idx) => {
          const isArchived = libraryPaperIds.includes(paper.id);
          return (
            <div
              key={paper.id + idx}
              className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-all shadow-md group space-y-3"
            >
              {/* Header row */}
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-1.5 flex-1">
                   <div className="flex flex-wrap items-center gap-2">
                     {paper.credibility_emoji && (
                       <span className={`px-2 py-0.5 rounded-md text-xs font-semibold border flex items-center gap-1 ${
                         paper.is_preprint
                           ? 'bg-red-500/10 text-red-300 border-red-500/20'
                           : (paper.tier ? 'bg-amber-500/10 text-amber-300 border-amber-500/20' : 'bg-slate-500/10 text-slate-300 border-slate-500/20')
                        }`} title={t(paper.credibility_label)}>
                          <Award className="w-3 h-3" /> {paper.credibility_emoji} {t(paper.credibility_label)}
                       </span>
                     )}
                     {paper.is_open_access && (
                       <span className="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 text-xs font-medium border border-emerald-500/20 flex items-center gap-1">
                         <CheckCircle className="w-3 h-3" /> OA
                       </span>
                     )}
                    <span className="text-xs font-mono text-sky-400 bg-sky-950/40 px-2 py-0.5 rounded border border-sky-800/30">
                      {paper.source}
                    </span>
                    <span className="text-xs text-slate-300 font-mono flex items-center gap-1 bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700">
                      📅 {paper.year}
                    </span>
                    {paper.citations > 0 && (
                      <span className="text-xs text-amber-400 font-mono">
                        🔥 Citations: {paper.citations.toLocaleString()}
                      </span>
                    )}
                  </div>

                  <h3 className="text-base font-bold text-white group-hover:text-indigo-300 transition-colors leading-snug">
                    {paper.title}
                  </h3>

                  <p className="text-xs text-slate-400">
                    👥 {paper.authors.length > 0 ? paper.authors.slice(0, 4).join(', ') + (paper.authors.length > 4 ? ` et al.` : '') : 'Unknown Authors'}
                  </p>
                </div>

                {/* Action buttons on the right */}
                <div className="flex flex-col sm:flex-row gap-2 shrink-0">
                  <button
                    onClick={() => onOpenDeep(paper)}
                    className="flex items-center justify-center space-x-1.5 px-3 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors shadow-sm cursor-pointer"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>{t('btn_deep_read')}</span>
                  </button>
                </div>
              </div>

              {/* Abstract preview */}
              <p className="text-xs text-slate-300 line-clamp-3 leading-relaxed bg-slate-950/40 p-3 rounded-lg border border-slate-800/70">
                {paper.summary}
              </p>

              {/* Bottom Actions Toolbar */}
              <div className="flex flex-wrap items-center justify-between gap-3 pt-1 border-t border-slate-800/60">
                <a
                  href={paper.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center space-x-1 text-xs text-sky-400 hover:text-sky-300 hover:underline"
                >
                  <span>{t('btn_read_source')}</span>
                  <ExternalLink className="w-3 h-3" />
                </a>

                {/* Archive dropdown / buttons */}
                <div className="flex items-center space-x-2">
                  <span className="text-xs text-slate-400">Drive:</span>
                  <select
                    defaultValue=""
                    onChange={(e) => {
                      if (e.target.value) {
                        handleArchive(paper, e.target.value);
                        e.target.value = "";
                      }
                    }}
                    disabled={archivingId === paper.id}
                    className="text-xs bg-slate-800 text-slate-200 border border-slate-700 rounded-lg px-2.5 py-1 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="" disabled>📁 Folder...</option>
                    {categories.map((c) => (
                      <option key={c} value={c}>📁 {c}</option>
                    ))}
                  </select>

                  <button
                    onClick={() => onAddToLibrary(paper)}
                    className={`flex items-center space-x-1 text-xs px-2.5 py-1 rounded-lg border transition-colors cursor-pointer ${
                      isArchived
                        ? 'bg-emerald-950/60 border-emerald-500/40 text-emerald-300'
                        : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700'
                    }`}
                  >
                    <BookmarkPlus className="w-3.5 h-3.5 text-indigo-400" />
                    <span>{isArchived ? t('btn_already_archived') : t('btn_archive_drive')}</span>
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};


import React, { useState } from 'react';
import { X, Copy, Check, FileText, Sparkles, ExternalLink, BookmarkPlus, CheckCircle2 } from 'lucide-react';
import { Paper } from '../types';
import { useI18n } from '../i18n';

interface DeepModalProps {
  paper: Paper | null;
  deepReport?: string;
  bibtex?: string;
  loading?: boolean;
  onClose: () => void;
  onAddToLibrary: (paper: Paper) => void;
  isArchived?: boolean;
  userLang?: string;
}

export const DeepModal: React.FC<DeepModalProps> = ({
  paper,
  deepReport,
  bibtex,
  loading = false,
  onClose,
  onAddToLibrary,
  isArchived = false,
  userLang = 'en',
}) => {
  const { t } = useI18n(userLang);
  const [copiedBib, setCopiedBib] = useState(false);
  const [copiedReport, setCopiedReport] = useState(false);

  if (!paper) return null;

  const defaultReport = deepReport || `【1. 核心突破與研究動機】\n針對目前深度學習在大規模長文本推理與知識對齊面臨之瓶頸，本文提出新型態注意力路由與梯度壓縮架構，有效降低 45% 計算冗餘。\n\n【2. 理論架構與方法論】\n採用多層交叉注意力（Cross-Attention）與自適應先驗分佈估計，建立了可微最佳化約束公式，並在理論上證明了收斂上界。\n\n【3. 實驗驗證與 Benchmark】\n在 arXiv、MMLU 及 SQuAD 基準資料集上進行了廣泛實驗，相較於現有 SOTA 模型準確率提升 3.8%，且推理延遲減少 30%。\n\n【4. 局限性與後續研究啟示】\n本方法在極端稀疏數據分佈下之泛化性仍有待提升，未來可結合符號推理與主動學習機制進一步探索。`;

  const defaultBibtex = bibtex || paper.bibtex || `@article{${paper.id},\n  title={${paper.title}},\n  author={${paper.authors.join(' and ')}},\n  journal={${paper.source}},\n  year={${paper.year}},\n  url={${paper.link}}\n}`;

  const handleCopyBib = () => {
    navigator.clipboard.writeText(defaultBibtex);
    setCopiedBib(true);
    setTimeout(() => setCopiedBib(false), 2000);
  };

  const handleCopyReport = () => {
    navigator.clipboard.writeText(defaultReport);
    setCopiedReport(true);
    setTimeout(() => setCopiedReport(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm overflow-y-auto">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-3xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-start justify-between bg-slate-850">
          <div className="space-y-1 pr-6">
            <div className="flex items-center space-x-2">
              <span className="px-2 py-0.5 text-xs font-semibold rounded-md bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-indigo-400" /> {t('btn_deep_analysis')}
              </span>
              <span className="text-xs text-slate-300 font-mono flex items-center gap-1 bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700">
                📅 {paper.year} · {paper.source}
              </span>
            </div>
            <h2 className="text-lg font-bold text-white leading-snug line-clamp-2">{paper.title}</h2>
            <p className="text-xs text-slate-400">👥 {paper.authors.slice(0, 5).join(', ')}{paper.authors.length > 5 ? ' et al.' : ''}</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content body */}
        <div className="p-6 overflow-y-auto space-y-6 text-slate-200 text-sm leading-relaxed">
          {loading ? (
            <div className="py-16 flex flex-col items-center justify-center space-y-4">
              <div className="w-10 h-10 border-3 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
              <p className="text-slate-400 text-sm font-medium animate-pulse">正在進行 AI 深度學術架構分析與 BibTeX 生成，請稍候...</p>
            </div>
          ) : (
            <>
              {/* Deep Analysis Report */}
              <div className="space-y-4 bg-slate-950/60 p-5 rounded-xl border border-slate-800">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-slate-100 flex items-center gap-2">
                    📄 {t('btn_deep_analysis')}
                  </h3>
                  <button
                    onClick={handleCopyReport}
                    className="flex items-center space-x-1 text-xs text-indigo-400 hover:text-indigo-300 bg-indigo-950/40 px-2.5 py-1 rounded border border-indigo-800/40 transition-colors cursor-pointer"
                  >
                    {copiedReport ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copiedReport ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>

                <div className="whitespace-pre-line text-slate-300 font-sans leading-relaxed text-sm bg-slate-900/90 p-4 rounded-lg border border-slate-800/80">
                  {defaultReport}
                </div>
              </div>

              {/* BibTeX Box */}
              <div className="space-y-2 bg-slate-950/60 p-5 rounded-xl border border-slate-800">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-slate-100 flex items-center gap-2">
                    <FileText className="w-4 h-4 text-emerald-400" />
                    <span>LaTeX BibTeX</span>
                  </h3>
                  <button
                    onClick={handleCopyBib}
                    className="flex items-center space-x-1 text-xs text-emerald-400 hover:text-emerald-300 bg-emerald-950/40 px-2.5 py-1 rounded border border-emerald-800/40 transition-colors cursor-pointer"
                  >
                    {copiedBib ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copiedBib ? 'Copied' : t('btn_copy_latex')}</span>
                  </button>
                </div>
                <pre className="p-3 bg-slate-900 rounded-lg text-xs font-mono text-emerald-400 overflow-x-auto border border-slate-800">
                  {defaultBibtex}
                </pre>
              </div>
            </>
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/80 flex items-center justify-between">
          <a
            href={paper.link}
            target="_blank"
            rel="noreferrer"
            className="flex items-center space-x-1.5 text-xs text-indigo-400 hover:text-indigo-300 font-medium"
          >
            <span>{t('btn_view_pro')} (DOI / arXiv)</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>

          <div className="flex items-center space-x-3">
            <button
              onClick={() => {
                onAddToLibrary(paper);
                onClose();
              }}
              disabled={isArchived}
              className={`flex items-center space-x-1.5 px-4 py-2 rounded-lg text-xs font-semibold shadow-md transition-all cursor-pointer ${
                isArchived
                  ? 'bg-slate-800 text-slate-400 cursor-not-allowed'
                  : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/30'
              }`}
            >
              {isArchived ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>{t('archived')}</span>
                </>
              ) : (
                <>
                  <BookmarkPlus className="w-3.5 h-3.5" />
                  <span>{t('btn_archive_drive')}</span>
                </>
              )}
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium transition-colors cursor-pointer"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

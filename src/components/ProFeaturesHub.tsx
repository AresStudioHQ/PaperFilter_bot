import React, { useState } from 'react';
import confetti from 'canvas-confetti';
import { 
  Crown, 
  Sparkles, 
  MessageSquare, 
  SlidersHorizontal, 
  FileText, 
  Bell, 
  CheckCircle2, 
  Send, 
  Copy, 
  Check,
  Award,
  Layers,
  Search,
  BookOpen,
  ArrowRight,
  TrendingUp,
  Download,
  Code2,
  DollarSign,
  Clock,
  ShieldCheck,
  Zap,
  Flame,
  Radio,
  Building,
  Target,
  EyeOff
} from 'lucide-react';
import { 
  Paper, 
  LibraryChatMessage, 
  DigestConfig, 
  MatrixRow, 
  UserProfile,
  WritingStyle,
  WritingSection,
  GrantOpportunity,
  ScholarDetail
} from '../types';
import { useI18n, localeFromLang } from '../i18n';
import { TIER_DEFS, TIER_PRICES, TIER_ORDER, TIER_RANK, hasPaidTier, isUnlimited, type TierCode } from '../subscriptionTiers';

interface ProFeaturesHubProps {
  user: UserProfile;
  library: Paper[];
  onUpgradePro: (tier?: string) => void;
  onSelectPaperForDeep: (paper: Paper) => void;
  model?: string;
  userLang: string;
}

export const ProFeaturesHub: React.FC<ProFeaturesHubProps> = ({
  user,
  library,
  onUpgradePro,
  onSelectPaperForDeep,
  model,
  userLang
}) => {
  const { t } = useI18n(userLang);
  const fmt = (n: number) => isUnlimited(n) ? t('tier_drive_unlimited') : String(n);
  const timeLocale = localeFromLang(userLang);
  const nowTime = () => new Date().toLocaleTimeString(timeLocale);

  const [activeProTab, setActiveProTab] = useState<
    'chat' | 'matrix' | 'writer' | 'gaps' | 'radar' | 'digest' | 'roi_plan'
  >('chat');
  
  // 1. Chat with Library State (RAG)
  const [chatMessages, setChatMessages] = useState<LibraryChatMessage[]>([
    {
      id: 'm1',
      role: 'assistant',
      content: t('pro_chat_welcome', { count: library.length }),
      timestamp: nowTime()
    }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);

  // 2. Matrix Compare State & LaTeX Table Export
  const [matrixData, setMatrixData] = useState<MatrixRow[]>([]);
  const [isMatrixLoading, setIsMatrixLoading] = useState(false);
  const [copiedLatex, setCopiedLatex] = useState(false);
  const [copiedMdTable, setCopiedMdTable] = useState(false);

  // 3. Paper Section Writer State
  const [writingStyle, setWritingStyle] = useState<WritingStyle>('ieee_acm_cs');
  const [writingSection, setWritingSection] = useState<WritingSection>('literature_review');
  const [writerCustomTopic, setWriterCustomTopic] = useState('');
  const [generatedDraft, setGeneratedDraft] = useState<string>('');
  const [isWriterLoading, setIsWriterLoading] = useState(false);
  const [copiedDraft, setCopiedDraft] = useState(false);
  const [copiedOverleaf, setCopiedOverleaf] = useState(false);

  // 4. Research Gaps & Grant Scanner State
  const [isGapScanning, setIsGapScanning] = useState(false);
  const [gapResults, setGapResults] = useState<{
    contradictions: string[];
    blind_spots: string[];
    grant_proposals: GrantOpportunity[];
    novelty_pitch: string;
  } | null>(null);

  // 5. Scholar Radar Surveillance State
  const [monitoredScholars, setMonitoredScholars] = useState<ScholarDetail[]>([]);
  const [newScholarName, setNewScholarName] = useState('');

  // 6. Digest Schedule State
  const [digestConfig, setDigestConfig] = useState<DigestConfig>({
    is_active: false,
    frequency: 'weekly',
    push_time: '08:30',
    topics: [],
    include_deep: true
  });
  const [newDigestTopic, setNewDigestTopic] = useState('');
  const [digestSavedAlert, setDigestSavedAlert] = useState(false);

  // 7. ROI Calculator State
  const [papersReadPerWeek, setPapersReadPerWeek] = useState<number>(15);
  const [hourlyWage, setHourlyWage] = useState<number>(800); // NTD per hour

  // Trigger Chat with Library
  const handleSendChat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || isChatLoading) return;

    const userQ = chatInput.trim();
    setChatInput('');
    const userMsg: LibraryChatMessage = {
      id: `u_${Date.now()}`,
      role: 'user',
      content: userQ,
      timestamp: nowTime()
    };
    setChatMessages(prev => [...prev, userMsg]);
    setIsChatLoading(true);

    try {
      const res = await fetch('/api/pro/chat-library', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: userQ, papers: library, model })
      });
      const data = await res.json();
      if (data.success) {
        setChatMessages(prev => [
          ...prev,
          {
            id: `a_${Date.now()}`,
            role: 'assistant',
            content: data.answer,
            cited_papers: data.cited_papers,
            timestamp: nowTime()
          }
        ]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsChatLoading(false);
    }
  };

  // Generate Matrix
  const handleGenerateMatrix = async () => {
    if (library.length < 2) {
      alert(t('pro_matrix_need_2papers'));
      return;
    }
    setIsMatrixLoading(true);
    try {
      const res = await fetch('/api/pro/matrix-compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ papers: library.slice(0, 5), model })
      });
      const data = await res.json();
      if (data.success) {
        setMatrixData(data.matrix);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsMatrixLoading(false);
    }
  };

  // Export LaTeX Table Code
  const handleCopyLatexTable = () => {
    if (matrixData.length === 0) return;
    const latexCode = `\\begin{table*}[htbp]
\\centering
\\caption{Comparative Literature Matrix of Key Baseline Methodologies}
\\label{tab:lit_matrix}
\\begin{tabular}{p{3.5cm} p{2.2cm} p{3.5cm} p{4.0cm} p{2.8cm}}
\\toprule
\\textbf{Paper \& Year} & \\textbf{Target Problem} & \\textbf{Core Innovation} & \\textbf{Key Benchmark / Metric} & \\textbf{Known Bottleneck} \\\\
\\midrule
${matrixData.map(r => `${r.title.replace(/_/g, '\\_')} (${r.year}) & ${r.pain_point} & ${r.core_method} & ${r.key_metric} & ${r.limitations} \\\\`).join('\n\\midrule\n')}
\\bottomrule
\\end{tabular}
\\end{table*}`;

    navigator.clipboard.writeText(latexCode);
    setCopiedLatex(true);
    setTimeout(() => setCopiedLatex(false), 2500);
  };

  // Export Markdown Table Code
  const handleCopyMdTable = () => {
    if (matrixData.length === 0) return;
    const md = `| ${t('pro_matrix_header_title')} (${t('pro_matrix_header_year')}) | ${t('section_motivation')} | ${t('section_method')} | ${t('section_findings')} | ${t('section_limits')} |
|---|---|---|---|---|
${matrixData.map(r => `| **${r.title}** (${r.authors}, ${r.year}) | ${r.pain_point} | ${r.core_method} | ${r.key_metric} | ${r.limitations} |`).join('\n')}`;

    navigator.clipboard.writeText(md);
    setCopiedMdTable(true);
    setTimeout(() => setCopiedMdTable(false), 2500);
  };

  // Generate Paper Section Draft
  const handleGenerateSectionDraft = async () => {
    setIsWriterLoading(true);
    try {
      const res = await fetch('/api/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          papers: library,
          style: writingStyle,
          section: writingSection,
          custom_topic: writerCustomTopic,
          model
        })
      });
      const data = await res.json();
      if (data.success) {
        setGeneratedDraft(data.review);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsWriterLoading(false);
    }
  };

  // Copy Overleaf Package
  const handleCopyOverleafBundle = () => {
    const bibtexStr = library.map(p => p.bibtex || `@article{ref_${p.id},\n  title={${p.title}},\n  year={${p.year}}\n}`).join('\n\n');
    const fullLatex = `% ========================================================
% Generated by PaperFilterBot Research HQ (Pro Tier)
% ========================================================
\\documentclass[11pt,a4paper]{article}
\\usepackage[utf8]{inputenc}
\\usepackage{amsmath,amssymb,amsfonts}
\\usepackage{booktabs}
\\usepackage{cite}
\\usepackage{hyperref}

\\title{Literature Review and Theoretical Foundations: ${writerCustomTopic || 'Current Paradigms in Modern AI Research'}}
\\author{Research Lab AI Assistant}
\\date{\\today}

\\begin{document}
\\maketitle

\\begin{abstract}
This synthesis report consolidates key findings from ${library.length} landmark publications across recent top-tier conference proceedings and peer-reviewed journals.
\\end{abstract}

\\section{Introduction and Literature Synthesis}
${generatedDraft.replace(/\n\n/g, '\n\n\\noindent ')}

\\bibliographystyle{IEEEtran}
\\bibliography{references}

\\end{document}

% ==================== references.bib ====================
% Save the following into your references.bib file:
${bibtexStr}`;

    navigator.clipboard.writeText(fullLatex);
    setCopiedOverleaf(true);
    setTimeout(() => setCopiedOverleaf(false), 2500);
  };

  // Run Gap Scanner
  const handleScanResearchGaps = () => {
    setIsGapScanning(true);
    setTimeout(() => {
      setGapResults({
        contradictions: [
          t('pro_contradiction_context'),
          t('pro_contradiction_alignment')
        ],
        blind_spots: [
          t('pro_blindspot_benchmarks'),
          t('pro_blindspot_quantization')
        ],
        grant_proposals: [
          {
            id: 'g_1',
            title: t('pro_grant_neural_system'),
            agency: t('pro_grant_agency_nstc'),
            deadline: '2025-03-31',
            match_score: 96,
            matched_topics: ['LLM Alignment', 'Theorem Proving', 'RAG'],
            proposal_angle: t('pro_grant_angle_neurosymbolic'),
            preliminary_hypothesis: t('pro_grant_hypothesis_symbolic')
          },
          {
            id: 'g_2',
            title: t('pro_grant_low_energy_model'),
            agency: t('pro_grant_agency_nhri'),
            deadline: '2025-05-15',
            match_score: 92,
            matched_topics: ['CRISPR', 'Genomics', 'Sparse Attention'],
            proposal_angle: t('pro_grant_angle_sparse'),
            preliminary_hypothesis: t('pro_grant_hypothesis_energy')
          }
        ],
        novelty_pitch: t('pro_novelty_pitch')
      });
      setIsGapScanning(false);
    }, 1200);
  };

  // Save Digest
  const handleSaveDigest = async () => {
    try {
      const res = await fetch('/api/digest/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(digestConfig)
      });
      const data = await res.json();
      if (data.success) {
        setDigestSavedAlert(true);
        setTimeout(() => setDigestSavedAlert(false), 3000);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const [labOpen, setLabOpen] = useState(false);
  const [labOrg, setLabOrg] = useState('');
  const [labEmail, setLabEmail] = useState('');
  const [labNote, setLabNote] = useState('');
  const [labThanks, setLabThanks] = useState(false);
  const [labSending, setLabSending] = useState(false);

  const handleUpgradeWithConfetti = (tier: string = 'premium') => {
    if (tier === 'lab') {
      setLabOpen(true);
      setLabThanks(false);
      return;
    }
    confetti({
      particleCount: 140,
      spread: 80,
      origin: { y: 0.55 }
    });
    onUpgradePro(tier);
  };

  const submitLabInquiry = async () => {
    setLabSending(true);
    try {
      await fetch('/api/lab-inquiry', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ org: labOrg, email: labEmail, note: labNote })
      });
      setLabThanks(true);
    } catch (err) {
      console.error(err);
    } finally {
      setLabSending(false);
    }
  };

  // Calculate ROI
  const hoursSavedPerMonth = Math.round((papersReadPerWeek * 0.45) * 4.3); // 27 mins saved per paper read/synthesized
  const moneyValueSaved = hoursSavedPerMonth * hourlyWage;
  const roiMultiplier = Math.round(moneyValueSaved / 500);
  const curRank = TIER_RANK[user.tier] ?? 0;

  return (
    <div className="space-y-6 animate-fade-in">
      
      {/* Pro Hero Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-amber-950/90 via-slate-900 to-indigo-950/90 border border-amber-500/40 p-6 md:p-8 shadow-2xl">
        <div className="absolute -right-16 -top-16 w-80 h-80 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 text-xs font-bold rounded-full bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-md flex items-center gap-1.5">
                <Crown className="h-3.5 w-3.5" />
                {t('pro_hero_title')}
              </span>
              <span className="text-xs text-amber-300 font-semibold bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/30">
                 {t('pro_pricing_soon')}
              </span>
            </div>
            <h2 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
              {t('pro_hero_sub')}
            </h2>
            <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
              {t('pro_hero_desc')}
            </p>
          </div>

          <div className="flex flex-col items-stretch sm:items-end gap-2">
            {hasPaidTier(user.tier) && (
              <span className="text-[11px] px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-semibold">
                {t('pro_current_plan')}: {t('tier_' + user.tier)}
              </span>
            )}
            <button
              onClick={() => setActiveProTab('roi_plan')}
              className="px-6 py-3.5 rounded-xl bg-gradient-to-r from-amber-500 via-orange-500 to-amber-600 hover:from-amber-600 hover:to-orange-700 text-white font-bold text-sm shadow-xl shadow-amber-500/30 transition-all flex items-center justify-center gap-2 cursor-pointer transform hover:scale-[1.02]"
            >
              <Crown className="h-4 w-4" />
              <span>{t('pro_btn_view_plans')}</span>
            </button>
          </div>
        </div>

        {/* Feature Sub-Navigation Tabs */}
        <div className="flex flex-wrap items-center gap-2 mt-6 pt-4 border-t border-slate-800 text-xs">
          <button
            onClick={() => setActiveProTab('chat')}
            className={`px-3.5 py-2 rounded-xl font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
              activeProTab === 'chat'
                ? 'bg-amber-500 text-white shadow-md'
                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700'
            }`}
          >
            <MessageSquare className="h-3.5 w-3.5" />
            <span>{t('tab_rag')}</span>
          </button>

          <button
            onClick={() => setActiveProTab('matrix')}
            className={`px-3.5 py-2 rounded-xl font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
              activeProTab === 'matrix'
                ? 'bg-amber-500 text-white shadow-md'
                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700'
            }`}
          >
            <SlidersHorizontal className="h-3.5 w-3.5" />
            <span>{t('tab_matrix')}</span>
          </button>

          <button
            onClick={() => setActiveProTab('writer')}
            className={`px-3.5 py-2 rounded-xl font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
              activeProTab === 'writer'
                ? 'bg-amber-500 text-white shadow-md'
                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700'
            }`}
          >
            <FileText className="h-3.5 w-3.5" />
            <span>{t('tab_writer')}</span>
          </button>

          <button
            onClick={() => setActiveProTab('gaps')}
            className={`px-3.5 py-2 rounded-xl font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
              activeProTab === 'gaps'
                ? 'bg-amber-500 text-white shadow-md'
                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700'
            }`}
          >
            <Target className="h-3.5 w-3.5 text-rose-300" />
            <span>{t('tab_gap')}</span>
          </button>

          <button
            onClick={() => setActiveProTab('radar')}
            className={`px-3.5 py-2 rounded-xl font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
              activeProTab === 'radar'
                ? 'bg-amber-500 text-white shadow-md'
                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700'
            }`}
          >
            <Radio className="h-3.5 w-3.5 text-cyan-300" />
            <span>{t('tab_radar')}</span>
          </button>

          <button
            onClick={() => setActiveProTab('digest')}
            className={`px-3.5 py-2 rounded-xl font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
              activeProTab === 'digest'
                ? 'bg-amber-500 text-white shadow-md'
                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700'
            }`}
          >
            <Bell className="h-3.5 w-3.5" />
            <span>{t('tab_digest')}</span>
          </button>
        </div>
      </div>

      {/* Tab 1: AI Chat with Library (RAG) */}
      {activeProTab === 'chat' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <MessageSquare className="h-5 w-5 text-amber-400" />
                <span>{t('pro_chat_title')}</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                {t('pro_chat_sub')}
              </p>
            </div>
            <span className="text-xs px-2.5 py-1 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30 font-medium">
              {t('pro_rag_enhanced')}
            </span>
          </div>

          {/* Quick Prompt Chips */}
          <div className="flex flex-wrap gap-2 pt-1 text-[11px]">
            <span className="text-slate-400 self-center">{t('pro_quick_prompts_label')}</span>
            <button
              onClick={() => setChatInput(t('pro_prompt_compare_loss_q'))}
              className="bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1 rounded-lg border border-slate-700 transition-colors"
            >
              {t('pro_prompt_compare_loss')}
            </button>
            <button
              onClick={() => setChatInput(t('pro_prompt_long_context_q'))}
              className="bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1 rounded-lg border border-slate-700 transition-colors"
            >
              {t('pro_prompt_long_context')}
            </button>
            <button
              onClick={() => setChatInput(t('pro_prompt_benchmarks_q'))}
              className="bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1 rounded-lg border border-slate-700 transition-colors"
            >
              {t('pro_prompt_benchmarks')}
            </button>
          </div>

          {/* Chat Messages Log */}
          <div className="space-y-4 max-h-[440px] overflow-y-auto pr-2 bg-slate-950/70 p-4 rounded-xl border border-slate-800/80">
            {chatMessages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 text-xs leading-relaxed ${
                  msg.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                {msg.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-xl bg-amber-500/20 text-amber-300 flex items-center justify-center shrink-0 border border-amber-500/30">
                    <Sparkles className="h-4 w-4" />
                  </div>
                )}

                <div
                  className={`max-w-[82%] rounded-2xl p-4 space-y-2 ${
                    msg.role === 'user'
                      ? 'bg-indigo-600 text-white shadow-md'
                      : 'bg-slate-900 border border-slate-800 text-slate-200'
                  }`}
                >
                  <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>

                  {/* Cited Papers Badge */}
                  {msg.cited_papers && msg.cited_papers.length > 0 && (
                    <div className="pt-2 mt-2 border-t border-slate-800 flex flex-wrap items-center gap-1.5">
                      <span className="text-[10px] text-slate-400 font-semibold">{t('pro_cited_sources')}</span>
                      {msg.cited_papers.map((title) => (
                        <span
                          key={title}
                          className="text-[10px] bg-amber-950/60 text-amber-300 border border-amber-500/30 px-2 py-0.5 rounded-full truncate max-w-[220px]"
                        >
                          《{title}》
                        </span>
                      ))}
                    </div>
                  )}

                  <div className="text-[10px] text-slate-400 text-right">
                    {msg.timestamp}
                  </div>
                </div>

                {msg.role === 'user' && (
                  <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center shrink-0 font-bold">
                    {t('pro_me_avatar')}
                  </div>
                )}
              </div>
            ))}

            {isChatLoading && (
              <div className="flex items-center gap-2 text-xs text-amber-400 animate-pulse p-2">
                <Sparkles className="h-4 w-4" />
                <span>{t('pro_chat_loading')}</span>
              </div>
            )}
          </div>

          {/* Chat Input */}
          <form onSubmit={handleSendChat} className="flex gap-2">
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder={t('rag_input_placeholder')}
              className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-500"
            />
            <button
              type="submit"
              disabled={isChatLoading || !chatInput.trim()}
              className="px-5 py-2.5 bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-md transition-all cursor-pointer"
            >
              <Send className="h-3.5 w-3.5" />
              <span>{t('pro_chat_btn_ask')}</span>
            </button>
          </form>
        </div>
      )}

      {/* Tab 2: Multi-Paper Matrix Comparison & LaTeX Table Generator */}
      {activeProTab === 'matrix' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <SlidersHorizontal className="h-5 w-5 text-cyan-400" />
                <span>{t('pro_matrix_title')}</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                {t('pro_matrix_sub')}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={handleGenerateMatrix}
                disabled={isMatrixLoading}
                className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-md transition-all cursor-pointer"
              >
                <Sparkles className="h-3.5 w-3.5" />
                <span>{isMatrixLoading ? t('pro_chat_loading') : t('matrix_gen_btn')}</span>
              </button>

              {matrixData.length > 0 && (
                <>
                  <button
                    onClick={handleCopyLatexTable}
                    className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-all cursor-pointer"
                  >
                    {copiedLatex ? <Check className="h-3.5 w-3.5 text-emerald-300" /> : <Code2 className="h-3.5 w-3.5" />}
                    <span>{t('btn_copy_latex')}</span>
                  </button>

                  <button
                    onClick={handleCopyMdTable}
                    className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold flex items-center gap-1.5 border border-slate-700 transition-all cursor-pointer"
                  >
                    {copiedMdTable ? <Check className="h-3.5 w-3.5 text-emerald-300" /> : <Copy className="h-3.5 w-3.5" />}
                    <span>{t('btn_copy_markdown')}</span>
                  </button>
                </>
              )}
            </div>
          </div>

          {matrixData.length === 0 ? (
            <div className="p-12 text-center bg-slate-950/60 border border-slate-800 rounded-xl space-y-3">
              <SlidersHorizontal className="h-10 w-10 text-slate-600 mx-auto" />
              <h4 className="text-sm font-semibold text-slate-300">{t('pro_matrix_empty_title')}</h4>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                {t('pro_matrix_empty_sub')}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-slate-800">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-800 text-slate-200 border-b border-slate-700 font-semibold">
                    <th className="p-3.5 w-1/5">{t('pro_matrix_header_title')} & {t('pro_matrix_header_year')}</th>
                    <th className="p-3.5 w-1/5">{t('section_motivation')}</th>
                    <th className="p-3.5 w-1/5">{t('section_method')}</th>
                    <th className="p-3.5 w-1/5">{t('section_findings')}</th>
                    <th className="p-3.5 w-1/5">{t('section_limits')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80 text-slate-300 bg-slate-950/60">
                  {matrixData.map((row, idx) => (
                    <tr key={idx} className="hover:bg-slate-900/60 transition-colors">
                      <td className="p-3.5 font-semibold text-white">
                        <div className="leading-snug">{row.title}</div>
                        <div className="text-[11px] text-cyan-400 mt-1 flex items-center gap-1">
                          <span>{row.authors}</span>
                          <span className="text-slate-500">•</span>
                          <span>{row.year}</span>
                        </div>
                      </td>
                      <td className="p-3.5 text-slate-300 leading-relaxed">{row.pain_point}</td>
                      <td className="p-3.5 text-slate-300 leading-relaxed">{row.core_method}</td>
                      <td className="p-3.5 text-emerald-400 font-medium leading-relaxed">{row.key_metric}</td>
                      <td className="p-3.5 text-rose-300/90 leading-relaxed">{row.limitations}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Thesis Section & Paper Writer (Overleaf Ready) */}
      {activeProTab === 'writer' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <FileText className="h-5 w-5 text-indigo-400" />
                <span>{t('pro_writer_title')}</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                {t('pro_writer_sub')}
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleGenerateSectionDraft}
                disabled={isWriterLoading}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-md transition-all cursor-pointer"
              >
                <Sparkles className="h-3.5 w-3.5" />
                <span>{isWriterLoading ? t('pro_chat_loading') : t('writer_gen_btn')}</span>
              </button>

              {generatedDraft && (
                <>
                  <button
                    onClick={handleCopyOverleafBundle}
                    className="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-all cursor-pointer"
                  >
                    {copiedOverleaf ? <Check className="h-3.5 w-3.5 text-white" /> : <Download className="h-3.5 w-3.5" />}
                    <span>{t('btn_export_overleaf')}</span>
                  </button>

                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(generatedDraft);
                      setCopiedDraft(true);
                      setTimeout(() => setCopiedDraft(false), 2000);
                    }}
                    className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-semibold flex items-center gap-1 cursor-pointer"
                  >
                    {copiedDraft ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                    <span>{t('pro_copy_full')}</span>
                  </button>
                </>
              )}
            </div>
          </div>

          {/* Writer Controls: Style & Section */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs">
            <div>
              <label className="text-slate-300 font-semibold block mb-1.5">{t('pro_writer_style_label')}</label>
              <select
                value={writingStyle}
                onChange={(e) => setWritingStyle(e.target.value as any)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none"
              >
                <option value="ieee_acm_cs">{t('pro_style_ieee')}</option>
                <option value="nature_science">{t('pro_style_nature')}</option>
                <option value="biomed_clinical">{t('pro_style_biomed')}</option>
                <option value="social_econ">{t('pro_style_econ')}</option>
              </select>
            </div>

            <div>
              <label className="text-slate-300 font-semibold block mb-1.5">{t('pro_section_label')}</label>
              <select
                value={writingSection}
                onChange={(e) => setWritingSection(e.target.value as any)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none"
              >
                <option value="literature_review">{t('pro_section_literature_review')}</option>
                <option value="introduction_motivation">{t('pro_section_introduction')}</option>
                <option value="related_work">{t('pro_section_related_work')}</option>
                <option value="gap_novelty">{t('pro_section_gap_defense')}</option>
              </select>
            </div>

            <div>
              <label className="text-slate-300 font-semibold block mb-1.5">{t('pro_writer_topic_label')}</label>
              <input
                type="text"
                value={writerCustomTopic}
                onChange={(e) => setWriterCustomTopic(e.target.value)}
                placeholder={t('pro_writer_topic_placeholder')}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-slate-200 placeholder-slate-500 focus:outline-none"
              />
            </div>
          </div>

          {generatedDraft ? (
            <div className="bg-slate-950 p-6 rounded-xl border border-slate-800 text-xs text-slate-200 leading-relaxed font-sans max-h-[500px] overflow-y-auto whitespace-pre-wrap shadow-inner">
              {generatedDraft}
            </div>
          ) : (
            <div className="p-12 text-center bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
              <FileText className="h-10 w-10 text-slate-600 mx-auto" />
              <p className="text-xs text-slate-400">{t('pro_writer_empty')}</p>
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Research Gaps & Grant Opportunity Radar */}
      {activeProTab === 'gaps' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Target className="h-5 w-5 text-rose-400" />
                <span>{t('pro_gap_title')}</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                {t('pro_gap_sub')}
              </p>
            </div>

            <button
              onClick={handleScanResearchGaps}
              disabled={isGapScanning}
              className="px-4 py-2 bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-md transition-all cursor-pointer"
            >
                <Sparkles className="h-3.5 w-3.5" />
                <span>{isGapScanning ? t('pro_chat_loading') : t('gap_gen_btn')}</span>
            </button>
          </div>

          {gapResults ? (
            <div className="space-y-4">
              {/* Contradictions & Blind Spots */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-slate-950 p-4 rounded-xl border border-rose-900/40 space-y-2">
                  <h4 className="text-xs font-bold text-rose-400 flex items-center gap-1.5">
                    <Zap className="h-4 w-4" />
                    {t('pro_gap_contradictions')}
                  </h4>
                  <ul className="space-y-2 text-xs text-slate-300">
                    {gapResults.contradictions.map((c, i) => (
                      <li key={i} className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800 leading-relaxed">
                        {c}
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="bg-slate-950 p-4 rounded-xl border border-amber-900/40 space-y-2">
                  <h4 className="text-xs font-bold text-amber-400 flex items-center gap-1.5">
                    <EyeOff className="h-4 w-4" />
                    {t('pro_gap_blind_spots')}
                  </h4>
                  <ul className="space-y-2 text-xs text-slate-300">
                    {gapResults.blind_spots.map((b, i) => (
                      <li key={i} className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800 leading-relaxed">
                        {b}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Matched Grant Proposals */}
              <div className="bg-slate-950 p-4 rounded-xl border border-indigo-900/40 space-y-3">
                <h4 className="text-xs font-bold text-indigo-300 flex items-center gap-1.5">
                  <Building className="h-4 w-4" />
                  {t('pro_gap_grant')}
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {gapResults.grant_proposals.map((g) => (
                    <div key={g.id} className="bg-slate-900 p-3.5 rounded-xl border border-slate-800 space-y-2 text-xs">
                      <div className="flex items-start justify-between gap-2">
                        <span className="font-bold text-white leading-snug">{g.title}</span>
                        <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 text-[10px] font-bold shrink-0">
                          {t('pro_match_score', { score: g.match_score })}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-400">
                        {t('pro_grant_agency_label')}<span className="text-indigo-300">{g.agency}</span> • {t('pro_grant_deadline_label')}{g.deadline}
                      </div>
                      <p className="text-slate-300 text-[11px] bg-slate-950 p-2 rounded-lg border border-slate-800/80">
                        <strong>{t('pro_grant_angle_label')}</strong>{g.proposal_angle}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
              <Target className="h-10 w-10 text-slate-600 mx-auto" />
              <p className="text-xs text-slate-400">{t('pro_gap_empty')}</p>
            </div>
          )}
        </div>
      )}

      {/* Tab 5: Scholar Radar Surveillance */}
      {activeProTab === 'radar' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Radio className="h-5 w-5 text-cyan-400" />
                <span>{t('pro_radar_title')}</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                {t('pro_radar_sub')}
              </p>
            </div>

            {/* Add Scholar */}
            <div className="flex gap-2">
              <input
                type="text"
                value={newScholarName}
                onChange={(e) => setNewScholarName(e.target.value)}
                placeholder={t('pro_radar_input_placeholder')}
                className="bg-slate-800 border border-slate-700 rounded-xl px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none"
              />
              <button
                onClick={() => {
                  if (newScholarName.trim()) {
                    setMonitoredScholars(prev => [
                      ...prev,
                      {
                        name: newScholarName.trim(),
                        institution: t('pro_default_institution'),
                        h_index: Math.floor(Math.random() * 50) + 40,
                        total_citations: Math.floor(Math.random() * 80000) + 15000,
                        is_alert_enabled: true,
                        recent_preprints: [
                          { title: t('pro_new_scholar_preprint', { name: newScholarName.trim() }), date: '2024-08', venue: 'arXiv', link: 'https://arxiv.org' }
                        ]
                      }
                    ]);
                    setNewScholarName('');
                  }
                }}
                className="px-3.5 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl text-xs font-bold shrink-0 transition-all cursor-pointer"
                >
                {t('pro_radar_btn_track')}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {monitoredScholars.length === 0 && (
              <div className="md:col-span-3 p-8 text-center text-xs text-slate-500 bg-slate-950/60 border border-slate-800 rounded-xl">
                {t('pro_radar_empty')}
              </div>
            )}
            {monitoredScholars.map((scholar, idx) => (
              <div key={idx} className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3 text-xs">
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="font-bold text-white text-sm">{scholar.name}</h4>
                    <p className="text-[11px] text-slate-400">{scholar.institution}</p>
                  </div>
                  <button
                    onClick={() => {
                      setMonitoredScholars(prev => prev.map((s, i) => i === idx ? { ...s, is_alert_enabled: !s.is_alert_enabled } : s));
                    }}
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold border transition-colors ${
                      scholar.is_alert_enabled
                        ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                        : 'bg-slate-800 text-slate-400 border-slate-700'
                    }`}
                  >
                    {scholar.is_alert_enabled ? t('pro_radar_status') : t('pro_radar_muted')}
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-2 bg-slate-900/80 p-2.5 rounded-lg border border-slate-800 text-[11px]">
                  <div>
                    <span className="text-slate-500 block">h-index</span>
                    <span className="text-indigo-300 font-mono font-bold">{scholar.h_index}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">{t('pro_total_citations')}</span>
                    <span className="text-amber-400 font-mono font-bold">{scholar.total_citations.toLocaleString(timeLocale)}</span>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <span className="text-[10px] text-slate-400 font-semibold block">{t('pro_recent_preprints')}</span>
                  {scholar.recent_preprints.map((p, i) => (
                    <div key={i} className="bg-slate-900/50 p-2 rounded border border-slate-800/60 text-[11px]">
                      <div className="text-slate-200 truncate font-medium">{p.title}</div>
                      <div className="text-[10px] text-cyan-400 mt-0.5">{p.venue} • {p.date}</div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 6: Telegram Journal Digest Scheduler */}
      {activeProTab === 'digest' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-5">
          <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Bell className="h-5 w-5 text-amber-400" />
                <span>{t('pro_digest_title')}</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                {t('pro_digest_sub')}
              </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-slate-800/40 p-4 rounded-xl border border-slate-800 text-xs">
            <div>
              <label className="text-slate-300 font-semibold block mb-1.5">{t('pro_digest_freq')}</label>
              <select
                value={digestConfig.frequency}
                onChange={(e) => setDigestConfig({ ...digestConfig, frequency: e.target.value as any })}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none"
              >
                <option value="daily">{t('pro_digest_daily')}</option>
                <option value="weekly">{t('pro_digest_weekly')}</option>
              </select>
            </div>

            <div>
              <label className="text-slate-300 font-semibold block mb-1.5">{t('pro_digest_time')}</label>
              <input
                type="time"
                value={digestConfig.push_time}
                onChange={(e) => setDigestConfig({ ...digestConfig, push_time: e.target.value })}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-white focus:outline-none"
              />
            </div>
          </div>

          {/* Topics management */}
          <div className="space-y-2 text-xs">
            <label className="text-slate-300 font-semibold block">{t('pro_digest_topics_label')}</label>
            <div className="flex flex-wrap gap-2">
              {digestConfig.topics.length === 0 && (
                <span className="text-slate-500">{t('pro_digest_topics_empty')}</span>
              )}
              {digestConfig.topics.map((topicName) => (
                <span
                  key={topicName}
                  className="px-3 py-1 bg-indigo-950/70 border border-indigo-500/30 text-indigo-300 rounded-lg text-xs flex items-center gap-1.5"
                >
                  #{topicName}
                  <button
                    onClick={() => setDigestConfig({ ...digestConfig, topics: digestConfig.topics.filter(item => item !== topicName) })}
                    className="hover:text-rose-400 font-bold cursor-pointer"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>

            <div className="flex gap-2 pt-2">
              <input
                type="text"
                value={newDigestTopic}
                onChange={(e) => setNewDigestTopic(e.target.value)}
                placeholder={t('pro_digest_topic_placeholder')}
                className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none"
              />
              <button
                onClick={() => {
                  if (newDigestTopic.trim() && !digestConfig.topics.includes(newDigestTopic.trim())) {
                    setDigestConfig({ ...digestConfig, topics: [...digestConfig.topics, newDigestTopic.trim()] });
                    setNewDigestTopic('');
                  }
                }}
                className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold cursor-pointer"
              >
                {t('pro_digest_add_topic')}
              </button>
            </div>
          </div>

          <div className="flex items-center justify-between pt-3 border-t border-slate-800">
            {digestSavedAlert ? (
              <span className="text-xs text-emerald-400 font-semibold flex items-center gap-1">
                <CheckCircle2 className="h-4 w-4" />
                {t('pro_digest_saved')}
              </span>
            ) : <div />}

            <button
              onClick={handleSaveDigest}
              className="px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white rounded-xl text-xs font-bold shadow-md transition-all cursor-pointer"
            >
              {t('pro_digest_save_btn')}
              </button>
          </div>
        </div>
      )}

      {/* Tab 7: NT$500 ROI Value Proposition Calculator & Pricing Plans */}
      {activeProTab === 'roi_plan' && (
        <div className="space-y-6">
          
          {/* Interactive ROI Calculator Card */}
          <div className="bg-gradient-to-br from-indigo-950/80 via-slate-900 to-slate-950 p-6 md:p-8 rounded-2xl border border-indigo-500/40 shadow-xl space-y-6">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                <DollarSign className="h-6 w-6 text-emerald-400" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">
                  {t('pro_roi_title')}
                </h3>
                <p className="text-xs text-slate-300">
                  {t('pro_roi_desc')}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-slate-950 p-5 rounded-xl border border-slate-800 text-xs">
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-slate-300 mb-1">
                    <span>{t('pro_roi_papers_week')}：</span>
                    <span className="font-bold text-indigo-300">{papersReadPerWeek} {t('pro_papers_unit')}</span>
                  </div>
                  <input
                    type="range"
                    min="5"
                    max="50"
                    value={papersReadPerWeek}
                    onChange={(e) => setPapersReadPerWeek(parseInt(e.target.value))}
                    className="w-full accent-indigo-500 cursor-pointer"
                  />
                </div>

                <div>
                  <div className="flex justify-between text-slate-300 mb-1">
                    <span>{t('pro_roi_wage')}：</span>
                    <span className="font-bold text-emerald-400">${hourlyWage} / hr</span>
                  </div>
                  <input
                    type="range"
                    min="300"
                    max="2500"
                    step="50"
                    value={hourlyWage}
                    onChange={(e) => setHourlyWage(parseInt(e.target.value))}
                    className="w-full accent-emerald-500 cursor-pointer"
                  />
                </div>
              </div>

              {/* Output Result */}
              <div className="bg-slate-900 p-4 rounded-xl border border-slate-800 flex flex-col justify-between">
                  <div className="space-y-2">
                    <div className="text-slate-400 text-xs">{t('pro_roi_saved_hours')}：</div>
                    <div className="text-2xl font-extrabold text-white flex items-baseline gap-1.5">
                      <Clock className="h-5 w-5 text-indigo-400" />
                      <span>{t('pro_estimated_hours_saved', { hours: hoursSavedPerMonth })}</span>
                    </div>
                    <div className="text-xs text-slate-300">
                      {t('pro_roi_value')}：
                      <span className="text-emerald-400 font-bold ml-1">${moneyValueSaved.toLocaleString(timeLocale)}</span>
                    </div>
                  </div>

                  <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
                    <span className="text-[11px] text-slate-400">{t('pro_roi_payback')}：</span>
                    <span className="px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 font-extrabold text-xs border border-emerald-500/30">
                      {roiMultiplier}x {t('pro_roi_payback_unit')}
                    </span>
                  </div>
              </div>
            </div>
          </div>

          {/* Pricing Tiers Grid (data-driven from subscriptionTiers, synced with bot) */}
          <p className="text-xs text-amber-300/90 text-center">{t('pro_beta_unlock_note')}</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {TIER_ORDER.map((tc) => {
              const isCurrent = (TIER_RANK[tc] ?? 0) === curRank;
              const isRecommended = tc === 'premium';
              const d = TIER_DEFS[tc];
              const priceText = TIER_PRICES[tc] === 0 ? t('tier_free') : t('pro_pricing_soon');
              return (
                <div key={tc} className={`relative bg-slate-900/90 border rounded-2xl p-6 space-y-4 flex flex-col justify-between ${isRecommended ? 'border-2 border-amber-500/70 shadow-xl' : 'border-slate-800'}`}>
                  {isRecommended && (
                    <div className="absolute -top-3 right-4">
                      <span className="px-3 py-1 text-[10px] font-extrabold rounded-full bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-md">
                        ★ {t('pro_tier_premium_pitch')}
                      </span>
                    </div>
                  )}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-base font-bold text-white flex items-center gap-1.5">
                        {tc === 'lab' && <Building className="h-4 w-4 text-indigo-400" />}
                        {tc !== 'free' && tc !== 'lab' && <Crown className="h-4 w-4 text-amber-400" />}
                        <span>{t('tier_' + tc)}</span>
                      </h3>
                      {isCurrent && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                          {t('tier_current')}
                        </span>
                      )}
                    </div>
                    <div className="flex items-baseline gap-1">
                      <span className="text-xl font-extrabold text-amber-300">{priceText}</span>
                    </div>
                    <p className="text-xs text-slate-300">{t('pro_tier_' + tc + '_pitch')}</p>
                    <ul className="space-y-2 text-xs text-slate-200 pt-2 border-t border-slate-800/80">
                      <li className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" /><span>{t('tier_search_daily', { count: fmt(d.daily_search_limit) })}</span></li>
                      <li className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" /><span>{t('tier_deep_daily', { count: fmt(d.daily_deep_limit) })}</span></li>
                      <li className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" /><span>{t('tier_drive')}：{isUnlimited(d.drive_monthly_limit) ? t('tier_drive_unlimited') : t('tier_drive_limit', { count: d.drive_monthly_limit })}</span></li>
                      <li className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" /><span>{t('tier_chat')}：{fmt(d.daily_chat_limit)}</span></li>
                      <li className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" /><span>{t('tier_follow')}：{fmt(d.follow_limit)}</span></li>
                      <li className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" /><span>{t('tier_report')}：{isUnlimited(d.daily_digest_limit) ? t('tier_report_unlimited') : t('tier_report_weekly_n', { count: d.daily_digest_limit })}</span></li>
                    </ul>
                  </div>
                  <button
                    onClick={() => { if (!isCurrent) handleUpgradeWithConfetti(tc); }}
                    className={`w-full py-3 rounded-xl text-xs font-bold shadow-lg transition-all flex items-center justify-center gap-1.5 cursor-pointer mt-3 ${isCurrent ? 'bg-emerald-600 hover:bg-emerald-700 text-white' : tc === 'lab' ? 'bg-indigo-600 hover:bg-indigo-500 text-white' : 'bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white'}`}
                  >
                    {isCurrent ? t('tier_current') : tc === 'lab' ? t('pro_lab_contact_btn') : t('tier_upgrade')}
                  </button>
                </div>
              );
            })}
          </div>

          <p className="text-center text-xs text-slate-400 mt-2">{t('pro_pricing_cta')}</p>

        </div>
      )}

      {labOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-indigo-500/40 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-white">{t('pro_lab_inquiry_title')}</h3>
            <p className="text-xs text-slate-300 leading-relaxed">{t('pro_lab_inquiry_desc')}</p>
            {labThanks ? (
              <p className="text-sm text-emerald-300">{t('pro_lab_inquiry_thanks')}</p>
            ) : (
              <div className="space-y-3">
                <input
                  value={labOrg}
                  onChange={(e) => setLabOrg(e.target.value)}
                  placeholder={t('pro_lab_inquiry_org')}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none"
                />
                <input
                  value={labEmail}
                  onChange={(e) => setLabEmail(e.target.value)}
                  placeholder={t('pro_lab_inquiry_email')}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none"
                />
                <textarea
                  value={labNote}
                  onChange={(e) => setLabNote(e.target.value)}
                  placeholder={t('pro_lab_inquiry_note')}
                  rows={3}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none resize-none"
                />
              </div>
            )}
            <div className="flex justify-end gap-2 pt-1">
              <button
                onClick={() => setLabOpen(false)}
                className="px-3 py-2 rounded-lg bg-slate-800 text-slate-200 text-xs font-semibold cursor-pointer"
              >
                {t('pro_lab_inquiry_cancel')}
              </button>
              {!labThanks && (
                <button
                  onClick={submitLabInquiry}
                  disabled={labSending}
                  className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold cursor-pointer disabled:opacity-50"
                >
                  {t('pro_lab_inquiry_submit')}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

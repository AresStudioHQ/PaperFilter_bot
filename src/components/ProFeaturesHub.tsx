import React, { useState } from 'react';
import {
  Crown,
  Sparkles,
  MessageSquare,
  SlidersHorizontal,
  CheckCircle2,
  Send,
  Copy,
  Check,
  Code2,
} from 'lucide-react';
import { Paper, LibraryChatMessage, MatrixRow, UserProfile } from '../types';
import { useI18n, localeFromLang } from '../i18n';
import {
  TIER_DEFS,
  TIER_PRICES,
  TIER_ORDER,
  TIER_RANK,
  TIER_PITCH_KEY,
  hasPaidTier,
  isUnlimited,
  normalizeTier,
} from '../subscriptionTiers';

interface ProFeaturesHubProps {
  user: UserProfile;
  library: Paper[];
  onRedeemCode: (code: string) => Promise<void> | void;
  onSelectPaperForDeep?: (paper: Paper) => void;
  model?: string;
  userLang: string;
}

export const ProFeaturesHub: React.FC<ProFeaturesHubProps> = ({
  user,
  library,
  onRedeemCode,
  model,
  userLang,
}) => {
  const { t } = useI18n(userLang);
  const fmt = (n: number) => (isUnlimited(n) ? t('tier_drive_unlimited') : String(n));
  const timeLocale = localeFromLang(userLang);
  const nowTime = () => new Date().toLocaleTimeString(timeLocale);
  const paid = hasPaidTier(user.tier);
  const currentTier = paid ? 'pro' : 'free';
  const curRank = TIER_RANK[normalizeTier(user.tier)];

  const [activeProTab, setActiveProTab] = useState<'chat' | 'matrix' | 'plans'>(
    paid ? 'chat' : 'plans'
  );

  const [chatMessages, setChatMessages] = useState<LibraryChatMessage[]>([
    {
      id: 'm1',
      role: 'assistant',
      content: t('pro_chat_welcome', { count: library.length }),
      timestamp: nowTime(),
    },
  ]);
  const [chatInput, setChatInput] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);

  const [matrixData, setMatrixData] = useState<MatrixRow[]>([]);
  const [isMatrixLoading, setIsMatrixLoading] = useState(false);
  const [copiedLatex, setCopiedLatex] = useState(false);
  const [copiedMdTable, setCopiedMdTable] = useState(false);

  const [redeemCode, setRedeemCode] = useState('');
  const [redeemBusy, setRedeemBusy] = useState(false);
  const [redeemFeedback, setRedeemFeedback] = useState<{ ok: boolean; text: string } | null>(null);
  const [waitlistMsg, setWaitlistMsg] = useState<string | null>(null);

  const handleSendChat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || isChatLoading) return;

    const userQ = chatInput.trim();
    setChatInput('');
    const userMsg: LibraryChatMessage = {
      id: `u_${Date.now()}`,
      role: 'user',
      content: userQ,
      timestamp: nowTime(),
    };
    setChatMessages((prev) => [...prev, userMsg]);
    setIsChatLoading(true);

    try {
      const res = await fetch('/api/pro/chat-library', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: userQ, papers: library, model }),
      });
      const data = await res.json();
      if (data.success) {
        setChatMessages((prev) => [
          ...prev,
          {
            id: `a_${Date.now()}`,
            role: 'assistant',
            content: data.answer,
            cited_papers: data.cited_papers,
            timestamp: nowTime(),
          },
        ]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsChatLoading(false);
    }
  };

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
        body: JSON.stringify({ papers: library.slice(0, 5), model }),
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

  const handleCopyLatexTable = () => {
    if (matrixData.length === 0) return;
    const latexCode = `\\begin{table*}[htbp]
\\centering
\\caption{Comparative Literature Matrix of Key Baseline Methodologies}
\\label{tab:lit_matrix}
\\begin{tabular}{p{3.5cm} p{2.2cm} p{3.5cm} p{4.0cm} p{2.8cm}}
\\toprule
\\textbf{Paper \\& Year} & \\textbf{Target Problem} & \\textbf{Core Innovation} & \\textbf{Key Benchmark / Metric} & \\textbf{Known Bottleneck} \\\\
\\midrule
${matrixData.map((r) => `${r.title.replace(/_/g, '\\_')} (${r.year}) & ${r.pain_point} & ${r.core_method} & ${r.key_metric} & ${r.limitations} \\\\`).join('\n\\midrule\n')}
\\bottomrule
\\end{tabular}
\\end{table*}`;

    navigator.clipboard.writeText(latexCode);
    setCopiedLatex(true);
    setTimeout(() => setCopiedLatex(false), 2500);
  };

  const handleCopyMdTable = () => {
    if (matrixData.length === 0) return;
    const md = `| ${t('pro_matrix_header_title')} (${t('pro_matrix_header_year')}) | ${t('section_motivation')} | ${t('section_method')} | ${t('section_findings')} | ${t('section_limits')} |
|---|---|---|---|---|
${matrixData.map((r) => `| **${r.title}** (${r.authors}, ${r.year}) | ${r.pain_point} | ${r.core_method} | ${r.key_metric} | ${r.limitations} |`).join('\n')}`;

    navigator.clipboard.writeText(md);
    setCopiedMdTable(true);
    setTimeout(() => setCopiedMdTable(false), 2500);
  };

  const handleRedeemSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const code = redeemCode.trim();
    if (!code || redeemBusy) return;
    setRedeemBusy(true);
    setRedeemFeedback(null);
    try {
      await onRedeemCode(code);
      setRedeemFeedback({ ok: true, text: t('pro_redeem_ok') });
      setRedeemCode('');
    } catch (err) {
      const msg = err instanceof Error && err.message ? err.message : t('pro_redeem_fail');
      setRedeemFeedback({ ok: false, text: msg });
    } finally {
      setRedeemBusy(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-amber-950/90 via-slate-900 to-indigo-950/90 border border-amber-500/40 p-6 md:p-8 shadow-2xl">
        <div className="absolute -right-16 -top-16 w-80 h-80 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 text-xs font-bold rounded-full bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-md flex items-center gap-1.5">
                <Crown className="h-3.5 w-3.5" />
                {t('pro_hero_title')}
              </span>
              <span className="text-[11px] px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-semibold">
                {t('pro_current_plan')}: {t('tier_' + currentTier)}
              </span>
            </div>
            <h2 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
              {t('pro_hero_sub')}
            </h2>
            <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
              {t('pro_hero_desc')}
            </p>
          </div>

          <button
            onClick={() => setActiveProTab('plans')}
            className="px-6 py-3.5 rounded-xl bg-gradient-to-r from-amber-500 via-orange-500 to-amber-600 hover:from-amber-600 hover:to-orange-700 text-white font-bold text-sm shadow-xl shadow-amber-500/30 transition-all flex items-center justify-center gap-2 cursor-pointer"
          >
            <Crown className="h-4 w-4" />
            <span>{t('pro_btn_view_plans')}</span>
          </button>
        </div>

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
            onClick={() => setActiveProTab('plans')}
            className={`px-3.5 py-2 rounded-xl font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
              activeProTab === 'plans'
                ? 'bg-amber-500 text-white shadow-md'
                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700'
            }`}
          >
            <Crown className="h-3.5 w-3.5" />
            <span>{t('tab_plans')}</span>
          </button>
        </div>
      </div>

      {activeProTab === 'chat' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <MessageSquare className="h-5 w-5 text-amber-400" />
                <span>{t('pro_chat_title')}</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">{t('pro_chat_sub')}</p>
            </div>
            <span className="text-xs px-2.5 py-1 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30 font-medium">
              {t('pro_rag_enhanced')}
            </span>
          </div>

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

                  <div className="text-[10px] text-slate-400 text-right">{msg.timestamp}</div>
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

      {activeProTab === 'matrix' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <SlidersHorizontal className="h-5 w-5 text-cyan-400" />
                <span>{t('pro_matrix_title')}</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">{t('pro_matrix_sub')}</p>
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
              <p className="text-xs text-slate-400 max-w-md mx-auto">{t('pro_matrix_empty_sub')}</p>
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

      {activeProTab === 'plans' && (
        <div className="space-y-6">
          <p className="text-xs text-amber-300/90 text-center">{t('pro_beta_unlock_note')}</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 max-w-3xl mx-auto">
            {TIER_ORDER.map((tc) => {
              const isCurrent = (TIER_RANK[tc] ?? 0) === curRank;
              const isRecommended = tc === 'pro';
              const d = TIER_DEFS[tc];
              const priceLabel =
                TIER_PRICES[tc] === 0 ? 'NT$0' : `NT$${TIER_PRICES[tc]}${t('tier_price_unit')}`;
              return (
                <div
                  key={tc}
                  className={`relative bg-slate-900/90 border rounded-2xl p-6 space-y-4 flex flex-col justify-between ${
                    isRecommended ? 'border-2 border-amber-500/70 shadow-xl' : 'border-slate-800'
                  }`}
                >
                  {isRecommended && (
                    <div className="absolute -top-3 right-4">
                      <span className="px-3 py-1 text-[10px] font-extrabold rounded-full bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-md">
                        ★ {t('tier_pro')}
                      </span>
                    </div>
                  )}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-base font-bold text-white flex items-center gap-1.5">
                        {tc !== 'free' && <Crown className="h-4 w-4 text-amber-400" />}
                        <span>{t('tier_' + tc)}</span>
                      </h3>
                      {isCurrent && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                          {t('tier_current')}
                        </span>
                      )}
                    </div>
                    <div className="flex items-baseline gap-1">
                      <span className="text-xl font-extrabold text-amber-300">{priceLabel}</span>
                    </div>
                    {tc === 'pro' && (
                      <p className="text-[11px] text-slate-400">{t('pro_pricing_soon')}</p>
                    )}
                    <p className="text-xs text-slate-300">{t(TIER_PITCH_KEY[tc])}</p>
                    <ul className="space-y-2 text-xs text-slate-200 pt-2 border-t border-slate-800/80">
                      <li className="flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                        <span>{t('tier_search_daily', { count: fmt(d.daily_search_limit) })}</span>
                      </li>
                      <li className="flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                        <span>{t('tier_deep_daily', { count: fmt(d.daily_deep_limit) })}</span>
                      </li>
                      <li className="flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                        <span>
                          {t('tier_drive')}：
                          {isUnlimited(d.drive_monthly_limit)
                            ? t('tier_drive_unlimited')
                            : t('tier_drive_limit', { count: d.drive_monthly_limit })}
                        </span>
                      </li>
                      <li className="flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                        <span>
                          {t('tier_chat')}：{fmt(d.daily_chat_limit)}
                        </span>
                      </li>
                      <li className="flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                        <span>
                          {t('tier_follow')}：{fmt(d.follow_limit)}
                        </span>
                      </li>
                    </ul>
                  </div>
                </div>
              );
            })}
          </div>

          <form
            onSubmit={handleRedeemSubmit}
            className="max-w-3xl mx-auto bg-slate-900/90 border border-slate-800 rounded-2xl p-5 space-y-3"
          >
            <label className="text-xs font-semibold text-slate-200 block">{t('pro_redeem_label')}</label>
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                type="text"
                value={redeemCode}
                onChange={(e) => setRedeemCode(e.target.value)}
                placeholder={t('pro_redeem_placeholder')}
                className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-500"
              />
              <button
                type="submit"
                disabled={redeemBusy || !redeemCode.trim()}
                className="px-5 py-2.5 bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white rounded-xl text-xs font-bold cursor-pointer"
              >
                {t('pro_redeem_btn')}
              </button>
            </div>
            {redeemFeedback && (
              <p className={`text-xs font-semibold ${redeemFeedback.ok ? 'text-emerald-400' : 'text-rose-400'}`}>
                {redeemFeedback.text}
              </p>
            )}
          </form>
          <div className="max-w-3xl mx-auto text-center space-y-2">
            <button
              type="button"
              onClick={async () => {
                try {
                  const res = await fetch('/api/waitlist', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
                  const data = await res.json();
                  setWaitlistMsg(data.already ? t('waitlist_already') : t('waitlist_ok'));
                } catch {
                  setWaitlistMsg(t('pro_redeem_fail'));
                }
              }}
              className="px-5 py-2.5 bg-slate-800 hover:bg-slate-700 text-amber-200 border border-amber-500/40 rounded-xl text-xs font-bold cursor-pointer"
            >
              {t('waitlist_btn')}
            </button>
            {waitlistMsg && <p className="text-xs text-emerald-400 font-semibold">{waitlistMsg}</p>}
          </div>
        </div>
      )}
    </div>
  );
};

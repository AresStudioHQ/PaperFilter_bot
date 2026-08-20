import React, { useState } from 'react';
import { Sparkles, TrendingUp, BarChart2, Calendar } from 'lucide-react';
import { TrendData } from '../types';

export const TrendsSection: React.FC<{ userLang?: string; model?: string }> = ({ userLang = 'en', model }) => {
  const [topic, setTopic] = useState('Reinforcement Learning');
  const [loading, setLoading] = useState(false);
  const [trendData, setTrendData] = useState<TrendData | null>({
    topic: 'Machine Learning & LLMs',
    total_papers_found: 18,
    year_distribution: {
      '2024': 8,
      '2023': 6,
      '2022': 3,
      '2021': 1,
    },
    recent_publications: [
      'Attention Is All You Need',
      'Language Models are Few-Shot Learners',
      'Direct Preference Optimization: Your Language Model is Secretly a Reward Model',
      'Deep Residual Learning for Image Recognition'
    ],
    ai_analysis: '【主流研究方向】當前聚焦於多模態大模型架構、長上下文理解（Long-Context Reasoning）以及高效微調技術。\n\n【新興技術】自適應強化學習對齊（RLAIF/DPO）與自主智能體（Agentic Workflows）快速普及。\n\n【研究熱度】近 3 年論文發表量呈顯著攀升，算力效率與輕量化模型部署備受關注。\n\n【未來 2-3 年預測】結合物理世界反饋的具身智能（Embodied AI）與神經符號系統將成為下一個學術爆發點。'
  });

  const handleAnalyzeTrend = async (e?: React.FormEvent, customTopic?: string) => {
    if (e) e.preventDefault();
    const t = customTopic || topic;
    if (!t.trim()) return;

    setLoading(true);
    try {
      const res = await fetch('/api/trend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: t, model }),
      });
      const data = await res.json();
      if (data.success) {
        setTrendData(data);
      }
    } catch (err) {
      console.error('Trend analysis error:', err);
    } finally {
      setLoading(false);
    }
  };

  const sampleTopics = ['Quantum Computing', 'CRISPR Gene Editing', 'Diffusion Models', 'Bioinformatics', 'Autonomous Robotics'];

  // Calculate year bars
  const yearEntries = trendData ? Object.entries(trendData.year_distribution).sort((a, b) => Number(b[0]) - Number(a[0])) : [];
  const maxYearCount = Math.max(...yearEntries.map(e => Number(e[1])), 1);

  return (
    <div className="space-y-6">
      {/* Search Header */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <div className="text-center space-y-1.5 max-w-2xl mx-auto">
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-amber-500/10 text-amber-300 text-xs font-semibold border border-amber-500/20 mb-1">
            <TrendingUp className="w-3.5 h-3.5" />
            <span>全球論文發表趨勢與熱度預測引擎</span>
          </div>
          <h2 className="text-2xl font-extrabold text-white">跨庫前沿學術趨勢與 2-3 年預測</h2>
          <p className="text-xs text-slate-400">
            自動採樣近期權威期刊與 arXiv 最新收錄，透過 AI 進行高階趨勢提煉與未來突破方向預測。
          </p>
        </div>

        <form onSubmit={handleAnalyzeTrend} className="max-w-2xl mx-auto flex items-center relative">
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="輸入欲分析的研究領域或關鍵字（如 Quantum Computing）..."
            className="w-full pl-4 pr-32 py-3 bg-slate-950 border border-slate-700 rounded-xl text-white placeholder-slate-500 text-sm focus:outline-none focus:border-amber-500"
          />
          <button
            type="submit"
            disabled={loading}
            className="absolute right-1.5 px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold rounded-lg transition-colors flex items-center space-x-1.5 cursor-pointer"
          >
            {loading ? <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div> : <Sparkles className="w-3.5 h-3.5" />}
            <span>{loading ? '分析中...' : '開始趨勢分析'}</span>
          </button>
        </form>

        <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
          <span className="text-xs text-slate-400">推薦熱門領域：</span>
          {sampleTopics.map(t => (
            <button
              key={t}
              onClick={() => {
                setTopic(t);
                handleAnalyzeTrend(undefined, t);
              }}
              className="text-xs px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 border border-slate-700 transition-colors cursor-pointer"
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Trend Report Details */}
      {trendData && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Year Distribution Chart */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
            <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-slate-800 pb-3">
              <BarChart2 className="w-4 h-4 text-sky-400" />
              發表年份分佈統計（共 {trendData.total_papers_found} 篇樣本）
            </h3>

            <div className="space-y-3 pt-2">
              {yearEntries.length === 0 ? (
                <p className="text-xs text-slate-400">尚無年份分佈資料</p>
              ) : (
                yearEntries.map(([year, count]) => {
                  const pct = Math.round((Number(count) / maxYearCount) * 100);
                  return (
                    <div key={year} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-mono text-slate-300 flex items-center gap-1">
                          <Calendar className="w-3 h-3 text-slate-500" /> {year} 年
                        </span>
                        <span className="font-semibold text-sky-400">{count} 篇</span>
                      </div>
                      <div className="w-full bg-slate-950 h-3 rounded-full overflow-hidden border border-slate-800">
                        <div
                          className="bg-gradient-to-r from-sky-500 to-indigo-500 h-full rounded-full transition-all duration-500"
                          style={{ width: `${pct}%` }}
                        ></div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            <div className="border-t border-slate-800 pt-3 space-y-2">
              <span className="text-xs font-semibold text-slate-300">近期代表性文獻：</span>
              <ul className="text-xs text-slate-400 space-y-1.5 pl-3 list-disc">
                {trendData.recent_publications.slice(0, 4).map((p, i) => (
                  <li key={i} className="line-clamp-1">{p}</li>
                ))}
              </ul>
            </div>
          </div>

          {/* AI Comprehensive Trend Analysis */}
          <div className="lg:col-span-2 bg-slate-900 border border-amber-500/30 rounded-xl p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-amber-400" />
                「{trendData.topic}」領域 AI 前沿趨勢深度解析
              </h3>
              <span className="text-xs px-2.5 py-1 rounded-md bg-amber-500/10 text-amber-300 border border-amber-500/20 font-medium">
                AI 趨勢研判
              </span>
            </div>

            <div className="whitespace-pre-line text-sm text-slate-200 leading-relaxed bg-slate-950/70 p-5 rounded-xl border border-slate-800 font-sans">
              {trendData.ai_analysis}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

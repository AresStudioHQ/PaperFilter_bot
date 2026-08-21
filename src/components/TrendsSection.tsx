import React, { useState } from 'react';
import { Sparkles, TrendingUp, BarChart2, Calendar } from 'lucide-react';
import { TrendData } from '../types';
import { useI18n } from '../i18n';

export const TrendsSection: React.FC<{ userLang?: string; model?: string }> = ({ userLang = 'en', model }) => {
  const { t } = useI18n(userLang);
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
    ai_analysis: t('trend_ai_analysis')
  });

  const handleAnalyzeTrend = async (e?: React.FormEvent, customTopic?: string) => {
    if (e) e.preventDefault();
    const topicToAnalyze = customTopic || topic;
    if (!topicToAnalyze.trim()) return;

    setLoading(true);
    try {
      const res = await fetch('/api/trend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: topicToAnalyze, model }),
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
            <span>{t('trends_engine_badge')}</span>
          </div>
          <h2 className="text-2xl font-extrabold text-white">{t('trends_title')}</h2>
          <p className="text-xs text-slate-400">
            {t('trends_sub')}
          </p>
        </div>

        <form onSubmit={handleAnalyzeTrend} className="max-w-2xl mx-auto flex items-center relative">
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder={t('trends_input_placeholder')}
            className="w-full pl-4 pr-32 py-3 bg-slate-950 border border-slate-700 rounded-xl text-white placeholder-slate-500 text-sm focus:outline-none focus:border-amber-500"
          />
          <button
            type="submit"
            disabled={loading}
            className="absolute right-1.5 px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold rounded-lg transition-colors flex items-center space-x-1.5 cursor-pointer"
          >
            {loading ? <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div> : <Sparkles className="w-3.5 h-3.5" />}
            <span>{loading ? t('trends_btn_analyzing') : t('trends_btn_start')}</span>
          </button>
        </form>

        <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
          <span className="text-xs text-slate-400">{t('trends_recommend_label')}</span>
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
               {t('trends_year_dist', { count: trendData.total_papers_found })}
             </h3>

            <div className="space-y-3 pt-2">
              {yearEntries.length === 0 ? (
                <p className="text-xs text-slate-400">{t('trends_no_year')}</p>
              ) : (
                yearEntries.map(([year, count]) => {
                  const pct = Math.round((Number(count) / maxYearCount) * 100);
                  return (
                    <div key={year} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-mono text-slate-300 flex items-center gap-1">
                          <Calendar className="w-3 h-3 text-slate-500" /> {year} {t('trends_year_unit')}
                        </span>
                        <span className="font-semibold text-sky-400">{count} {t('trends_papers_unit')}</span>
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
              <span className="text-xs font-semibold text-slate-300">{t('trends_recent_papers')}</span>
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
                {t('trends_ai_title', { topic: trendData.topic })}
              </h3>
              <span className="text-xs px-2.5 py-1 rounded-md bg-amber-500/10 text-amber-300 border border-amber-500/20 font-medium">
                {t('trends_ai_badge')}
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

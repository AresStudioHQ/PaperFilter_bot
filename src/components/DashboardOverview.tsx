import React, { useState, useEffect } from 'react';
import { 
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, 
  PieChart, Pie, Cell 
} from 'recharts';
import { 
  BookOpen, 
  Bookmark, 
  EyeOff, 
  BrainCircuit, 
  Sparkles, 
  Flame, 
  TrendingUp, 
  UserCheck, 
  Plus, 
  Trash2, 
  Clock, 
  ArrowUpRight,
  FolderOpen,
  CheckCircle
} from 'lucide-react';
import { UserProfile, HistoryRecord, Paper } from '../types';
import { useI18n, getLocalizedCategory, getLocalizedActivityDetail } from '../i18n';

interface DashboardOverviewProps {
  user: UserProfile;
  history: HistoryRecord[];
  library: Paper[];
  followedAuthors: string[];
  categories?: string[];
  userLang?: string;
  onAddAuthor: (name: string) => void;
  onRemoveAuthor: (name: string) => void;
  onSelectPaperForDeep: (paper: Paper) => void;
  onNavigateToTab: (tab: string) => void;
  onOpenDeep?: (paper: Paper) => void;
  onOpenSyncModal?: () => void;
  onOpenProModal?: () => void;
}

const COLORS = ['#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6'];

export const DashboardOverview: React.FC<DashboardOverviewProps> = ({
  user,
  history,
  library,
  followedAuthors,
  userLang = 'en',
  onAddAuthor,
  onRemoveAuthor,
  onSelectPaperForDeep,
  onNavigateToTab
}) => {
  const { t } = useI18n(userLang);
  const [newAuthorInput, setNewAuthorInput] = useState('');
  const [selectedActionFilter, setSelectedActionFilter] = useState<string>('all');
  const [chartData, setChartData] = useState<{
    reading_trend: any[];
    category_distribution: any[];
  }>({
    reading_trend: [],
    category_distribution: []
  });

  useEffect(() => {
    fetch('/api/analytics/charts')
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          setChartData({
            reading_trend: data.reading_trend,
            category_distribution: data.category_distribution
          });
        }
      })
      .catch(console.error);
  }, [library.length, history.length]);

  const handleAddAuthorSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (newAuthorInput.trim()) {
      onAddAuthor(newAuthorInput.trim());
      setNewAuthorInput('');
    }
  };

  const filteredHistory = history.filter(item => {
    if (selectedActionFilter === 'all') return true;
    return item.action === selectedActionFilter;
  });

  return (
    <div className="space-y-8 animate-fade-in">
      
      {/* Top Banner: Headquarters Hero & Synchronized Status */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-indigo-950/80 to-slate-900 border border-indigo-900/40 p-6 md:p-8 shadow-xl">
        <div className="absolute -right-16 -bottom-16 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center space-x-3">
              <span className="px-3 py-1 text-xs font-semibold rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                Telegram Live Sync
              </span>
              <span className="text-xs text-slate-400">
                Sync Code: <code className="text-indigo-300 font-mono font-bold bg-slate-800/80 px-1.5 py-0.5 rounded">{user.sync_code || 'PF8892'}</code>
              </span>
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
              {t('welcome_back', { name: user.username })}
            </h1>
            <p className="text-sm text-slate-300 max-w-2xl leading-relaxed">
              {t('welcome_sub')}
            </p>
          </div>

          <div className="flex items-center gap-3 self-start md:self-auto">
            <button
              onClick={() => onNavigateToTab('search')}
              className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold shadow-lg shadow-indigo-600/30 transition-all flex items-center gap-2 cursor-pointer"
            >
              <Sparkles className="h-4 w-4" />
              <span>{t('btn_search')}</span>
            </button>
            <button
              onClick={() => onNavigateToTab('pro')}
              className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white text-sm font-semibold shadow-lg shadow-amber-500/20 transition-all flex items-center gap-1.5 cursor-pointer"
            >
              <span>{t('nav_pro')}</span>
              <ArrowUpRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* 4 Key Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 hover:border-indigo-500/40 transition-all shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{t('stat_read')}</span>
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
              <BookOpen className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <div className="text-2xl font-bold text-white">{user.total_read_count}</div>
            <span className="text-xs font-medium text-emerald-400 flex items-center gap-0.5">
              <TrendingUp className="h-3 w-3" /> +18%
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-400">{t('stat_read_sub')}</p>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 hover:border-emerald-500/40 transition-all shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{t('stat_archived')}</span>
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
              <Bookmark className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <div className="text-2xl font-bold text-white">{library.length}</div>
            <span className="text-xs font-medium text-emerald-400">Drive Synced</span>
          </div>
          <p className="mt-2 text-xs text-slate-400">{t('stat_archived_sub')}</p>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 hover:border-rose-500/40 transition-all shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{t('stat_skipped')}</span>
            <div className="p-2 rounded-lg bg-rose-500/10 text-rose-400">
              <EyeOff className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <div className="text-2xl font-bold text-white">{user.total_skipped_count}</div>
            <span className="text-xs font-medium text-slate-400">Noise Filter</span>
          </div>
          <p className="mt-2 text-xs text-slate-400">{t('stat_skipped_sub')}</p>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 hover:border-amber-500/40 transition-all shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{t('stat_deep')}</span>
            <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400">
              <BrainCircuit className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <div className="text-2xl font-bold text-white">{user.total_deep_read_count}</div>
            <span className="text-xs font-medium text-amber-400">4D Insights</span>
          </div>
          <p className="mt-2 text-xs text-slate-400">{t('stat_deep_sub')}</p>
        </div>

      </div>

      {/* Visual Analytics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Main Growth Area Chart (2 cols) */}
        <div className="lg:col-span-2 bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Flame className="h-5 w-5 text-indigo-400" />
                <span>{t('trend_card_title')}</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">{t('trend_card_sub')}</p>
            </div>
            <div className="flex items-center gap-3 text-xs">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-indigo-500"></span>
                <span className="text-slate-300">{t('chart_searches')}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
                <span className="text-slate-300">{t('chart_archived')}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
                <span className="text-slate-300">{t('chart_deep')}</span>
              </div>
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData.reading_trend.length > 0 ? chartData.reading_trend : [
                { date: '8/12', searches: 12, archived: 3, deep_reads: 2 },
                { date: '8/13', searches: 15, archived: 4, deep_reads: 3 },
                { date: '8/14', searches: 9, archived: 2, deep_reads: 1 },
                { date: '8/15', searches: 22, archived: 6, deep_reads: 5 },
                { date: '8/16', searches: 18, archived: 5, deep_reads: 3 },
                { date: '8/17', searches: 25, archived: 7, deep_reads: 6 },
                { date: '8/18', searches: 20, archived: 5, deep_reads: 4 },
              ]}>
                <defs>
                  <linearGradient id="colorSearches" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorArchived" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorDeep" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" stroke="#64748b" fontSize={12} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem', color: '#fff', fontSize: '12px' }}
                />
                <Area type="monotone" dataKey="searches" stroke="#6366f1" strokeWidth={2} fillOpacity={1} fill="url(#colorSearches)" name={t('chart_searches')} />
                <Area type="monotone" dataKey="archived" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#colorArchived)" name={t('chart_archived')} />
                <Area type="monotone" dataKey="deep_reads" stroke="#f59e0b" strokeWidth={2} fillOpacity={1} fill="url(#colorDeep)" name={t('chart_deep')} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Subject Breakdown Pie Chart (1 col) */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-sm flex flex-col justify-between">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <FolderOpen className="h-5 w-5 text-cyan-400" />
              <span>{t('pie_card_title')}</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">{t('pie_card_sub')}</p>
          </div>

          <div className="h-48 w-full my-2">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={(chartData.category_distribution.length > 0 ? chartData.category_distribution : [
                    { name: t('dash_cat_ai'), value: 14 },
                    { name: t('dash_cat_life'), value: 5 },
                    { name: t('dash_cat_quantum'), value: 3 },
                    { name: t('dash_cat_general'), value: 2 },
                  ]).map(item => ({
                    ...item,
                    name: getLocalizedCategory(item.name, userLang)
                  }))}
                  cx="50%"
                  cy="50%"
                  innerRadius={45}
                  outerRadius={70}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {(chartData.category_distribution.length > 0 ? chartData.category_distribution : [
                    { name: t('dash_cat_ai'), value: 14 },
                    { name: t('dash_cat_life'), value: 5 },
                    { name: t('dash_cat_quantum'), value: 3 },
                    { name: t('dash_cat_general'), value: 2 },
                  ]).map((_entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem', color: '#fff', fontSize: '12px' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs">
            {(chartData.category_distribution.length > 0 ? chartData.category_distribution : [
              { name: t('dash_cat_ai'), value: 14 },
              { name: t('dash_cat_life'), value: 5 },
              { name: t('dash_cat_quantum'), value: 3 },
              { name: t('dash_cat_general'), value: 2 },
            ]).map((item, idx) => {
              const localizedName = getLocalizedCategory(item.name, userLang);
              return (
                <div key={item.name + idx} className="flex items-center gap-1.5 text-slate-300">
                  <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: COLORS[idx % COLORS.length] }}></span>
                  <span className="truncate">{localizedName} ({item.value})</span>
                </div>
              );
            })}
          </div>
        </div>

      </div>

      {/* Followed Authors Radar & Activity Stream Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left: Followed Authors Management (1 col) */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-base font-bold text-white flex items-center gap-2 shrink-0">
              <UserCheck className="h-5 w-5 text-indigo-400" />
              <span>{t('authors_card_title')}</span>
            </h3>
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 shrink-0 text-right">
              {t('authors_desc')}
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Telegram: <code>/follow AuthorName</code>
          </p>

          <form onSubmit={handleAddAuthorSubmit} className="flex gap-2">
            <input
              type="text"
              value={newAuthorInput}
              onChange={(e) => setNewAuthorInput(e.target.value)}
              placeholder="e.g., Yann LeCun, Hinton"
              className="flex-1 bg-slate-800/80 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
            <button
              type="submit"
              className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1 transition-colors cursor-pointer"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>{t('authors_add_btn')}</span>
            </button>
          </form>

          <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
            {followedAuthors.map((author) => (
              <div
                key={author}
                className="flex items-center justify-between p-2.5 rounded-xl bg-slate-800/50 border border-slate-700/60 text-xs hover:border-indigo-500/40 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-full bg-indigo-600/30 text-indigo-300 flex items-center justify-center font-bold text-[10px]">
                    {author.charAt(0)}
                  </div>
                  <span className="font-medium text-slate-200">{author}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => {
                      onNavigateToTab('search');
                    }}
                    className="text-[11px] text-indigo-400 hover:text-indigo-300 px-1.5 py-0.5 rounded hover:bg-indigo-500/10 cursor-pointer"
                    title="Search Author"
                  >
                    Search
                  </button>
                  <button
                    onClick={() => onRemoveAuthor(author)}
                    className="text-slate-500 hover:text-rose-400 p-1 transition-colors cursor-pointer"
                    title="Unfollow"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Full Telegram Action History Stream (2 cols) */}
        <div className="lg:col-span-2 bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Clock className="h-5 w-5 text-indigo-400" />
                <span>{t('recent_activity')}</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">{t('recent_activity_sub')}</p>
            </div>

            {/* Filter Pills */}
            <div className="flex items-center gap-1 bg-slate-800/70 p-1 rounded-lg border border-slate-700 text-xs overflow-x-auto">
              <button
                onClick={() => setSelectedActionFilter('all')}
                className={`px-2.5 py-1 rounded transition-colors cursor-pointer ${
                  selectedActionFilter === 'all' ? 'bg-indigo-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {t('filter_all')}
              </button>
              <button
                onClick={() => setSelectedActionFilter('archive')}
                className={`px-2.5 py-1 rounded transition-colors cursor-pointer ${
                  selectedActionFilter === 'archive' ? 'bg-emerald-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                📥 Drive
              </button>
              <button
                onClick={() => setSelectedActionFilter('deep_read')}
                className={`px-2.5 py-1 rounded transition-colors cursor-pointer ${
                  selectedActionFilter === 'deep_read' ? 'bg-amber-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                🔍 4D Deep
              </button>
              <button
                onClick={() => setSelectedActionFilter('seen')}
                className={`px-2.5 py-1 rounded transition-colors cursor-pointer ${
                  selectedActionFilter === 'seen' ? 'bg-blue-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                👁️ Seen
              </button>
              <button
                onClick={() => setSelectedActionFilter('skip')}
                className={`px-2.5 py-1 rounded transition-colors cursor-pointer ${
                  selectedActionFilter === 'skip' ? 'bg-rose-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                ❌ Skip
              </button>
            </div>
          </div>

          <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
            {filteredHistory.length === 0 ? (
              <p className="text-xs text-slate-500 py-6 text-center">{t('no_activity')}</p>
            ) : (
              filteredHistory.map((item) => (
                <div
                  key={item.id}
                  className="p-3.5 rounded-xl bg-slate-800/40 border border-slate-800 hover:border-slate-700 transition-all flex items-start justify-between gap-3 text-xs"
                >
                  <div className="flex items-start gap-3">
                    <div className={`mt-0.5 p-1.5 rounded-lg shrink-0 ${
                      item.action === 'archive' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                      item.action === 'deep_read' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                      item.action === 'seen' ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' :
                      item.action === 'skip' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' :
                      'bg-slate-700 text-slate-300'
                    }`}>
                      {item.action === 'archive' && <Bookmark className="h-4 w-4" />}
                      {item.action === 'deep_read' && <BrainCircuit className="h-4 w-4" />}
                      {item.action === 'seen' && <CheckCircle className="h-4 w-4" />}
                      {item.action === 'skip' && <EyeOff className="h-4 w-4" />}
                      {item.action === 'search' && <BookOpen className="h-4 w-4" />}
                    </div>

                    <div>
                      <h4 className="font-semibold text-slate-200 line-clamp-1">{item.paper_title}</h4>
                      {item.details && (
                        <p className="text-slate-400 text-[11px] mt-0.5">
                          {getLocalizedActivityDetail(item.action, item.details, item.category || '', userLang)}
                        </p>
                      )}
                      <div className="flex items-center gap-2 mt-1.5 text-[10px] text-slate-500">
                        {item.source && <span className="bg-slate-800 px-1.5 py-0.5 rounded text-slate-300">{item.source}</span>}
                        {item.category && (
                          <span className="bg-indigo-950/60 text-indigo-300 px-1.5 py-0.5 rounded">
                            {getLocalizedCategory(item.category, userLang)}
                          </span>
                        )}
                        <span>{new Date(item.timestamp).toLocaleString()}</span>
                      </div>
                    </div>
                  </div>

                  {item.paper_id && (
                    <button
                      onClick={() => {
                        const found = library.find(p => p.id === item.paper_id);
                        if (found) {
                          onSelectPaperForDeep(found);
                        } else {
                          onSelectPaperForDeep({
                            id: item.paper_id || 'p',
                            fingerprint: 'fp',
                            title: item.paper_title,
                            summary: item.details || '',
                            authors: item.authors || ['Research Team'],
                            year: item.year || '2024',
                            source: item.source || 'Scholar',
                            link: '#',
                            citations: 50,
                            is_open_access: true,
                            is_top_journal: true
                          });
                        }
                      }}
                      className="shrink-0 text-indigo-400 hover:text-indigo-300 font-medium text-[11px] flex items-center gap-1 bg-indigo-500/10 px-2 py-1 rounded hover:bg-indigo-500/20 transition-colors cursor-pointer"
                    >
                      <span>{t('btn_deep_read')}</span>
                      <ArrowUpRight className="h-3 w-3" />
                    </button>
                  )}
                </div>
              ))
            )}
          </div>

        </div>

      </div>

    </div>
  );
};

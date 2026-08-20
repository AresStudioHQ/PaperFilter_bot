export type Language = 'zh_hant' | 'zh_hans' | 'en' | 'ja';

export const TRANSLATIONS: Record<Language, Record<string, string>> = {
  zh_hant: {
    // Top Navbar
    brand_title: 'PaperFilterBot',
    brand_sub: 'Telegram 跨端學術情報與雲端文獻總庫',
    nav_dashboard: '科研儀表板',
    nav_library: '文獻中樞庫',
    nav_search: '4大庫檢索',
    nav_graph: '知識圖譜',
    nav_pro: '👑 Pro 專區',
    nav_trends: '學術趨勢',
    nav_simulator: 'TG 模擬器',
    nav_source: '後端代碼',
    mode_smart: '🧠 智能平衡',
    mode_top_tier: '🏆 頂刊優先',
    mode_free_only: '🟢 免費 OA',
    tg_linked: '已連線 TG',
    tg_bind: '綁定 TG',
    pro_badge: 'PRO',
    upgrade_pro: '升級 Pro',

    // Dashboard Overview
    welcome_back: '歡迎回來，{name}',
    welcome_sub: '雙軌 Google Drive 雲端同步 · 4 大官方學術庫即時監控 · references.bib 自動維護',
    stat_read: '累計調研文獻',
    stat_archived: '雲端歸檔總數',
    stat_deep: '4D 深度導讀',
    stat_skipped: '略過偏好調整',
    stat_read_sub: '含 arXiv / PubMed / S2',
    stat_archived_sub: '已同步至 Google Drive',
    stat_deep_sub: '4維結構化拆解報告',
    stat_skipped_sub: '智慧負向權重降噪',
    folders_card_title: 'Google Drive 分類資料夾',
    folders_count: '共 {count} 個',
    folders_add_btn: '新增資料夾',
    authors_card_title: '追蹤學者雷達',
    authors_desc: '新著作自動加權 +50 分',
    authors_add_btn: '追蹤學者',
    recent_activity: '最近科研調研軌跡',
    recent_activity_sub: '即時記錄 Telegram 與網頁端之調研、歸檔與導讀行為',
    view_all_history: '查看全部歷史',
    trend_card_title: '本週科研調研活躍趨勢',
    trend_card_sub: '檢索次數 vs 歸檔論文數 (每日分佈)',
    chart_searches: '檢索次數',
    chart_archived: '已歸檔',
    chart_deep: '4D 導讀',
    pie_card_title: '文獻庫領域分佈',
    pie_card_sub: '依 Google Drive 分類資料夾統計',
    no_activity: '暫無調研軌跡，在檢索頁面或 Telegram 中開始探索吧！',

    // Library Management
    lib_title: '個人科研文獻總庫',
    lib_sub: '共 {count} 篇文獻 · Google Drive 雙向同步 · references.bib 即時維護',
    btn_export_bib: '匯出 BibTeX',
    btn_export_ris: '匯出 RIS',
    btn_export_csv: '匯出 CSV',
    search_lib_placeholder: '在文獻庫中搜尋標題、作者、標籤或筆記...',
    filter_all: '全部文獻',
    filter_starred: '⭐ 標星重點',
    btn_deep_analysis: '4維深度導讀',
    btn_remove_paper: '移出庫',
    btn_save_notes: '保存筆記',
    notes_placeholder: '輸入這篇文獻的研究筆記、實驗想法或論文審稿意見...',
    tag_placeholder: '新增標籤 (按 Enter 鍵)',
    empty_library: '文獻庫中尚無文獻',
    empty_library_sub: '前往「4大庫檢索」頁面或在 Telegram Bot 中發送關鍵字，點擊「歸檔到雲端」即可收藏！',

    // Search Section
    search_title: '全球 4 大官方學術庫即時檢索',
    search_sub: 'arXiv · PubMed · Semantic Scholar · CrossRef (3.5億+篇) 智慧權重推薦',
    search_input_placeholder: '輸入論文關鍵字、DOI 或主題 (例如：Transformer, CRISPR, LLM Alignment)...',
    btn_search: '跨庫搜尋',
    searching: '正在交叉檢索 4 大學術庫與權重過濾...',
    hot_topics_label: '熱門研究方向：',
    btn_archive_drive: '☁️ 歸檔到 Drive',
    btn_already_archived: '✅ 已歸檔',
    btn_deep_read: '💡 4D 深度導讀',
    btn_read_source: '查看官方原文',
    search_results_count: '找到 {count} 篇符合條件的頂尖論文',
    no_search_results: '未找到符合條件的文獻，請嘗試調整關鍵字或更換過濾模式。',

    // Citation Graph
    graph_title: '文獻知識拓撲與引用網絡圖譜',
    graph_sub: '動態視覺化學術傳承脈絡 · 識別開山奠基之作 · 探索研究前沿聚類',
    layout_force: '🕸️ 引力拓撲',
    layout_timeline: '📅 年代傳承軸',
    layout_clusters: '🧬 領域聚合圈',
    export_svg: '📸 匯出 SVG 插圖',
    reset_view: '🔄 重置視角',
    legend_seminal: '開山奠基文獻 (引用 > 10,000)',
    legend_selected: '目前選中文獻',
    legend_regular: '常規研究節點',
    drawer_title: '論文拓撲詳細情報',
    drawer_add_matrix: '📊 匯入對比矩陣',
    drawer_deep: '💡 4D 深度導讀',
    graph_hint: '💡 提示：按住節點可自由拖曳排版；滾輪可縮放畫布；點擊節點展開傳承關係。',

    // Pro Features Hub
    pro_title: 'PaperFilterBot Pro 科研大師工作站',
    pro_sub: '跨文獻 RAG 智慧對話 · LaTeX 三線對比矩陣 · Overleaf 綜述起草 · 研究缺口雷達',
    tab_rag: '💬 跨文獻 RAG 問答',
    tab_matrix: '📊 結構化對比矩陣',
    tab_writer: '📑 論文綜述起草器',
    tab_gap: '🎯 研究缺口掃描',
    tab_radar: '📡 頂尖學者雷達',
    tab_roi: '💰 價值計算機',
    btn_copy_latex: '複製 LaTeX 代碼',
    btn_copy_markdown: '複製 Markdown',
    btn_copy_bibtex: '複製 BibTeX',
    btn_generate: '立即生成',
    btn_export_overleaf: '匯出 Overleaf .tex 專案',
    rag_input_placeholder: '向您的文獻庫提問（例如：對比 Transformer 與 DPO 在優化目標上的本質差異）...',
    matrix_gen_btn: '⚡ 生成多篇結構化橫向對比矩陣',
    writer_gen_btn: '🚀 生成頂刊級論文草稿與 Overleaf 專案',
    gap_gen_btn: '🔍 執行全庫研究矛盾與盲點掃描',

    // Deep Modal
    deep_modal_title: 'AI 4 維全景結構化深度導讀報告',
    tab_overview: '全景結構拆解',
    tab_bibtex: 'BibTeX 引用',
    section_motivation: '🎯 研究痛點與動機',
    section_method: '⚙️ 核心方法與技術創新',
    section_findings: '📊 關鍵發現與突破數據',
    section_limits: '⚠️ 研究限制與未來方向',
    btn_copy_bib: '複製 BibTeX 條目',
    btn_close: '關閉',

    // Telegram Binding Modal
    bind_modal_title: '綁定 Telegram 帳號與雙向雲端同步',
    step1_title: '在 Telegram 開啟機器人',
    step2_title: '發送指令取得同步碼',
    step3_title: '輸入 6 位數同步碼',
    step1_desc: '在 Telegram 搜尋 @PaperFilterBot 或開啟對話',
    step2_desc: '發送指令 /bind 或 /web 獲取專屬 6 位數代碼',
    step3_desc: '在下方輸入代碼，即可完成實時雙向連線',
    btn_confirm_sync: '確認並開始雙向同步',
    sync_code_placeholder: '例如：PF8892',

    // Subscription Tiers
    tier_free: '免費版',
    tier_basic: 'Basic 方案',
    tier_standard: 'Standard 方案',
    tier_premium: 'Premium 方案',
    tier_ultra: 'Ultra 方案',
    tier_price: '{price}/月',
    tier_search_daily: '{count} 次搜尋/日',
    tier_deep_daily: '{count} 次深度導讀/日',
    tier_chat: '跨文獻問答',
    tier_review: '文獻綜述',
    tier_gap: '研究缺口',
    tier_drive: 'Google Drive 歸檔',
    tier_drive_limit: '{count} 篇/月',
    tier_drive_unlimited: '無限',
    tier_follow: '追蹤學者',
    tier_folder: '自訂資料夾',
    tier_export: '匯出功能',
    tier_report: 'AI 分析報告',
    tier_report_none: '無',
    tier_report_monthly: '每月 1 份',
    tier_report_weekly: '每週 1 份',
    tier_report_daily: '每日 1 份',
    tier_ads: '網頁端廣告',
    tier_ads_none: '無廣告',
    tier_ads_show: '有廣告',
    tier_unlock: '解鎖',
    tier_locked: '需升級',
    tier_current: '目前方案',
    tier_upgrade: '升級方案',
    tier_select_model: '選擇 AI 模型',
    tier_model_available: '可用模型：{count} 個',
    tier_model_locked: '需升級至 {tier}',

    // Upgrade Prompt
    upgrade_title: '🔒 此功能需要升級方案',
    upgrade_current_tier: '您目前的方案',
    upgrade_compare: '方案比較',
    upgrade_btn: '查看升級方案',
    upgrade_drive_limited: '本月 Drive 額度已用完，下個月自動同步',

    // Footer
    footer_hq: 'PaperFilterBot 科研大總部',
    footer_langs: '支援 繁體中文 / 简体中文 / English / 日本語 4 國語言指令與介面',
    footer_sources: 'arXiv · PubMed · Semantic Scholar · CrossRef · Google Drive 雙軌自動歸檔',
  },

  zh_hans: {
    // Top Navbar
    brand_title: 'PaperFilterBot',
    brand_sub: 'Telegram 跨端学术情报与云端文献总库',
    nav_dashboard: '科研仪表板',
    nav_library: '文献中枢库',
    nav_search: '4大库检索',
    nav_graph: '知识图谱',
    nav_pro: '👑 Pro 专区',
    nav_trends: '学术趋势',
    nav_simulator: 'TG 模拟器',
    nav_source: '后端代码',
    mode_smart: '🧠 智能平衡',
    mode_top_tier: '🏆 顶刊优先',
    mode_free_only: '🟢 免费 OA',
    tg_linked: '已连线 TG',
    tg_bind: '绑定 TG',
    pro_badge: 'PRO',
    upgrade_pro: '升级 Pro',

    // Dashboard Overview
    welcome_back: '欢迎回来，{name}',
    welcome_sub: '双轨 Google Drive 云端同步 · 4 大官方学术库实时监控 · references.bib 自动维护',
    stat_read: '累计调研文献',
    stat_archived: '云端归档总数',
    stat_deep: '4D 深度导读',
    stat_skipped: '略过偏好调整',
    stat_read_sub: '含 arXiv / PubMed / S2',
    stat_archived_sub: '已同步至 Google Drive',
    stat_deep_sub: '4维结构化拆解报告',
    stat_skipped_sub: '智能负向权重降噪',
    folders_card_title: 'Google Drive 分类文件夹',
    folders_count: '共 {count} 个',
    folders_add_btn: '新增文件夹',
    authors_card_title: '追踪学者雷达',
    authors_desc: '新著作自动加权 +50 分',
    authors_add_btn: '追踪学者',
    recent_activity: '最近科研调研轨迹',
    recent_activity_sub: '实时记录 Telegram 与网页端之调研、归档与导读行为',
    view_all_history: '查看全部历史',
    trend_card_title: '本周科研调研活跃趋势',
    trend_card_sub: '检索次数 vs 归档论文数 (每日分布)',
    chart_searches: '检索次数',
    chart_archived: '已归档',
    chart_deep: '4D 导读',
    pie_card_title: '文献库领域分布',
    pie_card_sub: '依 Google Drive 分类文件夹统计',
    no_activity: '暂无调研轨迹，在检索页面或 Telegram 中开始探索吧！',

    // Library Management
    lib_title: '个人科研文献总库',
    lib_sub: '共 {count} 篇文献 · Google Drive 双向同步 · references.bib 实时维护',
    btn_export_bib: '导出 BibTeX',
    btn_export_ris: '导出 RIS',
    btn_export_csv: '导出 CSV',
    search_lib_placeholder: '在文献库中搜索标题、作者、标签或笔记...',
    filter_all: '全部文献',
    filter_starred: '⭐ 标星重点',
    btn_deep_analysis: '4维深度导读',
    btn_remove_paper: '移出库',
    btn_save_notes: '保存笔记',
    notes_placeholder: '输入这篇文献的研究笔记、实验想法或论文审稿意见...',
    tag_placeholder: '新增标签 (按 Enter 键)',
    empty_library: '文献库中尚无文献',
    empty_library_sub: '前往「4大库检索」页面或在 Telegram Bot 中发送关键词，点击「归档到云端」即可收藏！',

    // Search Section
    search_title: '全球 4 大官方学术库实时检索',
    search_sub: 'arXiv · PubMed · Semantic Scholar · CrossRef (3.5亿+篇) 智能权重推荐',
    search_input_placeholder: '输入论文关键词、DOI 或主题 (例如：Transformer, CRISPR, LLM Alignment)...',
    btn_search: '跨库搜索',
    searching: '正在交叉检索 4 大学术库与权重过滤...',
    hot_topics_label: '热门研究方向：',
    btn_archive_drive: '☁️ 归档到 Drive',
    btn_already_archived: '✅ 已归档',
    btn_deep_read: '💡 4D 深度导读',
    btn_read_source: '查看官方原文',
    search_results_count: '找到 {count} 篇符合条件的顶尖论文',
    no_search_results: '未找到符合条件的文献，请尝试调整关键词或更换过滤模式。',

    // Citation Graph
    graph_title: '文献知识拓扑与引用网络图谱',
    graph_sub: '动态可视化学术传承脉络 · 识别开山奠基之作 · 探索研究前沿聚类',
    layout_force: '🕸️ 引力拓扑',
    layout_timeline: '📅 年代传承轴',
    layout_clusters: '🧬 领域聚合圈',
    export_svg: '📸 导出 SVG 插图',
    reset_view: '🔄 重置视角',
    legend_seminal: '开山奠基文献 (引用 > 10,000)',
    legend_selected: '当前选中选中文献',
    legend_regular: '常规研究节点',
    drawer_title: '论文拓扑详细情报',
    drawer_add_matrix: '📊 导入对比矩阵',
    drawer_deep: '💡 4D 深度导读',
    graph_hint: '💡 提示：按住节点可自由拖拽排版；滚轮可缩放画布；点击节点展开传承关系。',

    // Pro Features Hub
    pro_title: 'PaperFilterBot Pro 科研大师工作站',
    pro_sub: '跨文献 RAG 智能对话 · LaTeX 三线对比矩阵 · Overleaf 综述起草 · 研究缺口雷达',
    tab_rag: '💬 跨文献 RAG 问答',
    tab_matrix: '📊 结构化对比矩阵',
    tab_writer: '📑 论文综述起草器',
    tab_gap: '🎯 研究缺口扫描',
    tab_radar: '📡 顶尖学者雷达',
    tab_roi: '💰 价值计算器',
    btn_copy_latex: '复制 LaTeX 代码',
    btn_copy_markdown: '复制 Markdown',
    btn_copy_bibtex: '复制 BibTeX',
    btn_generate: '立即生成',
    btn_export_overleaf: '导出 Overleaf .tex 项目',
    rag_input_placeholder: '向您的文献库提问（例如：对比 Transformer 与 DPO 在优化目标上的本质差异）...',
    matrix_gen_btn: '⚡ 生成多篇结构化横向对比矩阵',
    writer_gen_btn: '🚀 生成顶刊级论文草稿与 Overleaf 项目',
    gap_gen_btn: '🔍 执行全库研究矛盾与盲点扫描',

    // Deep Modal
    deep_modal_title: 'AI 4 维全景结构化深度导读报告',
    tab_overview: '全景结构拆解',
    tab_bibtex: 'BibTeX 引用',
    section_motivation: '🎯 研究痛点与动机',
    section_method: '⚙️ 核心方法与技术创新',
    section_findings: '📊 关键发现与突破数据',
    section_limits: '⚠️ 研究限制与未来方向',
    btn_copy_bib: '复制 BibTeX 条目',
    btn_close: '关闭',

    // Telegram Binding Modal
    bind_modal_title: '绑定 Telegram 账号与双向云端同步',
    step1_title: '在 Telegram 开启机器人',
    step2_title: '发送指令获取同步码',
    step3_title: '输入 6 位数同步码',
    step1_desc: '在 Telegram 搜索 @PaperFilterBot 或开启对话',
    step2_desc: '发送指令 /bind 或 /web 获取专属 6 位代码',
    step3_desc: '在下方输入代码，即可完成实时双向连线',
    btn_confirm_sync: '确认并开始双向同步',
    sync_code_placeholder: '例如：PF8892',

    // Subscription Tiers
    tier_free: '免费版',
    tier_basic: 'Basic 方案',
    tier_standard: 'Standard 方案',
    tier_premium: 'Premium 方案',
    tier_ultra: 'Ultra 方案',
    tier_price: '{price}/月',
    tier_search_daily: '{count} 次搜索/日',
    tier_deep_daily: '{count} 次深度导读/日',
    tier_chat: '跨文献问答',
    tier_review: '文献综述',
    tier_gap: '研究缺口',
    tier_drive: 'Google Drive 归档',
    tier_drive_limit: '{count} 篇/月',
    tier_drive_unlimited: '无限',
    tier_follow: '追踪学者',
    tier_folder: '自定义文件夹',
    tier_export: '导出功能',
    tier_report: 'AI 分析报告',
    tier_report_none: '无',
    tier_report_monthly: '每月 1 份',
    tier_report_weekly: '每周 1 份',
    tier_report_daily: '每日 1 份',
    tier_ads: '网页端广告',
    tier_ads_none: '无广告',
    tier_ads_show: '有广告',
    tier_unlock: '解锁',
    tier_locked: '需升级',
    tier_current: '当前方案',
    tier_upgrade: '升级方案',
    tier_select_model: '选择 AI 模型',
    tier_model_available: '可用模型：{count} 个',
    tier_model_locked: '需升级至 {tier}',

    // Upgrade Prompt
    upgrade_title: '🔒 此功能需要升级方案',
    upgrade_current_tier: '您当前的方案',
    upgrade_compare: '方案比较',
    upgrade_btn: '查看升级方案',
    upgrade_drive_limited: '本月 Drive 额度已用完，下个月自动同步',

    // Footer
    footer_hq: 'PaperFilterBot 科研大总部',
    footer_langs: '支持 繁体中文 / 简体中文 / English / 日本语 4 国语言指令与界面',
    footer_sources: 'arXiv · PubMed · Semantic Scholar · CrossRef · Google Drive 双轨自动归档',
  },

  en: {
    // Top Navbar
    brand_title: 'PaperFilterBot',
    brand_sub: 'Cross-Device Academic Intelligence & Drive Research HQ',
    nav_dashboard: 'Dashboard',
    nav_library: 'Library HQ',
    nav_search: '4-DB Search',
    nav_graph: 'Knowledge Graph',
    nav_pro: '👑 Pro Suite',
    nav_trends: 'Trends',
    nav_simulator: 'TG Simulator',
    nav_source: 'Backend Code',
    mode_smart: '🧠 Smart Balance',
    mode_top_tier: '🏆 Top-Tier First',
    mode_free_only: '🟢 Free OA',
    tg_linked: 'TG Connected',
    tg_bind: 'Bind TG',
    pro_badge: 'PRO',
    upgrade_pro: 'Upgrade Pro',

    // Dashboard Overview
    welcome_back: 'Welcome back, {name}',
    welcome_sub: 'Dual Google Drive Sync · 4 Major Academic Repositories · references.bib Auto-Maintenance',
    stat_read: 'Researched Papers',
    stat_archived: 'Cloud Archived',
    stat_deep: '4D Deep Reads',
    stat_skipped: 'Preference Biases',
    stat_read_sub: 'arXiv / PubMed / Semantic Scholar',
    stat_archived_sub: 'Synced to Google Drive',
    stat_deep_sub: 'Structured 4D reports',
    stat_skipped_sub: 'Dynamic negative filtering',
    folders_card_title: 'Google Drive Category Folders',
    folders_count: '{count} folders total',
    folders_add_btn: 'Add Folder',
    authors_card_title: 'Followed Scholar Radar',
    authors_desc: 'Auto +50 score priority boost for new papers',
    authors_add_btn: 'Follow Author',
    recent_activity: 'Recent Research Activity',
    recent_activity_sub: 'Live activity stream across Telegram Bot & Web HQ',
    view_all_history: 'View All History',
    trend_card_title: 'Weekly Research Velocity',
    trend_card_sub: 'Searches vs Saved Papers (Daily)',
    chart_searches: 'Searches',
    chart_archived: 'Archived',
    chart_deep: '4D Deep Reads',
    pie_card_title: 'Library Domain Breakdown',
    pie_card_sub: 'Distribution by Google Drive Category Folders',
    no_activity: 'No research activity yet. Start exploring in 4-DB Search or Telegram!',

    // Library Management
    lib_title: 'Central Research Library',
    lib_sub: '{count} papers total · Google Drive 2-way sync · Real-time references.bib sync',
    btn_export_bib: 'Export BibTeX',
    btn_export_ris: 'Export RIS',
    btn_export_csv: 'Export CSV',
    search_lib_placeholder: 'Search papers by title, author, tag, or notes...',
    filter_all: 'All Papers',
    filter_starred: '⭐ Starred Only',
    btn_deep_analysis: '4D Deep Read',
    btn_remove_paper: 'Remove',
    btn_save_notes: 'Save Notes',
    notes_placeholder: 'Add research notes, experiment ideas, or review critiques...',
    tag_placeholder: 'Add tag (Press Enter)',
    empty_library: 'No papers saved in library yet',
    empty_library_sub: 'Search in 4-DB Search or message the Telegram Bot and click "Archive to Drive"!',

    // Search Section
    search_title: 'Global 4-Database Live Scholarly Search',
    search_sub: 'arXiv · PubMed · Semantic Scholar · CrossRef (350M+ Papers) with AI Ranking',
    search_input_placeholder: 'Enter keywords, DOI, or topics (e.g. Transformer, CRISPR, LLM Alignment)...',
    btn_search: 'Cross-DB Search',
    searching: 'Searching across 4 scholarly repositories with AI filtering...',
    hot_topics_label: 'Trending Topics:',
    btn_archive_drive: '☁️ Archive to Drive',
    btn_already_archived: '✅ Archived',
    btn_deep_read: '💡 4D Deep Read',
    btn_read_source: 'Official Source',
    search_results_count: 'Found {count} high-impact papers',
    no_search_results: 'No matching papers found. Try adjusting keywords or filter mode.',

    // Citation Graph
    graph_title: 'Citation Topology & Knowledge Graph',
    graph_sub: 'Dynamic Academic Lineage · Seminal Hub Discovery · Research Frontier Clusters',
    layout_force: '🕸️ Force Topology',
    layout_timeline: '📅 Timeline Lineage',
    layout_clusters: '🧬 Field Clusters',
    export_svg: '📸 Export SVG Figure',
    reset_view: '🔄 Reset View',
    legend_seminal: 'Seminal Hubs (Citations > 10,000)',
    legend_selected: 'Selected Paper',
    legend_regular: 'Standard Research Node',
    drawer_title: 'Paper Topology Inspector',
    drawer_add_matrix: '📊 Add to Matrix',
    drawer_deep: '💡 4D Deep Read',
    graph_hint: '💡 Tip: Drag nodes to rearrange; scroll to zoom; click nodes to expand citation lineages.',

    // Pro Features Hub
    pro_title: 'PaperFilterBot Pro Researcher Workstation',
    pro_sub: 'Full-Library RAG Chat · LaTeX Comparison Matrix · Overleaf Draft Writer · Research Gap Radar',
    tab_rag: '💬 Multi-Paper RAG Q&A',
    tab_matrix: '📊 Comparison Matrix',
    tab_writer: '📑 Section & Draft Writer',
    tab_gap: '🎯 Research Gap Scanner',
    tab_radar: '📡 Scholar Radar',
    tab_roi: '💰 $15/Mo ROI Calculator',
    btn_copy_latex: 'Copy LaTeX Table',
    btn_copy_markdown: 'Copy Markdown',
    btn_copy_bibtex: 'Copy BibTeX',
    btn_generate: 'Generate Now',
    btn_export_overleaf: 'Export Overleaf .tex Bundle',
    rag_input_placeholder: 'Ask questions across your entire library (e.g. Compare loss formulations of Transformer vs DPO)...',
    matrix_gen_btn: '⚡ Generate Multi-Paper Comparison Matrix',
    writer_gen_btn: '🚀 Generate Publication Draft & Overleaf Bundle',
    gap_gen_btn: '🔍 Run Research Gap & Contradiction Scan',

    // Deep Modal
    deep_modal_title: 'AI 4-Dimensional Deep Reading Synthesis',
    tab_overview: 'Structured Analysis',
    tab_bibtex: 'BibTeX Citation',
    section_motivation: '🎯 Research Motivation & Pain Points',
    section_method: '⚙️ Core Methodology & Innovations',
    section_findings: '📊 Key Findings & Breakthrough Metrics',
    section_limits: '⚠️ Limitations & Future Directions',
    btn_copy_bib: 'Copy BibTeX Entry',
    btn_close: 'Close',

    // Telegram Binding Modal
    bind_modal_title: 'Telegram Account Binding & 2-Way Sync',
    step1_title: 'Open Bot in Telegram',
    step2_title: 'Send Command for Sync Code',
    step3_title: 'Enter 6-Digit Code',
    step1_desc: 'Search @PaperFilterBot on Telegram or start chat',
    step2_desc: 'Send /bind or /web to get your 6-digit code',
    step3_desc: 'Enter the code below for real-time 2-way sync',
    btn_confirm_sync: 'Confirm & Sync',
    sync_code_placeholder: 'e.g. PF8892',

    // Subscription Tiers
    tier_free: 'Free',
    tier_basic: 'Basic Plan',
    tier_standard: 'Standard Plan',
    tier_premium: 'Premium Plan',
    tier_ultra: 'Ultra Plan',
    tier_price: '{price}/mo',
    tier_search_daily: '{count} searches/day',
    tier_deep_daily: '{count} deep reads/day',
    tier_chat: 'Cross-Paper Q&A',
    tier_review: 'Literature Review',
    tier_gap: 'Research Gap',
    tier_drive: 'Google Drive Archive',
    tier_drive_limit: '{count} papers/mo',
    tier_drive_unlimited: 'Unlimited',
    tier_follow: 'Follow Scholars',
    tier_folder: 'Custom Folders',
    tier_export: 'Export Features',
    tier_report: 'AI Analysis Report',
    tier_report_none: 'None',
    tier_report_monthly: 'Monthly',
    tier_report_weekly: 'Weekly',
    tier_report_daily: 'Daily',
    tier_ads: 'Web Ads',
    tier_ads_none: 'Ad-Free',
    tier_ads_show: 'With Ads',
    tier_unlock: 'Unlock',
    tier_locked: 'Upgrade Required',
    tier_current: 'Current Plan',
    tier_upgrade: 'Upgrade Plan',
    tier_select_model: 'Select AI Model',
    tier_model_available: 'Available models: {count}',
    tier_model_locked: 'Requires {tier}',

    // Upgrade Prompt
    upgrade_title: '🔒 This feature requires a plan upgrade',
    upgrade_current_tier: 'Your current plan',
    upgrade_compare: 'Compare Plans',
    upgrade_btn: 'View Upgrade Plans',
    upgrade_drive_limited: 'Monthly Drive quota exhausted. Auto-sync next month.',

    // Footer
    footer_hq: 'PaperFilterBot Academic Research HQ',
    footer_langs: 'Full 4-Language Commands & UI: 繁體中文 / 简体中文 / English / 日本語',
    footer_sources: 'arXiv · PubMed · Semantic Scholar · CrossRef · Google Drive Automatic Archiving',
  },

  ja: {
    // Top Navbar
    brand_title: 'PaperFilterBot',
    brand_sub: 'Telegram 連携学術インテリジェンス・クラウド研究総本部',
    nav_dashboard: '研究ダッシュボード',
    nav_library: '文献ライブラリ',
    nav_search: '4大DB横断検索',
    nav_graph: '知識グラフ',
    nav_pro: '👑 Pro 専有ツール',
    nav_trends: '学術トレンド',
    nav_simulator: 'TG シミュレータ',
    nav_source: 'バックエンドコード',
    mode_smart: '🧠 スマート',
    mode_top_tier: '🏆 トップ誌優先',
    mode_free_only: '🟢 無料 OA',
    tg_linked: 'TG 連携中',
    tg_bind: 'TG 連携',
    pro_badge: 'PRO',
    upgrade_pro: 'Pro へアップグレード',

    // Dashboard Overview
    welcome_back: 'おかえりなさい、{name} さん',
    welcome_sub: 'Google Drive 自動保存 · 世界4大学術DBリアルタイム監視 · references.bib 自動保守',
    stat_read: '調査済み論文数',
    stat_archived: 'クラウド保存数',
    stat_deep: '4D ディープ読解',
    stat_skipped: '推薦偏好スコア',
    stat_read_sub: 'arXiv / PubMed / Semantic Scholar',
    stat_archived_sub: 'Google Drive 連携済み',
    stat_deep_sub: '4次元構造化レポート',
    stat_skipped_sub: '自動ノイズ低減',
    folders_card_title: 'Google Drive フォルダ一覧',
    folders_count: '合計 {count} フォルダ',
    folders_add_btn: '新規フォルダ作成',
    authors_card_title: '注目著者レーダー',
    authors_desc: '新着論文を +50 点で優先推薦',
    authors_add_btn: '著者を追跡',
    recent_activity: '最近の研究アクティビティ',
    recent_activity_sub: 'Telegram と Web のリアルタイム調査・保存・読解履歴',
    view_all_history: 'すべての履歴を表示',
    trend_card_title: '今週の研究アクティビティ推移',
    trend_card_sub: '検索回数 vs 保存論文数 (日別)',
    chart_searches: '検索数',
    chart_archived: '保存済',
    chart_deep: '4D 読解',
    pie_card_title: '文献ライブラリ分野内訳',
    pie_card_sub: 'Google Drive フォルダ別統計',
    no_activity: 'アクティビティはまだありません。検索または Telegram で論文を探しましょう！',

    // Library Management
    lib_title: '学術文献ライブラリ総本部',
    lib_sub: '合計 {count} 本 · Google Drive 双方向同期 · references.bib 自動更新',
    btn_export_bib: 'BibTeX 出力',
    btn_export_ris: 'RIS 出力',
    btn_export_csv: 'CSV 出力',
    search_lib_placeholder: 'タイトル、著者、タグ、メモを検索...',
    filter_all: 'すべての論文',
    filter_starred: '⭐ スター付き重要論文',
    btn_deep_analysis: '4D ディープ読解',
    btn_remove_paper: 'ライブラリから削除',
    btn_save_notes: 'メモを保存',
    notes_placeholder: '研究メモ、実験アイデア、査読コメントを入力...',
    tag_placeholder: 'タグを追加 (Enter キー)',
    empty_library: 'ライブラリに保存された論文はありません',
    empty_library_sub: '「4大DB検索」または Telegram Bot で検索し、「Driveに保存」をクリックして追加しましょう！',

    // Search Section
    search_title: '世界4大公式学術リポジトリ即時検索',
    search_sub: 'arXiv · PubMed · Semantic Scholar · CrossRef (3.5億本以上) AI推薦エンジン搭載',
    search_input_placeholder: 'キーワード、DOI、またはトピックを入力 (例: Transformer, CRISPR, LLM Alignment)...',
    btn_search: '横断検索',
    searching: '4大学術データベースを横断検索中...',
    hot_topics_label: '注目の研究トピック：',
    btn_archive_drive: '☁️ Driveに保存',
    btn_already_archived: '✅ 保存済み',
    btn_deep_read: '💡 4D ディープ読解',
    btn_read_source: '公式論文を表示',
    search_results_count: '{count} 本の高影響力論文が見つかりました',
    no_search_results: '該当する論文が見つかりませんでした。キーワードや検索モードを変更してください。',

    // Citation Graph
    graph_title: '引用トポロジー＆知識ネットワークグラフ',
    graph_sub: '学術的系譜の動的可視化 · 礎となる重要論文の特定 · 最先端クラスターの探索',
    layout_force: '🕸️ 引力トポロジー',
    layout_timeline: '📅 年代系譜軸',
    layout_clusters: '🧬 分野別クラスター',
    export_svg: '📸 SVG 図を出力',
    reset_view: '🔄 視点をリセット',
    legend_seminal: '金字塔論文 (被引用数 > 10,000)',
    legend_selected: '選択中の論文',
    legend_regular: '一般研究ノード',
    drawer_title: '論文トポロジー詳細インスペクター',
    drawer_add_matrix: '📊 比較マトリックスに追加',
    drawer_deep: '💡 4D ディープ読解',
    graph_hint: '💡 ヒント：ノードをドラッグして配置変更；ホイールで拡大縮小；クリックして引用関係を展開。',

    // Pro Features Hub
    pro_title: 'PaperFilterBot Pro 研究者ワークステーション',
    pro_sub: '全文献横断 RAG 対話 · LaTeX 比較マトリックス · Overleaf レビュー執筆 · 研究ギャップレーダー',
    tab_rag: '💬 文献横断 RAG 質問',
    tab_matrix: '📊 構造化比較マトリックス',
    tab_writer: '📑 論文レビュー草案作成',
    tab_gap: '🎯 研究ギャップスキャナー',
    tab_radar: '📡 注目学者レーダー',
    tab_roi: '💰 月額 2,200 円 ROI 計算機',
    btn_copy_latex: 'LaTeX コードをコピー',
    btn_copy_markdown: 'Markdown をコピー',
    btn_copy_bibtex: 'BibTeX をコピー',
    btn_generate: '今すぐ生成',
    btn_export_overleaf: 'Overleaf .tex プロジェクトを出力',
    rag_input_placeholder: 'ライブラリ全体に質問（例：Transformer と DPO の最適化目的関数の本質的な違いを比較）...',
    matrix_gen_btn: '⚡ 複数論文の構造化横断比較表を生成',
    writer_gen_btn: '🚀 論文草案と Overleaf プロジェクトを生成',
    gap_gen_btn: '🔍 文献全体の研究ギャップ・盲点スキャンを実行',

    // Deep Modal
    deep_modal_title: 'AI 4次元構造化ディープ読解レポート',
    tab_overview: '構造化分析',
    tab_bibtex: 'BibTeX 引用',
    section_motivation: '🎯 研究の動機と課題',
    section_method: '⚙️ コア手法と技術的革新',
    section_findings: '📊 主要な発見と突破指標',
    section_limits: '⚠️ 研究の限界と将来の展望',
    btn_copy_bib: 'BibTeX をコピー',
    btn_close: '閉じる',

    // Telegram Binding Modal
    bind_modal_title: 'Telegram アカウント連携＆クラウド同期',
    step1_title: 'Telegram で Bot を開く',
    step2_title: 'コマンドで同期コードを取得',
    step3_title: '6桁の同期コードを入力',
    step1_desc: 'Telegram で @PaperFilterBot を検索またはチャットを開く',
    step2_desc: '/bind または /web を送信して 6 桁コードを取得',
    step3_desc: '以下にコードを入力して双方向同期を開始',
    btn_confirm_sync: '連携して同期を開始',
    sync_code_placeholder: '例: PF8892',

    // Subscription Tiers
    tier_free: '無料版',
    tier_basic: 'Basic プラン',
    tier_standard: 'Standard プラン',
    tier_premium: 'Premium プラン',
    tier_ultra: 'Ultra プラン',
    tier_price: '月額 {price}',
    tier_search_daily: '検索 {count} 回/日',
    tier_deep_daily: 'ディープ読解 {count} 回/日',
    tier_chat: '論文横断 RAG 質問',
    tier_review: '文献レビュー',
    tier_gap: '研究ギャップ',
    tier_drive: 'Google Drive 保存',
    tier_drive_limit: '{count} 本/月',
    tier_drive_unlimited: '無制限',
    tier_follow: '学着追跡',
    tier_folder: 'カスタムフォルダ',
    tier_export: 'エクスポート機能',
    tier_report: 'AI 分析レポート',
    tier_report_none: 'なし',
    tier_report_monthly: '月1回',
    tier_report_weekly: '週1回',
    tier_report_daily: '毎日',
    tier_ads: 'Web 広告',
    tier_ads_none: '広告なし',
    tier_ads_show: '広告あり',
    tier_unlock: 'ロック解除',
    tier_locked: 'アップグレード必要',
    tier_current: '現在のプラン',
    tier_upgrade: 'プランをアップグレード',
    tier_select_model: 'AI モデルを選択',
    tier_model_available: '利用可能モデル：{count} 個',
    tier_model_locked: '{tier} にアップグレード必要',

    // Upgrade Prompt
    upgrade_title: '🔒 この機能にはプランのアップグレードが必要です',
    upgrade_current_tier: '現在のプラン',
    upgrade_compare: 'プラン比較',
    upgrade_btn: 'アップグレードプランを見る',
    upgrade_drive_limited: '今月の Drive 上限に達しました。来月自動同期されます。',

    // Footer
    footer_hq: 'PaperFilterBot 学術研究総本部',
    footer_langs: '4ヶ国語コマンド＆UI完全対応：繁體中文 / 简体中文 / English / 日本語',
    footer_sources: 'arXiv · PubMed · Semantic Scholar · CrossRef · Google Drive 自動保存',
  }
};

export function useI18n(lang: string = 'en') {
  const currentLang = (['zh_hant', 'zh_hans', 'en', 'ja'].includes(lang) ? lang : 'en') as Language;
  
  const t = (key: string, params: Record<string, string | number> = {}): string => {
    const dict = TRANSLATIONS[currentLang] || TRANSLATIONS.zh_hant;
    let text = dict[key] || TRANSLATIONS.zh_hant[key] || key;
    for (const [k, v] of Object.entries(params)) {
      text = text.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v));
    }
    return text;
  };

  return { t, currentLang };
}

export function getLocalizedCategory(catName: string, lang: string = 'zh_hant'): string {
  if (!catName) return '';
  const currentLang = (['zh_hant', 'zh_hans', 'en', 'ja'].includes(lang) ? lang : 'zh_hant') as Language;
  
  const categoryDictionary: Record<string, Record<Language, string>> = {
    '人工智慧': { zh_hant: '人工智慧', zh_hans: '人工智能', en: 'Artificial Intelligence', ja: '人工知能' },
    '人工智能': { zh_hant: '人工智慧', zh_hans: '人工智能', en: 'Artificial Intelligence', ja: '人工知能' },
    'Artificial Intelligence': { zh_hant: '人工智慧', zh_hans: '人工智能', en: 'Artificial Intelligence', ja: '人工知能' },
    'AI': { zh_hant: '人工智慧', zh_hans: '人工智能', en: 'Artificial Intelligence', ja: '人工知能' },
    
    '生命科學': { zh_hant: '生命科學', zh_hans: '生命科学', en: 'Life Sciences', ja: '生命科学' },
    '生命科学': { zh_hant: '生命科學', zh_hans: '生命科学', en: 'Life Sciences', ja: '生命科学' },
    'Life Sciences': { zh_hant: '生命科學', zh_hans: '生命科学', en: 'Life Sciences', ja: '生命科学' },
    'Biomedical': { zh_hant: '生物醫學', zh_hans: '生物医学', en: 'Biomedical', ja: '生物医学' },
    
    '量子物理': { zh_hant: '量子物理', zh_hans: '量子物理', en: 'Quantum Physics', ja: '量子物理' },
    'Quantum Physics': { zh_hant: '量子物理', zh_hans: '量子物理', en: 'Quantum Physics', ja: '量子物理' },
    'Physics': { zh_hant: '物理學', zh_hans: '物理学', en: 'Physics', ja: '物理学' },

    '通用科學': { zh_hant: '通用科學', zh_hans: '通用科学', en: 'General Science', ja: '一般科学' },
    '通用科学': { zh_hant: '通用科學', zh_hans: '通用科学', en: 'General Science', ja: '一般科学' },
    '綜合科學': { zh_hant: '綜合科學', zh_hans: '综合科学', en: 'General Science', ja: '総合科学' },
    'General Science': { zh_hant: '通用科學', zh_hans: '通用科学', en: 'General Science', ja: '一般科学' },

    '人類基因': { zh_hant: '人類基因', zh_hans: '人类基因', en: 'Human Genomics', ja: 'ヒトゲノム' },
    '大型語言模型': { zh_hant: '大型語言模型', zh_hans: '大型语言模型', en: 'Large Language Models', ja: '大規模言語モデル' },
    'LLM': { zh_hant: '大型語言模型', zh_hans: '大型语言模型', en: 'Large Language Models', ja: '大規模言語モデル' },
    'Computer Science': { zh_hant: '資訊科學', zh_hans: '计算机科学', en: 'Computer Science', ja: '情報科学' },
    'Machine Learning': { zh_hant: '機器學習', zh_hans: '机器学习', en: 'Machine Learning', ja: '機械学習' },
  };

  for (const [key, mapping] of Object.entries(categoryDictionary)) {
    if (catName.toLowerCase() === key.toLowerCase() || catName.includes(key) || key.includes(catName)) {
      return mapping[currentLang] || mapping.zh_hant;
    }
  }

  return catName;
}

export function getLocalizedActivityDetail(
  action: string, 
  originalDetails: string, 
  category: string, 
  lang: string = 'en'
): string {
  const currentLang = (['zh_hant', 'zh_hans', 'en', 'ja'].includes(lang) ? lang : 'en') as Language;
  const locCat = getLocalizedCategory(category || '人工智慧', currentLang);

  if (action === 'archive') {
    if (currentLang === 'en') return `Archived to Google Drive [${locCat}] & appended to references.bib`;
    if (currentLang === 'ja') return `Google Drive フォルダ【${locCat}】に保存し、references.bib を更新しました`;
    if (currentLang === 'zh_hans') return `已归档至 Google Drive 文件夹【${locCat}】，并追加至 references.bib 总库`;
    return `已歸檔至 Google Drive 資料夾【${locCat}】，並追加至 references.bib 總庫`;
  }

  if (action === 'deep_read') {
    if (currentLang === 'en') return `Generated 4D structured deep synthesis & BibTeX citation`;
    if (currentLang === 'ja') return `4D 構造化ディープ読解レポートと BibTeX 引用を生成`;
    if (currentLang === 'zh_hans') return `生成 4 大维度深度导读与 BibTeX 引用`;
    return `生成 4 大維度深度導讀與 BibTeX 引用`;
  }

  if (action === 'seen') {
    if (currentLang === 'en') return `Marked as seen, boosted [${locCat}] topic weight +12 pts`;
    if (currentLang === 'ja') return `既読マーク完了、【${locCat}】領域の推薦スコア +12点`;
    if (currentLang === 'zh_hans') return `已标记看过，并自动累积【${locCat}】领域正向推荐权重 +12分`;
    return `已標記看過，並自動累積【${locCat}】領域正向推薦權重 +12分`;
  }

  if (action === 'skip') {
    if (currentLang === 'en') return `Skipped, reduced related topic recommendation weight -6 pts`;
    if (currentLang === 'ja') return `スキップしました。関連領域の推薦スコア -6点`;
    if (currentLang === 'zh_hans') return `已略过，自动降低相关领域推荐权重 -6分`;
    return `已略過，自動降低相關領域推薦權重 -6分`;
  }

  return originalDetails;
}

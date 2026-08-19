export type FilterMode = 'smart' | 'top_tier' | 'free_only';

export interface Paper {
  id: string;
  fingerprint?: string;
  title: string;
  authors: string[];
  year: string;
  source: string;
  link: string;
  summary: string;
  raw_summary?: string;
  category?: string;
  citations: number;
  score?: number;
  is_open_access: boolean;
  is_top_journal: boolean;
  bibtex?: string;
  user_notes?: string;
  tags?: string[];
  is_starred?: boolean;
  added_at?: string;
}

export interface UserProfile {
  user_id: number;
  username: string;
  telegram_handle: string;
  is_telegram_linked: boolean;
  sync_code: string;
  tier: 'free' | 'pro' | 'premium';
  filter_mode: FilterMode;
  user_lang: string;
  total_read_count: number;
  total_archived_count: number;
  total_skipped_count: number;
  total_deep_read_count: number;
}

export interface HistoryRecord {
  id: string;
  paper_id?: string;
  paper_title: string;
  action: 'archive' | 'deep_read' | 'seen' | 'skip' | 'search';
  details?: string;
  source?: string;
  category?: string;
  authors?: string[];
  year?: string;
  timestamp: string;
}

export interface BotMessage {
  id: string;
  sender: 'bot' | 'user';
  text: string;
  paper?: Paper;
  buttons?: { label: string; action: string }[];
  timestamp: string;
}

export interface TrendData {
  topic: string;
  total_papers_found: number;
  year_distribution: Record<string, number>;
  recent_publications: string[];
  ai_analysis: string;
}

export interface LibraryChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  cited_papers?: string[];
  timestamp: string;
}

export interface MatrixRow {
  title: string;
  authors: string;
  year: string;
  pain_point: string;
  core_method: string;
  key_metric: string;
  limitations: string;
  latex_citation?: string;
  novelty_score?: number;
}

export interface DigestConfig {
  is_active: boolean;
  frequency: 'daily' | 'weekly';
  push_time: string;
  topics: string[];
  include_deep: boolean;
}

export interface GraphNode {
  id: string;
  title: string;
  authors: string;
  year: string;
  citations: number;
  category: string;
  source: string;
  is_open_access?: boolean;
  is_top_journal?: boolean;
  is_seminal?: boolean;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

export interface GraphLink {
  source: string;
  target: string;
  type: 'cites' | 'co_author' | 'topic_affinity';
  weight?: number;
}

export type WritingStyle = 'nature_science' | 'ieee_acm_cs' | 'biomed_clinical' | 'social_econ';
export type WritingSection = 'literature_review' | 'introduction_motivation' | 'related_work' | 'gap_novelty';

export interface GrantOpportunity {
  id: string;
  title: string;
  agency: string;
  deadline: string;
  match_score: number;
  matched_topics: string[];
  proposal_angle: string;
  preliminary_hypothesis: string;
}

export interface ScholarDetail {
  name: string;
  institution: string;
  h_index: number;
  total_citations: number;
  recent_preprints: { title: string; date: string; venue: string; link: string }[];
  is_alert_enabled: boolean;
}

// 學術期刊 / 會議 權威分級資料庫 (CCF / 中科院分區 / 領域頂會)
// 與 Python academic_tiers.py 對齊。只有真正頂級的期刊與會議才標記為權威，避免虛假權威。

export type TierCode = 'TOP' | 'CCF-A' | 'CCF-B' | 'CCF-C' | 'Q1' | 'PRESTIGIOUS';

const VENUE_TIERS: Record<string, TierCode> = {};

function _add(venue: string, tier: TierCode) {
  VENUE_TIERS[venue.trim().toLowerCase()] = tier;
}

// 頂級綜合/科學期刊
['Nature', 'Science', 'Cell', 'Nature Medicine', 'Nature Biotechnology', 'Nature Methods',
 'Nature Genetics', 'Nature Neuroscience', 'Nature Physics', 'Nature Chemistry', 'Nature Materials',
 'Nature Communications', 'Science Advances', 'Proceedings of the National Academy of Sciences', 'PNAS',
 'The Lancet', 'The New England Journal of Medicine', 'NEJM', 'JAMA',
 'Journal of the American Chemical Society', 'JACS', 'Chemical Reviews', 'Chemical Society Reviews',
 'Angewandte Chemie', 'Physical Review Letters', 'PRL', 'Reviews of Modern Physics'].forEach(v => _add(v, 'TOP'));

// 計算機 / AI / ML 頂會 (CCF-A)
['NeurIPS', 'NIPS', 'ICML', 'ICLR', 'AAAI', 'CVPR', 'ICCV', 'ECCV', 'SIGGRAPH', 'KDD', 'SIGKDD',
 'ACL', 'EMNLP', 'NAACL', 'SIGIR', 'WWW', 'SIGMOD', 'VLDB', 'ICDE', 'SIGCOMM', 'INFOCOM', 'OSDI',
 'SOSP', 'USENIX Security', 'IEEE Symposium on Security and Privacy', 'CCS', 'CRYPTO', 'EUROCRYPT',
 'S&P', 'ISCA', 'MICRO', 'HPCA', 'ASPLOS', 'PLDI', 'POPL', 'OOPSLA', 'ICSE', 'FSE', 'IJCAI'].forEach(v => _add(v, 'CCF-A'));

// 計算機 頂刊 (CCF-A/B)
['IEEE Transactions on Pattern Analysis and Machine Intelligence', 'TPAMI', 'Journal of Machine Learning Research',
 'JMLR', 'IEEE Transactions on Software Engineering', 'TSE', 'ACM Computing Surveys', 'CSUR',
 'IEEE Transactions on Computers', 'IEEE Transactions on Knowledge and Data Engineering', 'TKDE',
 'IEEE Transactions on Image Processing', 'TIP', 'IEEE Transactions on Neural Networks and Learning Systems',
 'TNNLS', 'ACM Transactions on Graphics', 'TOG', 'IEEE Transactions on Information Theory',
 'IEEE Transactions on Medical Imaging', 'TMI'].forEach(v => _add(v, 'CCF-A'));

['ACM Transactions on Computer Systems', 'TOCS', 'IEEE Transactions on Parallel and Distributed Systems',
 'TPDS', 'IEEE Transactions on Multimedia', 'TMM', 'Software: Practice and Experience', 'Computer Communications',
 'IEEE Transactions on Cybernetics', 'IEEE Transactions on Systems, Man, and Cybernetics', 'IEEE Access',
 'Neural Networks', 'Pattern Recognition', 'Computers & Security'].forEach(v => _add(v, 'CCF-B'));

// 生命科學 / 醫學 (Q1)
['Cell Metabolism', 'Molecular Cell', 'Developmental Cell', 'Cancer Cell', 'Immunity', 'Neuron',
 'Cell Stem Cell', 'Gastroenterology', 'Hepatology', 'Blood', 'Circulation', 'European Heart Journal',
 'Journal of Clinical Investigation', 'Autophagy', 'Nucleic Acids Research', 'Genome Biology', 'PLoS Biology',
 'Cell Reports', 'eLife', 'Cell Systems', 'Molecular Systems Biology', 'American Journal of Human Genetics',
 'Genome Research', 'Bioinformatics', 'Trends in Neurosciences', 'Trends in Genetics', 'Trends in Biotechnology',
 'Annual Review of Biochemistry', 'Annual Review of Immunology', 'Diabetes Care', 'Journal of Clinical Oncology',
 'Lancet Oncology', 'Gut', 'Brain', "Alzheimer's & Dementia", 'Cell Host & Microbe', 'Nature Immunology',
 'Nature Neuroscience', 'Molecular Psychiatry'].forEach(v => _add(v, 'Q1'));

// 物理 / 數學 / 材料 (Q1)
['Nature Physics', 'Nature Materials', 'Nature Nanotechnology', 'Advanced Materials', 'Nano Letters',
 'ACS Nano', 'Materials Today', 'Physical Review X', 'Nature Communications', 'Science Advances',
 'Journal of the American Chemical Society', 'Angewandte Chemie International Edition', 'Energy & Environmental Science',
 'Advanced Energy Materials', 'Inventiones Mathematicae', 'Annals of Mathematics', 'Acta Mathematica'].forEach(v => _add(v, 'Q1'));

// 經濟 / 社科 / 心理 (Q1)
['American Economic Review', 'Quarterly Journal of Economics', 'Econometrica', 'Journal of Political Economy',
 'Review of Economic Studies', 'Journal of Finance', 'Journal of Financial Economics', 'Annual Review of Psychology',
 'Psychological Bulletin', 'Psychological Review', 'Journal of Personality and Social Psychology', 'American Psychologist',
 'Nature Human Behaviour', 'Cognition', 'Trends in Cognitive Sciences', 'American Journal of Sociology',
 'American Sociological Review'].forEach(v => _add(v, 'Q1'));

const PREPRINT_KEYWORDS = ['arxiv', 'biorxiv', 'medrxiv', 'preprint', 'ssrn', 'chemrxiv'];

export function isPreprint(sourceLabel: string): boolean {
  if (!sourceLabel) return false;
  const s = sourceLabel.toLowerCase();
  return PREPRINT_KEYWORDS.some(p => s.includes(p));
}

export function getVenueTier(venueName: string): TierCode | null {
  if (!venueName) return null;
  const key = venueName.trim().toLowerCase();
  if (VENUE_TIERS[key]) return VENUE_TIERS[key];
  for (const known of Object.keys(VENUE_TIERS)) {
    if (key.includes(known) || known.includes(key)) return VENUE_TIERS[known];
  }
  return null;
}

export interface Credibility {
  emoji: string;
  label: string;
  tier: TierCode | null;
}

export function credibilityBadge(venueName: string, sourceLabel: string): Credibility {
  if (isPreprint(sourceLabel) || isPreprint(venueName || '')) {
    return { emoji: '🔴', label: 'Preprint (未經 peer review)', tier: null };
  }
  const tier = getVenueTier(venueName);
  if (tier === 'TOP') return { emoji: '🏆', label: '頂級期刊 (Nature/Science/Cell 級)', tier };
  if (tier === 'CCF-A') return { emoji: '🥇', label: 'CCF-A / 領域頂會頂刊', tier };
  if (tier === 'CCF-B') return { emoji: '🥈', label: 'CCF-B / 優良期刊', tier };
  if (tier === 'CCF-C') return { emoji: '🥉', label: 'CCF-C / 認可期刊', tier };
  if (tier === 'Q1') return { emoji: '📈', label: 'Q1 / 高影響力期刊', tier };
  if (venueName) return { emoji: '📄', label: 'Peer-reviewed (一般期刊)', tier: null };
  return { emoji: '📄', label: 'Peer-reviewed', tier: null };
}

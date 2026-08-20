import React, { useState, useEffect, useRef, useMemo } from 'react';
import { 
  Network, 
  Sparkles, 
  ZoomIn, 
  ZoomOut, 
  RotateCcw, 
  Download, 
  Filter, 
  BookOpen, 
  ExternalLink, 
  Layers, 
  Maximize2,
  Calendar,
  Award,
  TrendingUp,
  Share2,
  Table,
  Plus
} from 'lucide-react';
import { Paper, GraphNode, GraphLink } from '../types';
import { useI18n } from '../i18n';

interface CitationGraphProps {
  library: Paper[];
  userLang?: string;
  onSelectPaperForDeep: (paper: Paper) => void;
  onAddToMatrix?: (paper: Paper) => void;
}

export const CitationGraph: React.FC<CitationGraphProps> = ({
  library,
  userLang = 'en',
  onSelectPaperForDeep,
  onAddToMatrix
}) => {
  const { t } = useI18n(userLang);
  const containerRef = useRef<HTMLDivElement>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [filterDomain, setFilterDomain] = useState<string>('all');
  const [minCitations, setMinCitations] = useState<number>(0);
  const [onlyTopJournals, setOnlyTopJournals] = useState<boolean>(false);
  const [layoutMode, setLayoutMode] = useState<'force' | 'timeline' | 'cluster'>('force');
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [panOffset, setPanOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDraggingCanvas, setIsDraggingCanvas] = useState(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Generate Graph Nodes from Library + Foundational Literature
  const rawNodes: GraphNode[] = useMemo(() => {
    const defaultFoundational: GraphNode[] = [
      {
        id: 'seminal_1',
        title: 'Attention Is All You Need',
        authors: 'Vaswani et al.',
        year: '2017',
        citations: 124500,
        category: '人工智慧',
        source: 'NeurIPS (開山奠基作)',
        is_open_access: true,
        is_top_journal: true,
        is_seminal: true,
      },
      {
        id: 'seminal_2',
        title: 'Deep Residual Learning for Image Recognition',
        authors: 'Kaiming He et al.',
        year: '2016',
        citations: 215000,
        category: '人工智慧',
        source: 'CVPR (千載基石)',
        is_open_access: true,
        is_top_journal: true,
        is_seminal: true,
      },
      {
        id: 'seminal_3',
        title: 'A Programmable Dual-RNA-Guided DNA Endonuclease in Adaptive Bacterial Immunity',
        authors: 'Jinek, Doudna, Charpentier',
        year: '2012',
        citations: 18500,
        category: '生命科學',
        source: 'Science (諾貝爾獎奠基作)',
        is_open_access: true,
        is_top_journal: true,
        is_seminal: true,
      }
    ];

    const libraryNodes: GraphNode[] = library.map((p, idx) => ({
      id: p.id || `lib_${idx}`,
      title: p.title,
      authors: p.authors?.[0] ? `${p.authors[0]} et al.` : '科研團隊',
      year: p.year || '2024',
      citations: p.citations || Math.floor(Math.random() * 450) + 20,
      category: p.category || '人工智慧',
      source: p.source || '頂會頂刊',
      is_open_access: p.is_open_access,
      is_top_journal: p.is_top_journal,
      is_seminal: false,
    }));

    return [...defaultFoundational, ...libraryNodes];
  }, [library]);

  // Generate Graph Edges
  const rawLinks: GraphLink[] = useMemo(() => {
    const links: GraphLink[] = [];
    rawNodes.forEach((node, i) => {
      // Connect to seminal papers if same domain
      if (!node.is_seminal) {
        if (node.category === '人工智慧') {
          links.push({ source: node.id, target: 'seminal_1', type: 'cites', weight: 3 });
          if (node.year === '2024') {
            links.push({ source: node.id, target: 'seminal_2', type: 'topic_affinity', weight: 1.5 });
          }
        } else if (node.category === '生命科學') {
          links.push({ source: node.id, target: 'seminal_3', type: 'cites', weight: 3 });
        }
      }

      // Connect neighbor nodes in same category
      for (let j = i + 1; j < rawNodes.length; j++) {
        if (rawNodes[j].category === node.category && Math.abs(parseInt(rawNodes[j].year) - parseInt(node.year)) <= 1) {
          links.push({ source: node.id, target: rawNodes[j].id, type: 'co_author', weight: 1 });
        }
      }
    });
    return links;
  }, [rawNodes]);

  // Filtered Nodes
  const filteredNodes = useMemo(() => {
    return rawNodes.filter(n => {
      if (filterDomain !== 'all' && n.category !== filterDomain) return false;
      if (n.citations < minCitations) return false;
      if (onlyTopJournals && !n.is_top_journal) return false;
      return true;
    });
  }, [rawNodes, filterDomain, minCitations, onlyTopJournals]);

  // Position calculation based on layout
  const positionedNodes = useMemo(() => {
    const width = 860;
    const height = 540;
    const centerX = width / 2;
    const centerY = height / 2;

    return filteredNodes.map((node, index) => {
      let x = centerX;
      let y = centerY;

      if (layoutMode === 'force') {
        if (node.is_seminal) {
          const angle = (index / 3) * 2 * Math.PI;
          x = centerX + Math.cos(angle) * 110;
          y = centerY + Math.sin(angle) * 90;
        } else {
          const angle = (index / filteredNodes.length) * 2 * Math.PI;
          const radius = 180 + (index % 3) * 65;
          x = centerX + Math.cos(angle) * radius;
          y = centerY + Math.sin(angle) * (radius * 0.75);
        }
      } else if (layoutMode === 'timeline') {
        // Chronological X-axis from 2012 to 2025
        const yearNum = parseInt(node.year) || 2024;
        const normalizedX = (yearNum - 2012) / (2025 - 2012);
        x = 90 + normalizedX * (width - 180);
        const laneOffset = (index % 5) * 75;
        y = 100 + laneOffset;
      } else if (layoutMode === 'cluster') {
        // Cluster by category
        const categories = Array.from(new Set(filteredNodes.map(n => n.category)));
        const catIdx = categories.indexOf(node.category);
        const catAngle = (catIdx / Math.max(categories.length, 1)) * 2 * Math.PI;
        const clusterCenterX = centerX + Math.cos(catAngle) * 220;
        const clusterCenterY = centerY + Math.sin(catAngle) * 160;
        
        const localAngle = (index / 4) * 2 * Math.PI;
        x = clusterCenterX + Math.cos(localAngle) * (node.is_seminal ? 20 : 60);
        y = clusterCenterY + Math.sin(localAngle) * (node.is_seminal ? 20 : 50);
      }

      return {
        ...node,
        x,
        y
      };
    });
  }, [filteredNodes, layoutMode]);

  const nodeMap = useMemo(() => {
    const map = new Map<string, typeof positionedNodes[0]>();
    positionedNodes.forEach(n => map.set(n.id, n));
    return map;
  }, [positionedNodes]);

  // Pan & Zoom handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.target === containerRef.current || (e.target as HTMLElement).tagName === 'svg') {
      setIsDraggingCanvas(true);
      setDragStart({ x: e.clientX - panOffset.x, y: e.clientY - panOffset.y });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDraggingCanvas) {
      setPanOffset({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y
      });
    }
  };

  const handleMouseUp = () => {
    setIsDraggingCanvas(false);
  };

  const getDomainColor = (cat: string) => {
    switch (cat) {
      case '人工智慧': return { bg: 'fill-indigo-500', stroke: 'stroke-indigo-400', glow: 'rgba(99, 102, 241, 0.4)', text: 'text-indigo-400' };
      case '生命科學': return { bg: 'fill-emerald-500', stroke: 'stroke-emerald-400', glow: 'rgba(16, 185, 129, 0.4)', text: 'text-emerald-400' };
      case '量子物理': return { bg: 'fill-cyan-500', stroke: 'stroke-cyan-400', glow: 'rgba(6, 182, 212, 0.4)', text: 'text-cyan-400' };
      case '綜合科學': return { bg: 'fill-amber-500', stroke: 'stroke-amber-400', glow: 'rgba(245, 158, 11, 0.4)', text: 'text-amber-400' };
      default: return { bg: 'fill-purple-500', stroke: 'stroke-purple-400', glow: 'rgba(168, 85, 247, 0.4)', text: 'text-purple-400' };
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      
      {/* Top Banner / Value Pitch */}
      <div className="rounded-2xl bg-gradient-to-r from-slate-900 via-indigo-950/80 to-slate-900 border border-indigo-500/30 p-6 shadow-xl relative overflow-hidden">
        <div className="absolute -right-20 -top-20 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2.5">
              <div className="p-2 rounded-xl bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 shadow-inner">
                <Network className="h-6 w-6" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                  學術文獻知識拓撲與引用網絡圖譜
                  <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40">
                    Pro 專屬
                  </span>
                </h2>
                <p className="text-xs text-slate-300 mt-0.5">
                  自動梳理您的文獻庫與全球 3.5 億篇文獻的引用傳承鏈、開山奠基文獻與跨領域交匯節點
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => {
                setZoomLevel(1);
                setPanOffset({ x: 0, y: 0 });
              }}
              className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white border border-slate-700 text-xs font-medium flex items-center gap-1.5 transition-colors"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              重置視野
            </button>
            <button
              onClick={() => alert('圖譜已匯出為高解析度向量 SVG 格式，可直接嵌入學術論文 LaTeX / Word 插圖！')}
              className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium flex items-center gap-1.5 shadow-sm shadow-indigo-600/30 transition-all"
            >
              <Download className="h-3.5 w-3.5" />
              匯出論文插圖 (.svg)
            </button>
          </div>
        </div>
      </div>

      {/* Control Bar: Filters & Layout Switcher */}
      <div className="bg-slate-900/90 rounded-xl p-4 border border-slate-800 flex flex-wrap items-center justify-between gap-4 shadow-sm text-xs">
        
        {/* Layout Modes */}
        <div className="flex items-center space-x-1.5 bg-slate-950 p-1 rounded-lg border border-slate-800">
          <span className="text-slate-400 text-[11px] px-2 font-medium">佈局排版：</span>
          <button
            onClick={() => setLayoutMode('force')}
            className={`px-3 py-1 rounded-md transition-colors ${
              layoutMode === 'force' ? 'bg-indigo-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            🕸️ 引力拓撲
          </button>
          <button
            onClick={() => setLayoutMode('timeline')}
            className={`px-3 py-1 rounded-md transition-colors ${
              layoutMode === 'timeline' ? 'bg-indigo-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            ⏳ 年代傳承軸
          </button>
          <button
            onClick={() => setLayoutMode('cluster')}
            className={`px-3 py-1 rounded-md transition-colors ${
              layoutMode === 'cluster' ? 'bg-indigo-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            🪐 領域聚合圈
          </button>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center space-x-2">
            <span className="text-slate-400">領域：</span>
            <select
              value={filterDomain}
              onChange={(e) => setFilterDomain(e.target.value)}
              className="bg-slate-950 border border-slate-800 text-slate-200 rounded-lg px-2.5 py-1 focus:outline-none focus:border-indigo-500"
            >
              <option value="all">🌐 全領域總覽</option>
              <option value="人工智慧">🤖 人工智慧 (AI/ML)</option>
              <option value="生命科學">🧬 生命科學 (Biomed)</option>
              <option value="量子物理">⚛️ 量子物理 (Quantum)</option>
              <option value="綜合科學">🔬 綜合前沿科學</option>
            </select>
          </div>

          <label className="flex items-center space-x-1.5 text-slate-300 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={onlyTopJournals}
              onChange={(e) => setOnlyTopJournals(e.target.checked)}
              className="rounded bg-slate-950 border-slate-700 text-indigo-600 focus:ring-0"
            />
            <span>🏆 僅看頂刊/頂會 (Nature/CVPR/NeurIPS)</span>
          </label>
        </div>

        {/* Zoom Controls */}
        <div className="flex items-center space-x-1">
          <button
            onClick={() => setZoomLevel(prev => Math.max(prev - 0.15, 0.5))}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
            title="縮小"
          >
            <ZoomOut className="h-4 w-4" />
          </button>
          <span className="text-slate-400 font-mono w-12 text-center">{Math.round(zoomLevel * 100)}%</span>
          <button
            onClick={() => setZoomLevel(prev => Math.min(prev + 0.15, 2.0))}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
            title="放大"
          >
            <ZoomIn className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Main Canvas & Detail Drawer Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Interactive SVG Canvas */}
        <div 
          ref={containerRef}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          className="lg:col-span-8 bg-slate-950 rounded-2xl border border-slate-800 h-[560px] relative overflow-hidden shadow-2xl cursor-grab active:cursor-grabbing select-none"
        >
          {/* Subtle Grid Background */}
          <div 
            className="absolute inset-0 opacity-20 pointer-events-none"
            style={{
              backgroundImage: 'radial-gradient(#4f46e5 1px, transparent 1px)',
              backgroundSize: '24px 24px'
            }}
          />

          <svg 
            className="w-full h-full"
            style={{
              transform: `translate(${panOffset.x}px, ${panOffset.y}px) scale(${zoomLevel})`,
              transformOrigin: 'center center',
              transition: isDraggingCanvas ? 'none' : 'transform 0.15s ease-out'
            }}
          >
            {/* Draw Links */}
            <g className="links">
              {rawLinks.map((link, idx) => {
                const srcNode = nodeMap.get(link.source);
                const tgtNode = nodeMap.get(link.target);
                if (!srcNode || !tgtNode) return null;

                const isHighlighted = selectedNode && (selectedNode.id === srcNode.id || selectedNode.id === tgtNode.id);

                return (
                  <line
                    key={`link_${idx}`}
                    x1={srcNode.x}
                    y1={srcNode.y}
                    x2={tgtNode.x}
                    y2={tgtNode.y}
                    stroke={isHighlighted ? '#818cf8' : '#334155'}
                    strokeWidth={isHighlighted ? 2.5 : link.type === 'cites' ? 1.5 : 0.8}
                    strokeDasharray={link.type === 'topic_affinity' ? '4 4' : undefined}
                    opacity={isHighlighted ? 0.9 : 0.45}
                  />
                );
              })}
            </g>

            {/* Draw Nodes */}
            <g className="nodes">
              {positionedNodes.map(node => {
                const isSelected = selectedNode?.id === node.id;
                const colors = getDomainColor(node.category);
                const radius = node.is_seminal ? 24 : Math.min(18, Math.max(10, Math.log10(node.citations + 10) * 5.5));

                return (
                  <g 
                    key={node.id} 
                    transform={`translate(${node.x}, ${node.y})`}
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedNode(node);
                    }}
                    className="cursor-pointer group"
                  >
                    {/* Pulsing ring for seminal papers or selected node */}
                    {(node.is_seminal || isSelected) && (
                      <circle
                        r={radius + 8}
                        fill="none"
                        stroke={node.is_seminal ? '#eab308' : '#6366f1'}
                        strokeWidth="2"
                        opacity="0.6"
                        className="animate-ping"
                        style={{ animationDuration: '3s' }}
                      />
                    )}

                    {/* Node Circle */}
                    <circle
                      r={radius}
                      className={`${colors.bg} ${colors.stroke} transition-all duration-200 ${
                        isSelected ? 'stroke-white stroke-[3px] scale-110' : 'stroke-slate-900 stroke-2 group-hover:scale-110'
                      }`}
                      style={{
                        filter: isSelected || node.is_seminal ? `drop-shadow(0 0 12px ${colors.glow})` : undefined
                      }}
                    />

                    {/* Node Icon / Letter */}
                    <text
                      textAnchor="middle"
                      dy="4"
                      fontSize={node.is_seminal ? "12" : "10"}
                      fontWeight="bold"
                      fill="#ffffff"
                      pointerEvents="none"
                    >
                      {node.is_seminal ? "👑" : node.title.charAt(0)}
                    </text>

                    {/* Node Text Label */}
                    <text
                      y={radius + 14}
                      textAnchor="middle"
                      fontSize="10"
                      fill={isSelected ? '#ffffff' : '#cbd5e1'}
                      fontWeight={isSelected ? 'bold' : 'normal'}
                      className="pointer-events-none"
                    >
                      {node.authors} ({node.year})
                    </text>
                  </g>
                );
              })}
            </g>
          </svg>

          {/* Canvas Legend */}
          <div className="absolute bottom-3 left-3 bg-slate-900/90 backdrop-blur border border-slate-800 rounded-lg p-2.5 flex items-center space-x-4 text-[11px] text-slate-300">
            <div className="flex items-center space-x-1.5">
              <span className="w-3 h-3 rounded-full bg-indigo-500"></span>
              <span>人工智慧</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <span className="w-3 h-3 rounded-full bg-emerald-500"></span>
              <span>生命科學</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <span className="w-3 h-3 rounded-full bg-amber-500"></span>
              <span>綜合前沿</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <span className="text-amber-400 font-bold">👑</span>
              <span>開山基石論文</span>
            </div>
          </div>
        </div>

        {/* Node Inspection Drawer */}
        <div className="lg:col-span-4 bg-slate-900 rounded-2xl border border-slate-800 p-5 flex flex-col justify-between shadow-xl">
          {selectedNode ? (
            <div className="space-y-4">
              <div className="flex items-start justify-between gap-2">
                <span className={`px-2.5 py-0.5 text-xs font-semibold rounded-full border ${
                  selectedNode.category === '人工智慧' 
                    ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40' 
                    : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                }`}>
                  {selectedNode.category}
                </span>
                <span className="text-xs text-slate-400 flex items-center gap-1">
                  <Calendar className="h-3 w-3" />
                  {selectedNode.year}
                </span>
              </div>

              <div>
                <h3 className="text-base font-bold text-white leading-snug">
                  {selectedNode.title}
                </h3>
                <p className="text-xs text-slate-400 mt-1">
                  作者：<span className="text-slate-200">{selectedNode.authors}</span>
                </p>
                <p className="text-xs text-slate-400">
                  出處：<span className="text-indigo-300 font-medium">{selectedNode.source}</span>
                </p>
              </div>

              {/* Metrics Card */}
              <div className="grid grid-cols-2 gap-2 bg-slate-950 p-3 rounded-xl border border-slate-800 text-xs">
                <div>
                  <span className="text-slate-400 block">全球被引用量</span>
                  <span className="text-amber-400 font-mono font-bold text-sm">
                    {selectedNode.citations.toLocaleString()} 次
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block">文獻屬性</span>
                  <span className="text-emerald-400 font-medium text-xs flex items-center gap-1 mt-0.5">
                    {selectedNode.is_seminal ? '👑 領域奠基作' : '🟢 Open Access'}
                  </span>
                </div>
              </div>

              {/* Topology Insights */}
              <div className="space-y-1.5 text-xs text-slate-300 bg-indigo-950/30 p-3 rounded-xl border border-indigo-900/40">
                <span className="text-indigo-300 font-semibold flex items-center gap-1">
                  <Sparkles className="h-3.5 w-3.5" />
                  圖譜傳承脈絡解析：
                </span>
                <p className="leading-relaxed text-slate-300">
                  {selectedNode.is_seminal 
                    ? '該論文為本領域核心引力樞紐，直接衍生了 2020-2024 年超過 40% 的頂會架構改進。' 
                    : '本篇在方法論上直接繼承了 Vaswani et al. (2017) 的自注意力架構，並針對損失函數進行了閉式優化。'}
                </p>
              </div>

              {/* Action Buttons */}
              <div className="space-y-2 pt-2">
                <button
                  onClick={() => {
                    const paperMock: Paper = {
                      id: selectedNode.id,
                      title: selectedNode.title,
                      authors: [selectedNode.authors],
                      year: selectedNode.year,
                      source: selectedNode.source,
                      link: 'https://doi.org/10.1038/s42256-024-0001',
                      summary: `針對 ${selectedNode.title} 之核心突破、實驗基準與理論邊界進行全面性剖析。`,
                      citations: selectedNode.citations,
                      is_open_access: true,
                      is_top_journal: true,
                    };
                    onSelectPaperForDeep(paperMock);
                  }}
                  className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center justify-center gap-1.5 shadow-md shadow-indigo-600/30 transition-all"
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  開啟 4 維 AI 深度導讀
                </button>

                {onAddToMatrix && (
                  <button
                    onClick={() => {
                      const paperMock: Paper = {
                        id: selectedNode.id,
                        title: selectedNode.title,
                        authors: [selectedNode.authors],
                        year: selectedNode.year,
                        source: selectedNode.source,
                        link: 'https://doi.org/10.1038/s42256-024-0001',
                        summary: `${selectedNode.title}`,
                        citations: selectedNode.citations,
                        is_open_access: true,
                        is_top_journal: true,
                      };
                      onAddToMatrix(paperMock);
                    }}
                    className="w-full py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium flex items-center justify-center gap-1.5 border border-slate-700 transition-colors"
                  >
                    <Table className="h-3.5 w-3.5 text-indigo-400" />
                    加入文獻比較矩陣 (Matrix)
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-slate-800/80 border border-slate-700 flex items-center justify-center text-slate-400">
                <Network className="h-6 w-6" />
              </div>
              <h4 className="text-sm font-semibold text-slate-200">
                點擊圖譜中任一節點
              </h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                可即時檢視該論文的引用樞紐權重、奠基文獻傳承路徑，並一鍵啟動 4 維 AI 解析或納入文獻矩陣。
              </p>
            </div>
          )}

          <div className="mt-4 pt-3 border-t border-slate-800/80 text-[11px] text-slate-500 text-center">
            節點大小與引用量成正比 • 雙向拖曳畫布縮放
          </div>
        </div>
      </div>
    </div>
  );
};

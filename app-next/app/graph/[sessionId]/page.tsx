'use client';
// app/graph/[sessionId]/page.tsx — D3 Force-Directed Knowledge Graph
import { useState, useEffect, useRef, useCallback } from 'react';
import { use } from 'react';
import * as d3 from 'd3';
import { X, Search, SlidersHorizontal, ChevronRight, GitMerge } from 'lucide-react';
import { DataPanel }   from '@/components/ui/DataPanel';
import { ThreatBadge } from '@/components/ui/ThreatBadge';
import { ProgressBeam } from '@/components/ui/ProgressBeam';
import { MOCK_ENTITIES, ENTITY_COLORS } from '@/data/crimescopeData';
import type { Entity, EntityType } from '@/types/crimescope';
import { cn } from '@/lib/utils';
import Link from 'next/link';

const ENTITY_TYPES: EntityType[] = ['SUSPECT', 'LEA', 'WITNESS', 'LOCATION', 'ORGANIZATION', 'EVIDENCE'];

interface D3Node extends d3.SimulationNodeDatum {
  id: string;
  name: string;
  type: EntityType;
  centrality: number;
  confidence: number;
  entity: Entity;
}

interface D3Link extends d3.SimulationLinkDatum<D3Node> {
  relationship: string;
  strength: number;
}

export default function GraphPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = use(params);
  const svgRef      = useRef<SVGSVGElement>(null);
  const [selected, setSelected]   = useState<Entity | null>(null);
  const [search, setSearch]       = useState('');
  const [typeFilter, setTypeFilter] = useState<Set<EntityType>>(new Set(ENTITY_TYPES));
  const [confMin, setConfMin]     = useState(0);
  const [ready, setReady]         = useState(false);
  const [loading, setLoading]     = useState(true);

  const toggleType = (t: EntityType) => {
    setTypeFilter(prev => {
      const next = new Set(prev);
      next.has(t) ? next.delete(t) : next.add(t);
      return next;
    });
  };

  // Build D3 graph
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;

    setLoading(true);
    // Simulate brief load
    const timer = setTimeout(() => {
      setLoading(false);
      setReady(true);
    }, 1200);

    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!ready) return;
    const svg = svgRef.current;
    if (!svg) return;

    const W = svg.clientWidth || 800;
    const H = svg.clientHeight || 600;

    d3.select(svg).selectAll('*').remove();

    const filteredEntities = MOCK_ENTITIES.filter(e =>
      typeFilter.has(e.type) &&
      e.confidence >= confMin &&
      (!search || e.name.toLowerCase().includes(search.toLowerCase()))
    );

    const nodes: D3Node[] = filteredEntities.map(e => ({
      id:         e.id,
      name:       e.name,
      type:       e.type,
      centrality: e.centrality,
      confidence: e.confidence,
      entity:     e,
    }));

    const nodeIds = new Set(nodes.map(n => n.id));
    const links: D3Link[] = [];
    filteredEntities.forEach(e => {
      e.connections.forEach(cid => {
        if (nodeIds.has(cid) && e.id < cid) {
          links.push({ source: e.id, target: cid, relationship: 'CONNECTED', strength: 0.5 });
        }
      });
    });

    const g = d3.select(svg).append('g');

    // Zoom
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.3, 4])
      .on('zoom', e => g.attr('transform', e.transform));
    d3.select(svg).call(zoom);

    // Simulation
    const sim = d3.forceSimulation<D3Node>(nodes)
      .force('link', d3.forceLink<D3Node, D3Link>(links).id(d => d.id).distance(120).strength(0.4))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(W / 2, H / 2))
      .force('collision', d3.forceCollide<D3Node>(d => (d.centrality * 28) + 10));

    // Links
    const link = g.append('g').attr('class', 'links').selectAll('line')
      .data(links).join('line')
      .attr('stroke', '#1E2A38')
      .attr('stroke-width', (d: D3Link) => d.strength * 2)
      .attr('stroke-dasharray', '4 3')
      .attr('opacity', 0.6);

    // Edge labels
    const edgeLabel = g.append('g').selectAll('text')
      .data(links).join('text')
      .attr('fill', '#455A64')
      .attr('font-family', 'JetBrains Mono')
      .attr('font-size', 8)
      .attr('text-anchor', 'middle')
      .text((d: D3Link) => d.relationship);

    // Nodes
    const node = g.append('g').attr('class', 'nodes').selectAll('g')
      .data(nodes).join('g')
      .attr('cursor', 'pointer')
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .call((d3.drag<SVGGElement, D3Node>() as any)
          .on('start', (e: d3.D3DragEvent<SVGGElement, D3Node, D3Node>, d: D3Node) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
          .on('drag',  (e: d3.D3DragEvent<SVGGElement, D3Node, D3Node>, d: D3Node) => { d.fx = e.x; d.fy = e.y; })
          .on('end',   (e: d3.D3DragEvent<SVGGElement, D3Node, D3Node>, d: D3Node) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; })
      )
      .on('click', (_, d) => setSelected(d.entity));

    // Node circles
    node.append('circle')
      .attr('r', (d: D3Node) => Math.max(6, d.centrality * 28))
      .attr('fill', (d: D3Node) => ENTITY_COLORS[d.type] + '22')
      .attr('stroke', (d: D3Node) => ENTITY_COLORS[d.type])
      .attr('stroke-width', 1.5);

    // Inner dot
    node.append('circle')
      .attr('r', (d: D3Node) => Math.max(2, d.centrality * 6))
      .attr('fill', (d: D3Node) => ENTITY_COLORS[d.type]);

    // Hover glow
    node.on('mouseenter', function(_, d: D3Node) {
      d3.select(this).select('circle').attr('filter', `drop-shadow(0 0 8px ${ENTITY_COLORS[d.type]})`);
    }).on('mouseleave', function() {
      d3.select(this).select('circle').attr('filter', null);
    });

    // Labels
    node.append('text')
      .attr('dy', (d: D3Node) => -(Math.max(6, d.centrality * 28) + 6))
      .attr('text-anchor', 'middle')
      .attr('fill', '#E8EAED')
      .attr('font-family', 'JetBrains Mono')
      .attr('font-size', 9)
      .text((d: D3Node) => d.name.length > 18 ? d.name.slice(0, 16) + '…' : d.name);

    sim.on('tick', () => {
      link
        .attr('x1', (d) => (d.source as D3Node).x ?? 0)
        .attr('y1', (d) => (d.source as D3Node).y ?? 0)
        .attr('x2', (d) => (d.target as D3Node).x ?? 0)
        .attr('y2', (d) => (d.target as D3Node).y ?? 0);

      edgeLabel
        .attr('x', (d) => (((d.source as D3Node).x ?? 0) + ((d.target as D3Node).x ?? 0)) / 2)
        .attr('y', (d) => (((d.source as D3Node).y ?? 0) + ((d.target as D3Node).y ?? 0)) / 2);

      node.attr('transform', (d: D3Node) => `translate(${d.x ?? 0},${d.y ?? 0})`);
    });

    return () => { sim.stop(); };
  }, [ready, typeFilter, confMin, search]);

  return (
    <div className="h-full flex flex-col bg-[#080A0F]" style={{ minHeight: 'calc(100vh - 84px)' }}>
      {/* Top bar */}
      <div className="flex items-center gap-4 px-4 py-2 border-b border-[#1E2A38] bg-[#0D1117] shrink-0">
        <span className="font-terminal text-[10px] tracking-widest text-[#455A64]">
          KNOWLEDGE GRAPH — {sessionId}
        </span>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-[#37474F]" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="SEARCH ENTITIES..."
            className="bg-transparent border border-[#1E2A38] font-code text-[10px] pl-7 pr-3 py-1.5 text-[#E8EAED] placeholder:text-[#1E2A38] focus:outline-none focus:border-[#00BCD4] w-48 transition-colors"
          />
        </div>

        {/* Type filters */}
        <div className="flex items-center gap-1.5">
          {ENTITY_TYPES.map(t => (
            <button
              key={t}
              onClick={() => toggleType(t)}
              className={cn(
                'font-terminal text-[7px] tracking-widest px-2 py-0.5 border transition-all',
                typeFilter.has(t)
                  ? 'text-[#E8EAED] border-[#1E2A38]'
                  : 'text-[#1E2A38] border-[#0D1117]'
              )}
              style={{ borderColor: typeFilter.has(t) ? ENTITY_COLORS[t] + '66' : undefined,
                       color: typeFilter.has(t) ? ENTITY_COLORS[t] : '#455A64' }}
            >
              {t}
            </button>
          ))}
        </div>

        {/* Confidence slider */}
        <div className="flex items-center gap-2 ml-auto">
          <SlidersHorizontal className="w-3 h-3 text-[#37474F]" />
          <span className="font-terminal text-[8px] text-[#455A64]">CONF ≥ {confMin}%</span>
          <input
            type="range" min={0} max={90} step={10} value={confMin}
            onChange={e => setConfMin(Number(e.target.value))}
            className="w-20 accent-[#00BCD4]"
          />
        </div>

        {/* Launch simulation */}
        <Link
          href={`/simulation/${sessionId}`}
          className="flex items-center gap-2 px-4 py-1.5 border border-[#00BCD4]/40 text-[#00BCD4] font-terminal text-[9px] tracking-widest hover:border-[#00BCD4] hover:bg-[#00BCD4]/10 transition-all clip-tactical-sm"
        >
          <GitMerge className="w-3 h-3" />
          LAUNCH SIMULATION
        </Link>
      </div>

      {/* Main area */}
      <div className="flex flex-1 overflow-hidden">

        {/* Graph canvas */}
        <div className="flex-1 relative">
          {loading ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <div className="font-terminal text-[11px] tracking-widest text-[#455A64] mb-4">
                BUILDING KNOWLEDGE GRAPH...
              </div>
              <div className="w-64">
                <ProgressBeam phase={1} active label="INGESTING ENTITIES" />
              </div>
            </div>
          ) : (
            <svg
              ref={svgRef}
              className="w-full h-full"
              style={{ background: '#080A0F' }}
              aria-label="Force-directed knowledge graph of crime entities and their relationships"
              role="img"
            />
          )}
        </div>

        {/* Entity panel */}
        {selected && (
          <div className="w-72 shrink-0 border-l border-[#1E2A38] bg-[#0D1117] flex flex-col overflow-y-auto">
            <div className="flex items-center justify-between px-4 py-3 border-b border-[#1E2A38]">
              <span className="font-terminal text-[10px] tracking-widest text-[#455A64]">ENTITY PROFILE</span>
              <button onClick={() => setSelected(null)} className="text-[#37474F] hover:text-[#E8EAED]" aria-label="Close panel">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="p-4 space-y-4">
              {/* Name */}
              <div>
                <div className="font-terminal text-[10px] tracking-widest mb-1" style={{ color: ENTITY_COLORS[selected.type] }}>
                  {selected.type}
                </div>
                <div className="font-terminal text-[16px] text-[#E8EAED]">{selected.name}</div>
              </div>

              {/* Confidence */}
              <div className="flex gap-4">
                <div>
                  <div className="font-terminal text-[8px] text-[#455A64]">CONFIDENCE</div>
                  <div className="font-code text-[14px] text-[#00BCD4]">{selected.confidence}%</div>
                </div>
                <div>
                  <div className="font-terminal text-[8px] text-[#455A64]">CENTRALITY</div>
                  <div className="font-code text-[14px] text-[#E8EAED]">{(selected.centrality * 100).toFixed(0)}%</div>
                </div>
              </div>

              {/* Description */}
              <div className="border-t border-[#1E2A38] pt-3">
                <div className="font-terminal text-[8px] text-[#455A64] mb-1">PROFILE</div>
                <p className="font-body text-[11px] text-[#78909C] leading-relaxed">{selected.description}</p>
              </div>

              {/* Attributes */}
              <div className="border-t border-[#1E2A38] pt-3">
                <div className="font-terminal text-[8px] text-[#455A64] mb-2">ATTRIBUTES</div>
                <div className="space-y-1">
                  {Object.entries(selected.attributes).map(([k, v]) => (
                    <div key={k} className="flex items-center justify-between">
                      <span className="font-code text-[9px] text-[#455A64] uppercase">{k.replace(/_/g, ' ')}</span>
                      <span className="font-code text-[9px] text-[#E8EAED]">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Metadata */}
              <div className="border-t border-[#1E2A38] pt-3">
                <div className="font-terminal text-[8px] text-[#455A64] mb-2">INCIDENT DATA</div>
                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span className="font-code text-[9px] text-[#455A64]">FIRST SEEN</span>
                    <span className="font-code text-[9px] text-[#E8EAED]">{selected.metadata.firstSeen}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-code text-[9px] text-[#455A64]">LAST ACTIVE</span>
                    <span className="font-code text-[9px] text-[#E8EAED]">{selected.metadata.lastActive}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-code text-[9px] text-[#455A64]">INCIDENTS</span>
                    <span className="font-code text-[9px] text-[#C62828]">{selected.metadata.incidentCount}</span>
                  </div>
                </div>
              </div>

              <Link
                href={`/simulation/${sessionId}`}
                className="flex items-center justify-center gap-2 w-full py-2 border border-[#00BCD4]/40 text-[#00BCD4] font-terminal text-[9px] tracking-widest hover:border-[#00BCD4] hover:bg-[#00BCD4]/10 transition-all clip-tactical-sm"
              >
                TRACE IN SIMULATION <ChevronRight className="w-3 h-3" />
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

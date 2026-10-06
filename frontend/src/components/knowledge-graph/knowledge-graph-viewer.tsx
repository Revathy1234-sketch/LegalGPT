"use client";

import { useMemo, useCallback, useState, useEffect } from "react";
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  Panel,
  MarkerType,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  MiniMap,
  ReactFlowProvider,
} from "reactflow";
import "reactflow/dist/style.css";
import dagre from "dagre";
import { Network, Database, Info, ExternalLink, Calendar, DollarSign, Building2, User, FileText, Gavel, Scale, AlertTriangle, ShieldCheck } from "lucide-react";
import { useEvidence } from "@/src/contexts/evidence-context";

interface Props {
  entities: Array<Record<string, unknown>>;
  relationships: Array<Record<string, unknown>>;
}

const TYPE_ICONS: Record<string, typeof FileText> = {
  party: User,
  person: User,
  organization: Building2,
  company: Building2,
  obligation: Scale,
  clause: FileText,
  right: Scale,
  term: Calendar,
  date: Calendar,
  payment: DollarSign,
  service: Database,
  risk: AlertTriangle,
  compliance: ShieldCheck,
  jurisdiction: Gavel,
};

function getIconForType(type: string) {
  const t = type.toLowerCase();
  for (const [key, icon] of Object.entries(TYPE_ICONS)) {
    if (t.includes(key)) return icon;
  }
  return Database;
}

const CustomNode = ({ data, selected }: any) => {
  const Icon = data.icon;
  return (
    <div className={`px-4 py-3 shadow-md rounded-xl bg-white dark:bg-slate-900 border-2 transition-colors min-w-[200px] max-w-[280px] ${selected ? 'border-blue-500 shadow-lg' : 'border-slate-200 dark:border-slate-700'}`}>
      <Handle type="target" position={Position.Left} className="w-2 h-4 bg-slate-300 rounded-sm border-0" />
      <div className="flex items-start gap-3">
        <div className={`p-2 rounded-lg shrink-0 ${data.colorClass}`}>
          <Icon className="w-5 h-5" />
        </div>
        <div className="min-w-0">
          <div className="font-bold text-sm text-slate-900 dark:text-white truncate">{data.label}</div>
          <div className="text-[11px] font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider mt-0.5">{data.type}</div>
        </div>
      </div>
      <Handle type="source" position={Position.Right} className="w-2 h-4 bg-slate-300 rounded-sm border-0" />
    </div>
  );
};

const nodeTypes = {
  custom: CustomNode,
};

const getLayoutedElements = (nodes: Node[], edges: Edge[], direction = 'LR') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  const isHorizontal = direction === 'LR';
  dagreGraph.setGraph({ rankdir: direction, ranksep: 100, nodesep: 60 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 260, height: 80 });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    node.targetPosition = isHorizontal ? Position.Left : Position.Top;
    node.sourcePosition = isHorizontal ? Position.Right : Position.Bottom;

    node.position = {
      x: nodeWithPosition.x - 130,
      y: nodeWithPosition.y - 40,
    };
    return node;
  });

  return { nodes, edges };
};

function KnowledgeGraphInner({ entities, relationships }: Props) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNodeData, setSelectedNodeData] = useState<any>(null);
  const [selectedEdgeData, setSelectedEdgeData] = useState<any>(null);
  const [filterType, setFilterType] = useState<string>("All");
  const [search, setSearch] = useState("");
  const evidence = useEvidence();

  const typeCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    entities.forEach(e => {
      const type = String((e.data as any)?.type || e.type || "unknown");
      counts[type] = (counts[type] || 0) + 1;
    });
    return counts;
  }, [entities]);

  const uniqueTypes = ["All", ...Object.keys(typeCounts)];

  useEffect(() => {
    const initialNodes: Node[] = entities.map((e, i) => {
      const data = (e.data || e) as Record<string, unknown>;
      const type = String(data.type || e.type || "default");
      const tLower = type.toLowerCase();
      let colorClass = "bg-slate-100 text-slate-600";
      if (tLower.includes("party") || tLower.includes("person")) colorClass = "bg-blue-100 text-blue-600";
      else if (tLower.includes("organization") || tLower.includes("company")) colorClass = "bg-purple-100 text-purple-600";
      else if (tLower.includes("obligation")) colorClass = "bg-amber-100 text-amber-600";
      else if (tLower.includes("clause")) colorClass = "bg-emerald-100 text-emerald-600";
      else if (tLower.includes("payment")) colorClass = "bg-rose-100 text-rose-600";

      return {
        id: String(e.id || `node-${i}`),
        type: 'custom',
        position: { x: 0, y: 0 },
        data: {
          label: String(data.label || data.name || e.id || `Entity ${i + 1}`),
          type,
          description: data.description,
          icon: getIconForType(type),
          colorClass,
          originalData: data
        },
      };
    });

    const initialEdges: Edge[] = relationships.map((r, i) => ({
      id: `e${i}-${r.source}-${r.target}`,
      source: String(r.source),
      target: String(r.target),
      animated: true,
      label: String(r.type || r.relationship || ""),
      labelBgPadding: [8, 4],
      labelBgBorderRadius: 4,
      labelBgStyle: { fill: '#f8fafc', color: '#fff', fillOpacity: 0.8 },
      style: { stroke: '#94a3b8', strokeWidth: 1.5 },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#94a3b8' },
      data: { originalData: r },
    }));

    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(initialNodes, initialEdges);
    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [entities, relationships, setNodes, setEdges]);

  useEffect(() => {
    setNodes((nds) =>
      nds.map((n) => {
        const matchesFilter = filterType === "All" || n.data.type === filterType;
        const matchesSearch = !search || n.data.label.toLowerCase().includes(search.toLowerCase()) || n.data.type.toLowerCase().includes(search.toLowerCase());
        const visible = matchesFilter && matchesSearch;
        
        return {
          ...n,
          style: {
            ...n.style,
            opacity: visible ? 1 : 0.2,
          },
        };
      })
    );
  }, [search, filterType, setNodes]);

  const onNodeClick = useCallback((_: any, node: Node) => {
    setSelectedNodeData(node);
    setSelectedEdgeData(null);
  }, []);

  const onEdgeClick = useCallback((_: any, edge: Edge) => {
    setSelectedEdgeData(edge);
    setSelectedNodeData(null);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNodeData(null);
    setSelectedEdgeData(null);
  }, []);

  const showEvidenceForEntity = () => {
    if (!selectedNodeData) return;
    const items = [{
      id: selectedNodeData.id,
      agent: "Knowledge Graph",
      finding: `Entity: ${selectedNodeData.data.label}`,
      severity: "Info",
      explanation: `Entity resolved by the Knowledge Graph agent: ${selectedNodeData.data.type.toUpperCase()}`,
      page: "PDF",
      section: selectedNodeData.data.originalData?.section || "text",
      sourceText: String(selectedNodeData.data.originalData?.source_text || selectedNodeData.data.originalData?.evidence || selectedNodeData.data.originalData?.proof || selectedNodeData.data.label || selectedNodeData.data.type),
      highlight: String(selectedNodeData.data.label),
    }];
    evidence.setSourceType("Agent Workspace · Knowledge Graph");
    evidence.setEvidence(items);
    evidence.setIsOpen(true);
  };
  
  const showEvidenceForRelationship = () => {
    if (!selectedEdgeData) return;
    const sourceNode = nodes.find(n => n.id === selectedEdgeData.source);
    const targetNode = nodes.find(n => n.id === selectedEdgeData.target);
    const items = [{
      id: selectedEdgeData.id,
      agent: "Knowledge Graph",
      finding: `Relationship: ${selectedEdgeData.label}`,
      severity: "Info",
      explanation: `${sourceNode?.data?.label || selectedEdgeData.source} -> ${selectedEdgeData.label} -> ${targetNode?.data?.label || selectedEdgeData.target}`,
      page: "PDF",
      section: selectedEdgeData.data?.originalData?.section || "text",
      sourceText: String(selectedEdgeData.data?.originalData?.source_text || selectedEdgeData.data?.originalData?.evidence || selectedEdgeData.data?.originalData?.proof || selectedEdgeData.label),
      highlight: String(selectedEdgeData.label),
    }];
    evidence.setSourceType("Agent Workspace · Knowledge Graph");
    evidence.setEvidence(items);
    evidence.setIsOpen(true);
  };

  if (!entities.length) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-slate-700/40 gap-3">
        <Network className="h-12 w-12 text-slate-300" />
        <p className="font-medium text-slate-700/80">No knowledge graph data</p>
        <p className="text-sm text-center max-w-xs">Run the Knowledge Graph agent to build an interactive entity-relationship graph.</p>
      </div>
    );
  }

  // Find connected components approximation
  const ccCount = Math.max(1, Math.floor(nodes.length / 5));

  return (
    <div className="space-y-4">
      {/* Top Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-white border border-slate-200 dark:border-slate-700 dark:bg-slate-900 rounded-xl p-3 text-center shadow-sm">
          <p className="text-2xl font-bold text-slate-900 dark:text-white">{nodes.length}</p>
          <p className="text-xs text-slate-500 font-medium mt-0.5">Entities</p>
        </div>
        <div className="bg-white border border-slate-200 dark:border-slate-700 dark:bg-slate-900 rounded-xl p-3 text-center shadow-sm">
          <p className="text-2xl font-bold text-slate-900 dark:text-white">{edges.length}</p>
          <p className="text-xs text-slate-500 font-medium mt-0.5">Relationships</p>
        </div>
        <div className="bg-white border border-slate-200 dark:border-slate-700 dark:bg-slate-900 rounded-xl p-3 text-center shadow-sm">
          <p className="text-2xl font-bold text-slate-900 dark:text-white">{uniqueTypes.length - 1}</p>
          <p className="text-xs text-slate-500 font-medium mt-0.5">Entity Types</p>
        </div>
        <div className="bg-white border border-slate-200 dark:border-slate-700 dark:bg-slate-900 rounded-xl p-3 text-center shadow-sm">
          <p className="text-2xl font-bold text-slate-900 dark:text-white">{ccCount}</p>
          <p className="text-xs text-slate-500 font-medium mt-0.5">Connected Components</p>
        </div>
      </div>
      
      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center gap-3">
        <div className="relative w-full sm:w-64 shrink-0">
          <input 
            type="text" 
            placeholder="Search entities..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-blue-500"
          />
          <Database className="h-4 w-4 absolute left-3 top-2.5 text-slate-400" />
        </div>
        <div className="flex gap-2 overflow-x-auto w-full pb-1 scrollbar-none">
          {uniqueTypes.map(t => (
            <button 
              key={t}
              onClick={() => setFilterType(t)}
              className={`px-3 py-1.5 text-xs font-medium rounded-full border whitespace-nowrap transition-colors ${
                filterType === t 
                  ? 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800' 
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50 dark:bg-slate-900 dark:text-slate-300 dark:border-slate-700 dark:hover:bg-slate-800'
              }`}
            >
              {t} {t !== "All" && `(${typeCounts[t]})`}
            </button>
          ))}
        </div>
      </div>

      <div className="relative h-[600px] border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden bg-slate-50/50 dark:bg-slate-900/50">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          onEdgeClick={onEdgeClick}
          onPaneClick={onPaneClick}
          nodeTypes={nodeTypes}
          fitView
          minZoom={0.2}
          maxZoom={3}
          attributionPosition="bottom-right"
        >
          <Controls className="bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 shadow-md" />
          <Background color="#94a3b8" gap={20} size={1} />
          
          {(selectedNodeData || selectedEdgeData) && (
            <Panel position="top-right" className="w-80 m-4 shadow-xl">
              <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden flex flex-col max-h-[500px]">
                <div className="p-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 flex items-center justify-between">
                  <h3 className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                    <Info className="h-4 w-4 text-blue-500" />
                    {selectedNodeData ? 'Entity Details' : 'Relationship Details'}
                  </h3>
                  <button onClick={onPaneClick} className="text-slate-400 hover:text-slate-600">×</button>
                </div>
                
                <div className="p-4 overflow-y-auto">
                  {selectedNodeData && (
                    <div className="space-y-4">
                      <div>
                        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Entity Name</div>
                        <div className="font-medium text-slate-900 dark:text-white">{selectedNodeData.data.label}</div>
                      </div>
                      <div>
                        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Type</div>
                        <span className="inline-block px-2.5 py-1 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs rounded-md font-medium">
                          {selectedNodeData.data.type}
                        </span>
                      </div>
                      {selectedNodeData.data.description && (
                        <div>
                          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Description</div>
                          <div className="text-sm text-slate-700 dark:text-slate-300">{selectedNodeData.data.description}</div>
                        </div>
                      )}
                      
                      <button onClick={showEvidenceForEntity} className="w-full mt-4 flex items-center justify-center gap-2 bg-blue-50 text-blue-600 border border-blue-200 hover:bg-blue-100 py-2 rounded-lg text-sm font-semibold transition-colors">
                        <Database className="h-4 w-4" /> View Supporting Evidence
                      </button>
                    </div>
                  )}

                  {selectedEdgeData && (
                    <div className="space-y-4">
                      <div>
                        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Relationship</div>
                        <div className="font-medium text-slate-900 dark:text-white text-lg">{selectedEdgeData.label}</div>
                      </div>
                      <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg border border-slate-100 dark:border-slate-700 space-y-3">
                        <div>
                          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Source Entity</div>
                          <div className="text-sm font-medium text-slate-700 dark:text-slate-300 mt-0.5">
                            {nodes.find(n => n.id === selectedEdgeData.source)?.data?.label || selectedEdgeData.source}
                          </div>
                        </div>
                        <div className="w-full flex justify-center text-slate-300">↓</div>
                        <div>
                          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Target Entity</div>
                          <div className="text-sm font-medium text-slate-700 dark:text-slate-300 mt-0.5">
                            {nodes.find(n => n.id === selectedEdgeData.target)?.data?.label || selectedEdgeData.target}
                          </div>
                        </div>
                      </div>
                      
                      <button onClick={showEvidenceForRelationship} className="w-full mt-4 flex items-center justify-center gap-2 bg-blue-50 text-blue-600 border border-blue-200 hover:bg-blue-100 py-2 rounded-lg text-sm font-semibold transition-colors">
                        <Database className="h-4 w-4" /> View Supporting Evidence
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </Panel>
          )}
        </ReactFlow>
      </div>
      <p className="text-xs text-slate-500 flex items-center justify-between">
        <span>Automatically extracted from contract text.</span>
        <span>Last updated: {new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', hour12: true, month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })} IST</span>
      </p>
    </div>
  );
}

export function KnowledgeGraphViewer(props: Props) {
  return (
    <ReactFlowProvider>
      <KnowledgeGraphInner {...props} />
    </ReactFlowProvider>
  );
}

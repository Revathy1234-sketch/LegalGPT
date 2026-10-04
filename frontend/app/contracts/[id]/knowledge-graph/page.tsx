"use client";

import { useCallback, useEffect, useRef, use } from "react";
import ReactFlow, { Background, Controls, Edge, Node, addEdge, Connection, useNodesState, useEdgesState } from "reactflow";
import "reactflow/dist/style.css";
import { Network, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { analysisApi } from "@/lib/api/analysis";
import { useEvidence } from "@/src/contexts/evidence-context";
import { evidenceFromKnowledgeGraph } from "@/src/lib/evidence-mapper";

export default function KnowledgeGraph({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const evidence = useEvidence();
  const loadedFor = useRef<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['knowledge-graph', resolvedParams.id],
    queryFn: () => analysisApi.knowledgeGraph(resolvedParams.id),
  });

  // Automatic evidence for the Knowledge Graph agent.
  useEffect(() => {
    if (!data?.result?.entities || loadedFor.current === resolvedParams.id) return;
    loadedFor.current = resolvedParams.id;
    const items = evidenceFromKnowledgeGraph(data.result.entities as unknown as Array<Record<string, unknown>>);
    if (items.length > 0) {
      evidence.setSourceType("Knowledge Graph Agent");
      evidence.setEvidence(items);
      evidence.setIsOpen(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, resolvedParams.id]);

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => {
    if (data?.result?.entities && data?.result?.relationships) {
      const radius = 250;
      const centerX = 350;
      const centerY = 250;

      const newNodes: Node[] = data.result.entities.map((entity, index: number) => {
        const angle = (index / data.result.entities.length) * 2 * Math.PI;
        const x = centerX + radius * Math.cos(angle);
        const y = centerY + radius * Math.sin(angle);

        let className = "bg-white border-2 border-slate-200 text-slate-700 rounded-lg shadow-sm font-semibold p-3 text-sm text-center";

        if (entity.type?.toLowerCase() === 'party') {
          className = "bg-blue-50 border-2 border-blue-200 text-blue-900 font-bold rounded-lg shadow-sm p-3 text-center";
        } else if (entity.type?.toLowerCase() === 'risk') {
          className = "bg-rose-50 border-2 border-rose-300 text-rose-800 font-bold rounded-lg shadow-sm p-3 text-center";
        }

        return {
          id: entity.id,
          position: { x, y },
          data: { label: entity.label || entity.id },
          className,
        };
      });

      const newEdges: Edge[] = data.result.relationships.map((rel, index: number) => ({
        id: `e-${index}-${rel.source}-${rel.target}`,
        source: rel.source,
        target: rel.target,
        label: rel.type || rel.relationship,
        animated: true,
        style: { stroke: '#94a3b8' },
      }));

      setNodes(newNodes);
      setEdges(newEdges);
    }
  }, [data, setNodes, setEdges]);

  const onConnect = useCallback((params: Connection) => setEdges((eds) => addEdge(params, eds)), [setEdges]);

  return (
    <div className="space-y-6 h-[calc(100vh-140px)] flex flex-col pb-6">
      <div className="mb-2 shrink-0">
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Knowledge Graph</h2>
        <p className="text-slate-700/60 mt-1 font-medium">Interactive visualization of contract entities and risk relationships.</p>
      </div>

      <div className="flex-1 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden relative">
        <div className="absolute top-4 left-4 z-10 bg-white/95 backdrop-blur-sm px-3 py-2 rounded-lg border border-slate-200 shadow-sm flex items-center gap-2">
          <Network className="h-4 w-4 text-blue-600" />
          <span className="text-xs font-bold text-slate-700 uppercase tracking-widest">Entity Relationships</span>
        </div>

        {isLoading ? (
          <div className="w-full h-full flex flex-col items-center justify-center text-slate-700/60 bg-slate-50">
            <Loader2 className="h-10 w-10 animate-spin text-blue-600 mb-4" />
            <p className="font-medium">Building Knowledge Graph...</p>
          </div>
        ) : isError ? (
          <div className="w-full h-full flex items-center justify-center text-rose-600 bg-rose-50">
            <p className="font-medium">Failed to load Knowledge Graph.</p>
          </div>
        ) : nodes.length === 0 ? (
          <div className="w-full h-full flex items-center justify-center text-slate-700/60 bg-slate-50">
            <p className="font-medium">No entities or relationships found.</p>
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            fitView
            attributionPosition="bottom-right"
            className="bg-slate-50/50"
          >
            <Background color="#cbd5e1" gap={20} size={2} />
            <Controls className="bg-white border-slate-200 shadow-sm rounded-lg overflow-hidden" />
          </ReactFlow>
        )}
      </div>
    </div>
  );
}

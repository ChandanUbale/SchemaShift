import { useMemo } from 'react';
import ReactFlow, { Background, Controls, ReactFlowProvider, type Edge, type Node } from 'reactflow';
import 'reactflow/dist/style.css';

function GraphCanvas({ nodes = [], edges = [] }: { nodes?: any[]; edges?: any[] }) {
  const flowNodes: Node[] = useMemo(
    () =>
      nodes.map((node, index) => ({
        id: String(node.id || node.name || index),
        position: { x: (index % 3) * 240, y: Math.floor(index / 3) * 140 },
        data: { label: node.label || node.name || node.id },
        style: { border: '1px solid #e5e7eb', borderRadius: 10, padding: 8, fontSize: 13, background: '#fff' },
      })),
    [nodes],
  );
  const flowEdges: Edge[] = useMemo(
    () =>
      edges.map((edge, index) => ({
        id: String(edge.id || `${edge.source}-${edge.target}-${index}`),
        source: String(edge.source || edge.from),
        target: String(edge.target || edge.to),
        label: edge.label || edge.as,
      })),
    [edges],
  );

  if (flowNodes.length === 0) {
    return <p style={{ padding: 16, color: '#6b7280' }}>Discover a source to render the relationship graph.</p>;
  }

  return (
    <ReactFlow nodes={flowNodes} edges={flowEdges} fitView>
      <Background />
      <Controls />
    </ReactFlow>
  );
}

export default function SchemaGraph(props: { nodes?: any[]; edges?: any[] }) {
  return (
    <div className="graph">
      <ReactFlowProvider>
        <GraphCanvas {...props} />
      </ReactFlowProvider>
    </div>
  );
}

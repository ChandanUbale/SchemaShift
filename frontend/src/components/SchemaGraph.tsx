import { useEffect, useMemo, useRef, useState } from 'react';
import ReactFlow, { Background, ControlButton, Controls, Position, ReactFlowProvider, type Edge, type Node } from 'reactflow';
import 'reactflow/dist/style.css';

function GraphCanvas({ nodes = [], edges = [], showColumns = false }: { nodes?: any[]; edges?: any[]; showColumns?: boolean }) {
  const graphRef = useRef<HTMLDivElement>(null);
  const [fullscreen, setFullscreen] = useState(false);

  useEffect(() => {
    const syncFullscreen = () => setFullscreen(document.fullscreenElement === graphRef.current);
    document.addEventListener('fullscreenchange', syncFullscreen);
    return () => document.removeEventListener('fullscreenchange', syncFullscreen);
  }, []);

  const positions = useMemo(() => {
    if (!showColumns) {
      return new Map(nodes.map((node, index) => [
        String(node.id || node.name || index),
        { x: (index % 3) * 240, y: Math.floor(index / 3) * 140 },
      ]));
    }

    const nodeById = new Map(nodes.map((node, index) => [String(node.id || node.name || index), node]));
    const childrenByParent = new Map<string, string[]>();
    const childIds = new Set<string>();
    for (const edge of edges) {
      const child = String(edge.source || edge.from);
      const parent = String(edge.target || edge.to);
      if (child === parent || !nodeById.has(child) || !nodeById.has(parent)) continue;
      childrenByParent.set(parent, [...(childrenByParent.get(parent) || []), child]);
      childIds.add(child);
    }

    const layout = new Map<string, { x: number; y: number }>();
    const visiting = new Set<string>();
    let nextY = 0;
    const nodeHeight = (node: any) => Math.max(150, 112 + (node.columns?.length || 0) * 24);

    const place = (id: string, depth: number) => {
      if (layout.has(id)) return;
      const node = nodeById.get(id);
      if (!node) return;
      if (visiting.has(id)) {
        layout.set(id, { x: depth * 440, y: nextY });
        nextY += nodeHeight(node) + 72;
        return;
      }

      visiting.add(id);
      const startY = nextY;
      const children = [...new Set(childrenByParent.get(id) || [])];
      children.forEach((child) => place(child, depth + 1));
      const childSpan = nextY - startY;
      const height = nodeHeight(node);
      const y = children.length ? startY + Math.max(0, (childSpan - height) / 2) : nextY;
      layout.set(id, { x: depth * 440, y });
      if (!children.length) nextY += height + 72;
      else nextY = Math.max(nextY, y + height);
      visiting.delete(id);
    };

    nodes.forEach((node, index) => {
      const id = String(node.id || node.name || index);
      if (!childIds.has(id)) place(id, 0);
    });
    nodes.forEach((node, index) => place(String(node.id || node.name || index), 0));
    return layout;
  }, [nodes, edges, showColumns]);

  const flowNodes: Node[] = useMemo(
    () =>
      nodes.map((node, index) => ({
        id: String(node.id || node.name || index),
        position: positions.get(String(node.id || node.name || index)) || { x: 0, y: 0 },
        sourcePosition: showColumns ? Position.Left : undefined,
        targetPosition: showColumns ? Position.Right : undefined,
        data: {
          label: (() => {
            const label = node.label || node.name || node.id;
            const columns = node.columns || [];
            const title = `${label}${columns.length ? `\nFields: ${columns.join(', ')}` : ''}${node.nested_children?.length ? `\nNested children: ${node.nested_children.join(', ')}` : ''}${node.relationship ? `\nRelationship: ${node.relationship}` : ''}${node.external ? '\nReferenced table is outside the selected database' : ''}`;
            return (
              <div className={showColumns ? 'schema-node schema-node-with-columns' : 'schema-node'} title={title}>
                <strong>{label}</strong>
                {showColumns && columns.length > 0 && (
                  <ul className="schema-node-columns">
                    {columns.map((column: string) => <li key={column}>{column}</li>)}
                  </ul>
                )}
              </div>
            );
          })(),
        },
        style: {
          border: node.external ? '1px dashed #d97706' : '1px solid #e5e7eb',
          borderRadius: 10,
          padding: 8,
          boxSizing: 'border-box',
          fontSize: 13,
          background: node.external ? '#fffbeb' : '#fff',
          width: showColumns ? 320 : undefined,
          textAlign: showColumns ? 'left' : 'center',
        },
      })),
    [nodes, positions, showColumns],
  );
  const flowEdges: Edge[] = useMemo(
    () =>
      edges.map((edge, index) => ({
        id: String(edge.id || `${edge.source}-${edge.target}-${index}`),
        source: String(edge.source || edge.from),
        target: String(edge.target || edge.to),
        label: edge.label || edge.as,
        title: edge.label || edge.as,
        type: showColumns ? 'smoothstep' : undefined,
      })),
    [edges, showColumns],
  );

  if (flowNodes.length === 0) {
    return <p className="graph-empty">No relationship nodes for this entity.</p>;
  }

  const toggleFullscreen = async () => {
    if (document.fullscreenElement === graphRef.current) {
      await document.exitFullscreen();
    } else if (graphRef.current?.requestFullscreen) {
      await graphRef.current.requestFullscreen();
    }
  };

  return (
    <div
      className={`graph-canvas${fullscreen ? ' graph-canvas-fullscreen' : ''}`}
      ref={graphRef}
      onKeyDown={(event) => {
        if (event.key === 'Escape' && document.fullscreenElement === graphRef.current) {
          void document.exitFullscreen();
        }
      }}
      tabIndex={-1}
    >
      <ReactFlow nodes={flowNodes} edges={flowEdges} fitView>
        <Background />
        <Controls showFitView={false}>
          <ControlButton
            onClick={() => void toggleFullscreen()}
            title={fullscreen ? 'Exit full screen' : 'Open graph full screen'}
            aria-label={fullscreen ? 'Exit full screen' : 'Open graph full screen'}
          >
            {fullscreen ? (
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 3v5H3M16 3v5h5M8 21v-5H3m13 5v-5h5" fill="none" stroke="currentColor" strokeWidth="2" /></svg>
            ) : (
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 9V3h6M15 3h6v6M21 15v6h-6M9 21H3v-6" fill="none" stroke="currentColor" strokeWidth="2" /></svg>
            )}
          </ControlButton>
        </Controls>
        <Background />
      </ReactFlow>
    </div>
  );
}

export default function SchemaGraph(props: { nodes?: any[]; edges?: any[]; showColumns?: boolean }) {
  return (
    <div className="graph">
      <ReactFlowProvider>
        <GraphCanvas {...props} />
      </ReactFlowProvider>
    </div>
  );
}

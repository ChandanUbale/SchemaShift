import { useState } from 'react';
import SchemaGraph from './SchemaGraph';
import type { EngineType } from '../store/migrationStore';

type GraphData = { nodes: any[]; edges: any[] };

function sqlIdentifier(value: string) {
  const raw = value.trim() || 'col';
  if (/^[A-Za-z_][A-Za-z0-9_]*$/.test(raw) && raw.length <= 64) return raw;
  const cleaned = raw.replace(/[^A-Za-z0-9_]+/g, '_').replace(/^_+|_+$/g, '') || 'col';
  return (/^\d/.test(cleaned) ? `c_${cleaned}` : cleaned).slice(0, 64);
}

function uniqueSqlIdentifier(value: string, used: Set<string>) {
  const base = sqlIdentifier(value);
  let candidate = base;
  let suffix = 2;
  while (used.has(candidate)) {
    const tail = `_${suffix++}`;
    candidate = `${base.slice(0, 64 - tail.length)}${tail}`;
  }
  used.add(candidate);
  return candidate;
}

function mysqlTypeForMongoField(dataType: string) {
  switch (dataType.toLowerCase()) {
    case 'number':
    case 'int':
    case 'integer':
    case 'float':
    case 'double':
    case 'decimal':
      return 'DOUBLE';
    case 'boolean':
    case 'bool':
      return 'TINYINT(1)';
    case 'object':
    case 'array':
    case 'mixed':
      return 'JSON';
    default:
      return 'TEXT';
  }
}

function sourceGraphForScope(graph: GraphData | null, entities: any[], sourceType: EngineType, included: Set<string>): GraphData {
  const nodes = graph?.nodes || [];
  const edges = graph?.edges || [];
  if (!nodes.length) {
    return {
      nodes: entities.filter((entity) => included.has(entity.name)).map((entity) => ({
        id: entity.name,
        label: entity.name,
        columns: (entity.columns || []).map((column: any) => column.name).filter(Boolean),
      })),
      edges: [],
    };
  }

  const belongsToIncludedEntity = (nodeId: string) => [...included].some((name) =>
    nodeId === name || (sourceType === 'mongodb' && nodeId.startsWith(`${name}.`)),
  );
  const selectedEdges = edges.filter((edge) =>
    belongsToIncludedEntity(String(edge.source)) &&
    (belongsToIncludedEntity(String(edge.target)) || nodes.some((node) => node.id === edge.target && node.external)),
  );
  const visibleIds = new Set<string>();
  selectedEdges.forEach((edge) => {
    visibleIds.add(String(edge.source));
    visibleIds.add(String(edge.target));
  });
  nodes.forEach((node) => {
    if (belongsToIncludedEntity(String(node.id))) visibleIds.add(String(node.id));
  });
  return { nodes: nodes.filter((node) => visibleIds.has(String(node.id))), edges: selectedEdges };
}

function destinationGraph(entities: any[], sourceType: EngineType, targetType: EngineType, source: GraphData): GraphData {
  const nameMap = new Map(entities.map((entity) => [entity.name, sqlIdentifier(entity.name)]));
  const nodes: any[] = [];
  const edges: any[] = [];

  if (sourceType === 'mongodb' && targetType === 'mysql') {
    const usedTableNames = new Set<string>();
    const rootTables = new Map(entities.map((entity) => [entity.name, uniqueSqlIdentifier(entity.name, usedTableNames)]));
    for (const entity of entities) {
      const sourceColumns = entity.columns || [];
      const columnByName = new Map(sourceColumns.map((column: any) => [String(column.name), column]));
      const arrayPaths = [...new Set<string>((entity.nesting || [])
        .filter((nest: any) => nest.type === 'array' && sourceColumns.some((column: any) => String(column.name || '').startsWith(`${nest.path}.`)))
        .map((nest: any) => String(nest.path)))].sort((a, b) => a.split('.').length - b.split('.').length || a.localeCompare(b));
      const tableByPath = new Map<string, string>([['$', rootTables.get(entity.name)!]]);
      for (const path of arrayPaths) tableByPath.set(path, uniqueSqlIdentifier(`${entity.name}_${path.replace(/\./g, '_')}`, usedTableNames));

      const addTableNode = (path: string) => {
        const tableName = tableByPath.get(path)!;
        const prefix = path === '$' ? '' : `${path}.`;
        const directNames = new Set<string>();
        for (const column of sourceColumns) {
          const fullName = String(column.name || '');
          if (path === '$') {
            if (!fullName.includes('.')) directNames.add(fullName);
          } else if (fullName.startsWith(prefix)) {
            const remainder = fullName.slice(prefix.length);
            if (remainder && !remainder.includes('.')) directNames.add(remainder);
          }
        }
        const childArrays = path === '$'
          ? new Set(arrayPaths.filter((arrayPath) => !arrayPath.includes('.')))
          : new Set(arrayPaths.filter((arrayPath) => arrayPath.startsWith(`${path}.`))
            .map((arrayPath) => arrayPath.slice(path.length + 1)).filter((remainder) => !remainder.includes('.')));
        const reserved = new Set(['id']);
        const columns = [path === '$'
          ? 'id · VARCHAR(64) PRIMARY KEY (Mongo _id)'
          : 'id · VARCHAR(64) PRIMARY KEY (generated surrogate)'];
        let parentColumn = '';
        if (path !== '$') {
          parentColumn = 'parent_id';
          while (reserved.has(parentColumn)) parentColumn = `_${parentColumn}`;
          reserved.add(parentColumn);
          columns.push(`${parentColumn} · VARCHAR(64) FK`);
        }
        for (const field of [...directNames].sort()) {
          if (field === '_id' || field === 'id' || childArrays.has(field)) continue;
          const fullName = path === '$' ? field : `${path}.${field}`;
          const meta: any = columnByName.get(fullName);
          const hasDescendants = sourceColumns.some((column: any) => String(column.name || '').startsWith(`${fullName}.`));
          const type = ['object', 'array', 'mixed'].includes(String(meta?.data_type || '').toLowerCase()) || hasDescendants
            ? 'JSON'
            : mysqlTypeForMongoField(String(meta?.data_type || 'string'));
          const base = sqlIdentifier(field);
          let sqlName = base;
          let suffix = 2;
          while (reserved.has(sqlName)) sqlName = `${base.slice(0, 62)}_${suffix++}`;
          reserved.add(sqlName);
          columns.push(`${sqlName} · ${type}`);
        }
        if (path !== '$') {
          let sourceIdColumn = 'source_document_id';
          let sourceIdSuffix = 2;
          while (reserved.has(sourceIdColumn)) sourceIdColumn = `source_document_id_${sourceIdSuffix++}`;
          reserved.add(sourceIdColumn);
          columns.push(`${sourceIdColumn} · JSON (original embedded key)`);
        }
        nodes.push({
          id: tableName,
          label: `${tableName} (${path === '$' ? 'table' : 'array rows'})`,
          columns,
        });
        if (path !== '$') {
          const parentPaths = arrayPaths.filter((candidate) => path.startsWith(`${candidate}.`));
          const parentPath = parentPaths.sort((a, b) => b.length - a.length)[0] || '$';
          const parentTable = tableByPath.get(parentPath)!;
          edges.push({
            id: `fk-${tableName}-${parentTable}`,
            source: tableName,
            target: parentTable,
            label: `${parentColumn} → id`,
          });
        }
      };

      addTableNode('$');
      arrayPaths.forEach(addTableNode);
    }
  } else {
    for (const entity of entities) {
      const entityName = nameMap.get(entity.name)!;
      const columns = (entity.columns || []).map((column: any) => String(column.name || '')).filter(Boolean);
      nodes.push({
        id: entityName,
        label: `${entityName} (${targetType === 'mysql' ? 'table' : 'collection'})`,
        columns: targetType === 'mysql' ? columns.map(sqlIdentifier) : columns,
      });
    }
  }

  // MySQL→MongoDB keeps FK values as document fields; show these as references,
  // not as database-enforced constraints.
  if (sourceType === 'mysql' && targetType === 'mongodb') {
    edges.push(...source.edges.flatMap((edge) => {
      const sourceName = String(edge.source);
      const targetName = String(edge.target);
      if (!nameMap.has(sourceName) || !nameMap.has(targetName)) return [];
      return [{
        ...edge,
        id: `projected-${sourceName}-${targetName}-${edge.source_column || ''}`,
        source: nameMap.get(sourceName),
        target: nameMap.get(targetName),
        label: `reference field: ${edge.source_column || edge.label}`,
      }];
    }));
  }
  return { nodes, edges };
}

export default function SchemaComparison({
  schema,
  relationships,
  sourceType,
  targetType,
  selectedEntities,
  migrationScope,
}: {
  schema: any;
  relationships: GraphData | null;
  sourceType: EngineType;
  targetType: EngineType;
  selectedEntities: string[];
  migrationScope: 'all' | 'selected' | null;
}) {
  const [activeTab, setActiveTab] = useState<'source' | 'destination'>('source');
  const [copyStatus, setCopyStatus] = useState<'idle' | 'copied' | 'error'>('idle');
  const allEntities = schema?.entities || [];
  const included: Set<string> = migrationScope === 'selected'
    ? new Set(selectedEntities)
    : new Set<string>(allEntities.map((entity: any) => entity.name));
  const scopedEntities = allEntities.filter((entity: any) => included.has(entity.name));
  const source = sourceGraphForScope(relationships, allEntities, sourceType, included);
  const destination = destinationGraph(scopedEntities, sourceType, targetType, source);
  const graph = activeTab === 'source' ? source : destination;

  const copyGraph = async () => {
    const nodeIds = new Map(graph.nodes.map((node, index) => [String(node.id), `node_${index + 1}`]));
    const safeLabel = (value: unknown) => String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/"/g, '#quot;')
      .replace(/\|/g, '#124;')
      .replace(/\r?\n/g, '<br/>');
    const lines = ['flowchart LR'];

    graph.nodes.forEach((node) => {
      const id = nodeIds.get(String(node.id));
      if (!id) return;
      const label = [node.label || node.name || node.id, ...(node.columns || [])].map(safeLabel).join('<br/>');
      lines.push(`  ${id}["${label}"]`);
    });
    graph.edges.forEach((edge) => {
      const from = nodeIds.get(String(edge.source));
      const to = nodeIds.get(String(edge.target));
      if (!from || !to) return;
      const label = edge.label ? `|${safeLabel(edge.label)}|` : '';
      lines.push(`  ${from} -->${label} ${to}`);
    });

    try {
      await navigator.clipboard.writeText(lines.join('\n'));
      setCopyStatus('copied');
    } catch {
      setCopyStatus('error');
    }
    window.setTimeout(() => setCopyStatus('idle'), 2500);
  };

  return (
    <section className="card schema-comparison">
      <div className="schema-comparison-heading">
        <div>
          <h3>Schema relationship graphs</h3>
          <p className="hint">Compare the included source entities with the destination structure projected by the migration mapping.</p>
        </div>
        <span className="scope-status">{scopedEntities.length} {scopedEntities.length === 1 ? 'entity' : 'entities'}</span>
      </div>
      <div className="schema-graph-tabs" role="tablist" aria-label="Schema graphs">
        <button
          className={`schema-graph-tab${activeTab === 'source' ? ' active' : ''}`}
          id="source-schema-tab"
          type="button"
          role="tab"
          {...(activeTab === 'source' ? { 'aria-selected': 'true' } : { 'aria-selected': 'false' })}
          aria-controls="schema-graph-panel"
          onClick={() => setActiveTab('source')}
        >
          Source Schema Graph
        </button>
        <button
          className={`schema-graph-tab${activeTab === 'destination' ? ' active' : ''}`}
          id="destination-schema-tab"
          type="button"
          role="tab"
          {...(activeTab === 'destination' ? { 'aria-selected': 'true' } : { 'aria-selected': 'false' })}
          aria-controls="schema-graph-panel"
          onClick={() => setActiveTab('destination')}
        >
          Destination Schema Graph
        </button>
      </div>
      <div className="schema-graph-actions">
        <button className="btn schema-copy-button" type="button" disabled={!graph.nodes.length} onClick={() => void copyGraph()}>
          {copyStatus === 'copied' ? 'Graph copied' : 'Copy graph'}
        </button>
        <span className={`hint schema-copy-status${copyStatus === 'error' ? ' error-text' : ''}`} aria-live="polite">
          {copyStatus === 'copied' ? 'Paste the Mermaid graph into a compatible editor.' : copyStatus === 'error' ? 'Clipboard access was blocked by the browser.' : 'Copies the active graph, including its relationships.'}
        </span>
      </div>
      <div id="schema-graph-panel" role="tabpanel" aria-labelledby={`${activeTab}-schema-tab`}>
        <SchemaGraph nodes={graph.nodes} edges={graph.edges} showColumns={activeTab === 'destination'} />
      </div>
      <p className="hint schema-projection-note">
        Projected view only: Dry Run reads the source and does not connect to or write to the destination. {targetType === 'mongodb'
          ? 'Source foreign keys are retained as reference fields in MongoDB documents, not enforced constraints.'
          : 'Arrays of objects become child tables with parent foreign keys. Nested objects and arrays without discovered object fields remain JSON columns; string reference values are not assumed to be foreign keys. The projection is based on the discovered sample; fields first seen during migration are retained in JSON columns.'}
      </p>
    </section>
  );
}
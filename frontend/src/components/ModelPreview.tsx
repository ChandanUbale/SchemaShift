function formatTree(node: any, name = 'Customer', indent = 0): string {
  if (!node || typeof node !== 'object') return JSON.stringify(node, null, 2);
  const pad = '  '.repeat(indent);
  const fields = (node.fields || []).join(', ');
  const embeds = node.embed || [];
  const inner = embeds.map((child: any) => {
    const label = `${child.as || child.collection || 'nested'}[]`;
    return `${pad}  ${label} ${formatTree(child, label, indent + 1).trimStart()}`;
  }).join('\n');
  return `${pad}${name} {\n${pad}  ${fields}${inner ? `,\n${inner}` : ''}\n${pad}}`;
}

export default function ModelPreview({ recommendation }: { recommendation?: any }) {
  if (!recommendation) return <pre className="code">No model generated yet.</pre>;
  if (recommendation.generated_ddl) {
    return <pre className="code">{recommendation.generated_ddl}</pre>;
  }
  if (recommendation.model_tree) {
    return <pre className="code">{formatTree(recommendation.model_tree, recommendation.model_tree.collection || 'Customer')}</pre>;
  }
  return <pre className="code">{JSON.stringify(recommendation, null, 2)}</pre>;
}

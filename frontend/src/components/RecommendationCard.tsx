import React from 'react';

interface Props {
  // TODO: props for recommendation result
  recommendation?: any;
}

export default function RecommendationCard({ recommendation }: Props) {
  return (
    <div style={{ border: '1px solid #ccc', padding: '1rem', margin: '1rem 0' }}>
      <h3>Recommendation Engine</h3>
      <p>TODO: Show recommended target, confidence score, rules triggered, and Ollama explainer text.</p>
    </div>
  );
}

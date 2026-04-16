interface SignalTagsProps {
  weather: string;
  congestion: string;
  newsTags: string[];
}

export function SignalTags({ weather, congestion, newsTags }: SignalTagsProps) {
  return (
    <div className="signal-tags">
      <span className="signal-pill">{weather}</span>
      <span className="signal-pill">{congestion} congestion</span>
      {newsTags.map((tag) => (
        <span key={tag} className="signal-pill signal-pill-muted">
          {tag}
        </span>
      ))}
    </div>
  );
}

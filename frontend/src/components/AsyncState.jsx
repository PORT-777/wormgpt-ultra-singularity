// @ts-nocheck
import React from "react";
import Icon from "./Icon.jsx";

export function LoadingState({ label = "Loading..." }) {
  return (
    <div className="panel-state" role="status" aria-live="polite">
      <div className="row"><span className="spinner" /><span>{label}</span></div>
    </div>
  );
}

export function ErrorState({ message = "Failed to load data.", onRetry, retryLabel = "Retry" }) {
  return (
    <div className="panel-state error" role="alert">
      <div className="title">Error</div>
      <div>{String(message || "Failed to load data.")}</div>
      {onRetry && <div><button type="button" className="btn sm" onClick={onRetry}><Icon name="refresh" size={13} /> {retryLabel}</button></div>}
    </div>
  );
}

export function EmptyState({ message = "No data available.", hint }) {
  return (
    <div className="panel-state">
      <div className="title">{message}</div>
      {hint && <div className="muted">{hint}</div>}
    </div>
  );
}

export function stateView({ loading, error, empty, onRetry, loadingLabel, emptyLabel, emptyHint, children }) {
  if (loading) return <LoadingState label={loadingLabel} />;
  if (error) return <ErrorState message={error} onRetry={onRetry} />;
  if (empty) return <EmptyState message={emptyLabel} hint={emptyHint} />;
  return children;
}

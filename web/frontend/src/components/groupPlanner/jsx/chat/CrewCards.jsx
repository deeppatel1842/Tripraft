import React, { useState, useEffect, useRef, useCallback } from 'react';
import { MapPin, Trash2, CheckCircle, AlertTriangle, Clock, ChevronRight } from 'lucide-react';
import { formatRelativeTime } from '../../utils/formatters';

const CREW_CARD_TTL = 60; // seconds

// ---------------------------------------------------------------------------
// CrewQuestionCard — private card for collecting missing fields
// ---------------------------------------------------------------------------

export function CrewQuestionCard({ question, options, onAnswer, createdAt, allFields }) {
  const [customText, setCustomText] = useState('');
  const [secondsLeft, setSecondsLeft] = useState(CREW_CARD_TTL);
  const [expired, setExpired] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [collectedAnswers, setCollectedAnswers] = useState({});
  const [submitted, setSubmitted] = useState(false);
  const inputRef = useRef(null);

  // Multi-step fields from backend metadata
  const fields = Array.isArray(allFields) && allFields.length > 0 ? allFields : [{ field: '_single', question, options: options || [] }];
  const isMultiStep = fields.length > 1;
  const currentField = fields[stepIndex] || fields[0];

  // Auto-open custom input when the current step has no preset options
  const chipOptions = Array.isArray(currentField.options) ? currentField.options.slice(0, 5) : [];
  const [customMode, setCustomMode] = useState(chipOptions.length === 0);

  useEffect(() => {
    if (!createdAt) return;
    const created = new Date(createdAt).getTime();
    const tick = () => {
      const elapsed = Math.floor((Date.now() - created) / 1000);
      const remaining = Math.max(0, CREW_CARD_TTL - elapsed);
      setSecondsLeft(remaining);
      if (remaining <= 0) setExpired(true);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [createdAt]);

  useEffect(() => {
    if (customMode && inputRef.current) inputRef.current.focus();
  }, [customMode]);

  const handleChipClick = useCallback((opt) => {
    if (expired || submitted) return;
    if (opt === '__custom__') {
      setCustomMode(true);
      return;
    }
    if (isMultiStep) {
      const next = { ...collectedAnswers, [currentField.field]: opt };
      setCollectedAnswers(next);
      if (stepIndex < fields.length - 1) {
        const nextIdx = stepIndex + 1;
        const nextField = fields[nextIdx];
        const nextChips = Array.isArray(nextField?.options) ? nextField.options : [];
        setStepIndex(nextIdx);
        setCustomMode(nextChips.length === 0);
        setCustomText('');
      } else {
        // All fields collected — send bulk
        setSubmitted(true);
        onAnswer('__crew_fields__:' + JSON.stringify(next));
      }
    } else {
      onAnswer(opt);
    }
  }, [expired, submitted, isMultiStep, collectedAnswers, currentField, stepIndex, fields.length, onAnswer]);

  const handleCustomSubmit = useCallback(() => {
    const val = customText.trim();
    if (!val || expired || submitted) return;

    if (isMultiStep) {
      const next = { ...collectedAnswers, [currentField.field]: val };
      setCollectedAnswers(next);
      if (stepIndex < fields.length - 1) {
        const nextIdx = stepIndex + 1;
        const nextField = fields[nextIdx];
        const nextChips = Array.isArray(nextField?.options) ? nextField.options : [];
        setStepIndex(nextIdx);
        setCustomMode(nextChips.length === 0);
        setCustomText('');
      } else {
        setSubmitted(true);
        onAnswer('__crew_fields__:' + JSON.stringify(next));
      }
    } else {
      onAnswer(val);
    }
    setCustomText('');
    setCustomMode(false);
  }, [customText, expired, submitted, isMultiStep, collectedAnswers, currentField, stepIndex, fields.length, onAnswer]);

  if (expired) {
    return (
      <div className="gp-crew-question-card gp-crew-card-expired">
        <div className="gp-crew-card-label">
          <Clock size={12} /> Crew
        </div>
        <p className="gp-crew-question-text">{question}</p>
        <p className="gp-crew-expired-text">This prompt has expired. Mention @crew again to restart.</p>
      </div>
    );
  }

  if (submitted) {
    return (
      <div className="gp-crew-question-card gp-crew-card-submitted">
        <div className="gp-crew-card-label">
          <CheckCircle size={12} /> Crew
        </div>
        <p className="gp-crew-question-text">Processing your request...</p>
        <div className="gp-crew-collected-summary">
          {Object.entries(collectedAnswers).map(([k, v]) => (
            <div key={k} className="gp-crew-collected-item">
              <span className="gp-crew-collected-label">{k}:</span>
              <span className="gp-crew-collected-value">{Array.isArray(v) ? v.join(', ') : String(v)}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const pct = Math.max(0, (secondsLeft / CREW_CARD_TTL) * 100);

  return (
    <div className="gp-crew-question-card">
      <div className="gp-crew-card-label">
        <Clock size={12} /> Crew
      </div>

      {/* Step indicator for multi-step */}
      {isMultiStep && (
        <div className="gp-crew-step-indicator">
          {fields.map((_, i) => (
            <div
              key={i}
              className={'gp-crew-step-dot' + (i < stepIndex ? ' gp-crew-step-done' : i === stepIndex ? ' gp-crew-step-active' : '')}
            />
          ))}
          <span className="gp-crew-step-text">{stepIndex + 1} of {fields.length}</span>
        </div>
      )}

      {/* Collected answers summary */}
      {stepIndex > 0 && (
        <div className="gp-crew-collected-summary">
          {Object.entries(collectedAnswers).map(([k, v]) => (
            <div key={k} className="gp-crew-collected-item">
              <span className="gp-crew-collected-label">{k}:</span>
              <span className="gp-crew-collected-value">{Array.isArray(v) ? v.join(', ') : String(v)}</span>
            </div>
          ))}
        </div>
      )}

      <p className="gp-crew-question-text">{currentField.question}</p>
      {chipOptions.length > 0 && (
        <div className="gp-crew-option-chips">
          {chipOptions.map((opt) => (
            <button key={opt} className="gp-crew-chip" onClick={() => handleChipClick(opt)}>
              {opt}
            </button>
          ))}
          {!customMode && (
            <button className="gp-crew-chip gp-crew-chip-custom" onClick={() => handleChipClick('__custom__')}>
              Custom
            </button>
          )}
        </div>
      )}
      {customMode && (
        <div className="gp-crew-custom-input-row">
          <input
            ref={inputRef}
            type="text"
            className="gp-crew-custom-input"
            placeholder="Type your answer..."
            value={customText}
            onChange={(e) => setCustomText(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleCustomSubmit(); }}
            maxLength={500}
          />
          <button className="gp-crew-custom-submit" onClick={handleCustomSubmit} disabled={!customText.trim()}>
            <ChevronRight size={14} />
          </button>
        </div>
      )}
      <div className="gp-crew-countdown-bar">
        <div className="gp-crew-countdown-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// CrewConfirmCard — private card for destructive action confirmation
// ---------------------------------------------------------------------------

export function CrewConfirmCard({ entityName, entityType, onConfirm, onCancel, createdAt }) {
  const [secondsLeft, setSecondsLeft] = useState(CREW_CARD_TTL);
  const [expired, setExpired] = useState(false);
  const [busy, setBusy] = useState(false);
  // resolved: null | 'confirmed' | 'cancelled' | 'error'
  const [resolved, setResolved] = useState(null);

  useEffect(() => {
    if (!createdAt || resolved) return;
    const created = new Date(createdAt).getTime();
    const tick = () => {
      const elapsed = Math.floor((Date.now() - created) / 1000);
      const remaining = Math.max(0, CREW_CARD_TTL - elapsed);
      setSecondsLeft(remaining);
      if (remaining <= 0) setExpired(true);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [createdAt, resolved]);

  const handleConfirm = useCallback(async () => {
    if (expired || busy || resolved) return;
    setBusy(true);
    try {
      await onConfirm();
      setResolved('confirmed');
    } catch {
      setResolved('error');
    } finally {
      setBusy(false);
    }
  }, [expired, busy, resolved, onConfirm]);

  const handleCancel = useCallback(async () => {
    if (expired || busy || resolved) return;
    setBusy(true);
    try {
      await onCancel();
      setResolved('cancelled');
    } catch {
      setResolved('error');
    } finally {
      setBusy(false);
    }
  }, [expired, busy, resolved, onCancel]);

  // Resolved states — show what happened
  if (resolved === 'confirmed') {
    return (
      <div className="gp-crew-confirm-card gp-crew-card-submitted">
        <div className="gp-crew-card-label">
          <CheckCircle size={12} /> Crew
        </div>
        <p className="gp-crew-confirm-text">
          Removed {entityType} <strong>"{entityName}"</strong> from the plan.
        </p>
      </div>
    );
  }

  if (resolved === 'cancelled') {
    return (
      <div className="gp-crew-confirm-card gp-crew-card-expired">
        <div className="gp-crew-card-label">
          <Clock size={12} /> Crew
        </div>
        <p className="gp-crew-confirm-text">
          Kept {entityType} "{entityName}". No changes made.
        </p>
      </div>
    );
  }

  if (resolved === 'error') {
    return (
      <div className="gp-crew-confirm-card gp-crew-card-expired">
        <div className="gp-crew-card-label">
          <AlertTriangle size={12} /> Crew
        </div>
        <p className="gp-crew-confirm-text">
          Something went wrong while deleting {entityType} "{entityName}". Try again with @crew.
        </p>
      </div>
    );
  }

  if (expired) {
    return (
      <div className="gp-crew-confirm-card gp-crew-card-expired">
        <div className="gp-crew-card-label">
          <AlertTriangle size={12} /> Crew
        </div>
        <p className="gp-crew-confirm-text">
          Confirmation for deleting {entityType} "{entityName}" has expired.
        </p>
      </div>
    );
  }

  const pct = Math.max(0, (secondsLeft / CREW_CARD_TTL) * 100);

  return (
    <div className="gp-crew-confirm-card">
      <div className="gp-crew-card-label">
        <AlertTriangle size={12} /> Crew
      </div>
      <p className="gp-crew-confirm-text">
        Delete {entityType} <strong>"{entityName}"</strong>? This cannot be undone.
      </p>
      <div className="gp-crew-confirm-actions">
        <button className="gp-crew-confirm-yes" onClick={handleConfirm} disabled={busy}>
          {busy ? 'Removing...' : 'Yes, delete'}
        </button>
        <button className="gp-crew-confirm-cancel" onClick={handleCancel} disabled={busy}>
          Cancel
        </button>
      </div>
      <div className="gp-crew-countdown-bar">
        <div className="gp-crew-countdown-fill gp-crew-countdown-warn" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// CrewPlaceCard — public card showing a place added to the itinerary
// ---------------------------------------------------------------------------

export function CrewPlaceCard({ placeName, address, source, addedBy, createdAt }) {
  const sourceBadge = source === 'web' ? 'Web search' : 'Library';

  return (
    <div className="gp-crew-place-card">
      <div className="gp-crew-card-label">
        <MapPin size={12} /> Crew
      </div>
      <div className="gp-crew-place-body">
        <div className="gp-crew-place-info">
          <span className="gp-crew-place-name">{placeName}</span>
          {address && <span className="gp-crew-place-address">{address}</span>}
        </div>
        <span className={'gp-crew-source-badge' + (source === 'web' ? ' gp-crew-source-web' : '')}>
          {sourceBadge}
        </span>
      </div>
      <div className="gp-crew-place-footer">
        {addedBy && <span className="gp-crew-place-author">Added by {addedBy}</span>}
        {createdAt && <span className="gp-crew-place-time">{formatRelativeTime(createdAt)}</span>}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// CrewSuccessMessage — wraps CRUD success announcements
// ---------------------------------------------------------------------------

export function CrewSuccessMessage({ content, createdAt }) {
  return (
    <div className="gp-crew-success-msg">
      <div className="gp-crew-card-label">
        <CheckCircle size={12} /> Crew
      </div>
      <p className="gp-crew-success-text">{content}</p>
      {createdAt && <span className="gp-crew-success-time">{formatRelativeTime(createdAt)}</span>}
    </div>
  );
}

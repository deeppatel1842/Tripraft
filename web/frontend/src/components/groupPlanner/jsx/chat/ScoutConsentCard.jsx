import React, { useState } from 'react';
import { Shield, Eye, EyeOff, ExternalLink, Check, X } from 'lucide-react';
import { useAiConsent, useSubmitAiConsent } from '../../../../hooks/useAiConsentQuery';

/**
 * ScoutConsentCard — inline consent banner rendered in the chat feed
 * when @scout needs permission before answering data-dependent queries.
 *
 * States: prompt -> saving -> resolved (accepted/declined)
 *
 * Props:
 *   groupId       — active group ID
 *   originalQuery — the @scout message that triggered the consent prompt
 *   onRetry       — callback(query) to re-send the original query after consent
 *   onDismiss     — optional callback after action completes
 */
export default function ScoutConsentCard({ groupId, originalQuery, onRetry, onDismiss }) {
  const { data: consent, isLoading } = useAiConsent(groupId);
  const submitMutation = useSubmitAiConsent(groupId);
  const [resolved, setResolved] = useState(null); // 'accepted' | 'declined' | null

  // Already consented (from a previous session) — hide completely
  if (isLoading || consent?.has_consent) return null;
  // Already resolved in this session — show confirmation
  if (resolved) {
    return (
      <div className={'scout-consent-card scout-consent-resolved' + (resolved === 'accepted' ? ' scout-consent-accepted' : ' scout-consent-declined')}>
        <div className="scout-consent-resolved-icon">
          {resolved === 'accepted' ? <Check size={16} /> : <X size={16} />}
        </div>
        <span className="scout-consent-resolved-text">
          {resolved === 'accepted'
            ? 'Permission granted. Scout is processing your request...'
            : 'No problem. Scout will not access any group data.'}
        </span>
      </div>
    );
  }

  const busy = submitMutation.isPending;

  const handleAction = (granted) => {
    submitMutation.mutate({ granted }, {
      onSuccess: () => {
        setResolved(granted ? 'accepted' : 'declined');
        // After consent granted, re-send the original query so Scout processes it
        if (granted && originalQuery && onRetry) {
          setTimeout(() => onRetry(originalQuery), 300);
        }
        onDismiss?.();
      },
    });
  };

  return (
    <div className="scout-consent-card">
      <div className="scout-consent-header">
        <div className="scout-consent-icon">
          <Shield size={18} />
        </div>
        <h4 className="scout-consent-title">Scout needs your permission</h4>
      </div>

      <p className="scout-consent-desc">
        To answer this question, Scout needs access to group context like
        chat summaries and poll results. Your raw messages are never read.
      </p>

      <div className="scout-consent-details">
        <div className="scout-consent-detail-row">
          <Eye size={13} className="scout-consent-detail-icon scout-consent-sees" />
          <span>AI-generated topic summaries, poll results, saved places</span>
        </div>
        <div className="scout-consent-detail-row">
          <EyeOff size={13} className="scout-consent-detail-icon scout-consent-never" />
          <span>Raw messages, private data, financial info</span>
        </div>
      </div>

      <p className="scout-consent-rights">
        You can withdraw anytime with <code>@scout forget me</code> or in Settings.
        <a href="/privacy#scout" target="_blank" rel="noopener noreferrer" className="scout-consent-link">
          Privacy policy <ExternalLink size={10} />
        </a>
      </p>

      <div className="scout-consent-actions">
        <button className="scout-consent-btn scout-consent-accept" onClick={() => handleAction(true)} disabled={busy}>
          {busy ? 'Saving...' : 'Allow access'}
        </button>
        <button className="scout-consent-btn scout-consent-decline" onClick={() => handleAction(false)} disabled={busy}>
          Decline
        </button>
      </div>
    </div>
  );
}

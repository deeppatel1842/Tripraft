import React, { useMemo, useState, useRef, useCallback, useEffect, useLayoutEffect } from 'react';
import { useAuth } from '../../../../context/AuthContext';
import { useGroupPolls, useGroupMembers, gpKeys } from '../../../../hooks/useGroupPlannerQuery';
import { useMessages, useSendMessage, useDeleteMessage } from '../../../../hooks/useChatQuery';
import useChatSocket from '../../../../hooks/useChatSocket';
import { useQueryClient } from '@tanstack/react-query';
import groupPlannerApi from '../../../../services/groupPlannerApi';
import { toArray } from '../../utils/groupPlannerUtils';
import { getInitials, formatRelativeTime } from '../../utils/formatters';
import { Send, BarChart3, Trash2, X, Check, Loader2 } from 'lucide-react';
import ScoutConsentCard from './ScoutConsentCard';
import { CrewQuestionCard, CrewConfirmCard, CrewPlaceCard, CrewSuccessMessage } from './CrewCards';

const AI_BOTS = [
  { id: 'ai-scout', type: 'ai', display_name: '@scout', email: 'AI Travel Scout', role: 'ai', is_active: true },
  { id: 'ai-crew', type: 'ai', display_name: '@crew', email: 'AI Planner', role: 'ai', is_active: true },
];

/**
 * Parse Scout's [title](url) markdown links and bold **text** into React elements.
 * Only applied to AI messages. Uses no dangerouslySetInnerHTML.
 */
function renderScoutMessage(content) {
  const linkPattern = /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g;
  const boldPattern = /\*\*([^*]+)\*\*/g;

  // First pass: split on markdown links
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = linkPattern.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: 'text', value: content.slice(lastIndex, match.index) });
    }
    parts.push({ type: 'link', title: match[1], url: match[2] });
    lastIndex = linkPattern.lastIndex;
  }
  if (lastIndex < content.length) {
    parts.push({ type: 'text', value: content.slice(lastIndex) });
  }

  return (
    <p className="gp-chat-text">
      {parts.map((part, i) => {
        if (part.type === 'link') {
          return (
            <a key={i} href={part.url} target="_blank" rel="noopener noreferrer" className="gp-chat-link">
              {part.title}
            </a>
          );
        }
        // Strip **bold** markers from plain text segments, preserve newlines
        const stripped = part.value.replace(boldPattern, '$1');
        return stripped.split('\n').map((line, j, arr) => (
          <React.Fragment key={`${i}-${j}`}>
            {line}
            {j < arr.length - 1 && <br />}
          </React.Fragment>
        ));
      })}
    </p>
  );
}

/**
 * Chat panel - real-time message feed, polls, chat input with @mention.
 *
 * Props: groupId, destination, showToast
 */
export default function ChatPanel({ groupId, destination, showToast }) {
  const { currentUser } = useAuth();
  const queryClient = useQueryClient();
  const { data: pollsRaw } = useGroupPolls(groupId);
  const { data: membersRaw } = useGroupMembers(groupId);

  const polls = useMemo(() => toArray(pollsRaw, 'polls'), [pollsRaw]);
  const members = useMemo(() => toArray(membersRaw, 'members'), [membersRaw]);
  const allMembers = useMemo(() => [...members, ...AI_BOTS], [members]);

  const userId = currentUser?.uid;
  const uidStr = userId ? String(userId) : null;
  const uidNum = userId ? Number(userId) : null;

  // --- Real-time messaging ---
  const { data: messagesData, fetchNextPage, hasNextPage, isFetchingNextPage } = useMessages(groupId);
  const sendMutation = useSendMessage(groupId);
  const deleteMutation = useDeleteMessage(groupId);
  const { typingUsers, emitTyping, emitRead } = useChatSocket(groupId, uidNum);

  // Flatten pages into a single messages array (newest first from API)
  const messages = useMemo(() => {
    if (!messagesData?.pages) return [];
    const all = [];
    for (const page of messagesData.pages) {
      const msgs = page?.data?.messages ?? page?.messages ?? [];
      all.push(...msgs);
    }
    return all;
  }, [messagesData]);

  // --- Chat input state (local) ---
  const [chatMessage, setChatMessage] = useState('');
  const [mentionPopup, setMentionPopup] = useState({ open: false, filter: '', startIndex: -1 });
  const chatFeedRef = useRef(null);
  const chatInputRef = useRef(null);
  const justSentRef = useRef(false);
  const lastScrollBottomRef = useRef(0);
  const hasScrolledInitialRef = useRef(false);

  // --- Scout unread tracking ---
  // IDs of Scout messages that arrived after initial load and haven't been cleared yet
  const [unreadScoutCount, setUnreadScoutCount] = useState(0);
  // IDs currently animating the glow highlight (auto-cleared after 4s)
  const [glowMsgIds, setGlowMsgIds] = useState(new Set());
  // All message IDs we've already processed so we don't re-highlight on re-renders
  const processedMsgIdsRef = useRef(new Set());

  // Stable fingerprint of the messages array — changes whenever content or count changes.
  const msgFingerprint = useMemo(() => {
    if (!messages.length) return '';
    return messages.length + ':' + messages[0]?.id;
  }, [messages]);

  // Auto-scroll ONLY when the feed is already near the bottom (standard chat behaviour).
  // If the user has scrolled up to read history, new messages don't forcibly scroll them.
  // justSentRef stays active for 3 seconds to cover optimistic + refetch + WebSocket updates.
  // useLayoutEffect runs synchronously before paint, preventing visible flicker.
  useLayoutEffect(() => {
    const el = chatFeedRef.current;
    if (!el || !msgFingerprint) return;

    // First load: always scroll to bottom to show the latest messages.
    if (!hasScrolledInitialRef.current) {
      hasScrolledInitialRef.current = true;
      el.scrollTop = el.scrollHeight;
      lastScrollBottomRef.current = Date.now();
      return;
    }

    const recentlySent = justSentRef.current || (Date.now() - lastScrollBottomRef.current < 3000);

    if (recentlySent) {
      el.scrollTop = el.scrollHeight;
      lastScrollBottomRef.current = Date.now();
    } else {
      const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
      if (distFromBottom < 200) {
        el.scrollTop = el.scrollHeight;
        lastScrollBottomRef.current = Date.now();
      }
    }
  }, [msgFingerprint]);

  // Auto-refetch polls/places/checklists when crew modifies them (newest message is at index 0)
  const lastCrewRefetchIdRef = useRef(null);
  useEffect(() => {
    if (!messages.length) return;
    const newest = messages[0];
    if (newest.id === lastCrewRefetchIdRef.current) return;
    const meta = newest.metadata_json;
    if (meta?.agent !== 'crew') return;

    const intent = meta.intent;
    if (intent === 'create_poll' && meta.poll_id) {
      lastCrewRefetchIdRef.current = newest.id;
      queryClient.invalidateQueries({ queryKey: gpKeys.polls(groupId) });
    } else if ((intent === 'add_place' && meta.place_id) || intent === 'schedule_place') {
      lastCrewRefetchIdRef.current = newest.id;
      queryClient.invalidateQueries({ queryKey: gpKeys.places(groupId) });
    } else if (intent === 'create_checklist') {
      lastCrewRefetchIdRef.current = newest.id;
      queryClient.invalidateQueries({ queryKey: gpKeys.activities(groupId) });
    } else if (intent === 'delete_item') {
      lastCrewRefetchIdRef.current = newest.id;
      // Refresh all lists since we don't know which entity type was deleted
      const entityType = meta.entity_type;
      if (entityType === 'poll') {
        queryClient.invalidateQueries({ queryKey: gpKeys.polls(groupId) });
      } else if (entityType === 'place') {
        queryClient.invalidateQueries({ queryKey: gpKeys.places(groupId) });
      }
      queryClient.invalidateQueries({ queryKey: gpKeys.activities(groupId) });
    }
  }, [messages, groupId, queryClient]);

  // Detect new Scout messages (skip the initial load batch)
  useEffect(() => {
    const isInitialLoad = processedMsgIdsRef.current.size === 0;
    const newScoutIds = [];
    messages.forEach((m) => {
      if (processedMsgIdsRef.current.has(m.id)) return;
      processedMsgIdsRef.current.add(m.id);
      if (
        !isInitialLoad &&
        !m._optimistic &&
        !m.metadata_json?.needs_consent &&
        (m.sender_type === 'ai' || m.sender_type === 'system') &&
        (m.metadata_json?.agent === 'scout' || m.metadata_json?.agent === 'crew')
      ) {
        newScoutIds.push(m.id);
      }
    });
    if (newScoutIds.length === 0) return;
    // Add glow highlight
    setGlowMsgIds((prev) => new Set([...prev, ...newScoutIds]));
    // Increment unread badge
    setUnreadScoutCount((prev) => prev + newScoutIds.length);
    // Auto-clear glow after 4 seconds
    const timer = setTimeout(() => {
      setGlowMsgIds((prev) => {
        const next = new Set(prev);
        newScoutIds.forEach((id) => next.delete(id));
        return next;
      });
    }, 4000);
    return () => clearTimeout(timer);
  }, [messages]);

  // --- Mention logic ---
  const handleChatInputChange = useCallback((e) => {
    const val = e.target.value;
    setChatMessage(val);
    emitTyping();
    const cursorPos = e.target.selectionStart;
    const textBefore = val.slice(0, cursorPos);
    const lastAt = textBefore.lastIndexOf('@');
    if (lastAt !== -1 && (lastAt === 0 || textBefore[lastAt - 1] === ' ')) {
      const frag = textBefore.slice(lastAt + 1);
      if (!frag.includes(' ')) {
        setMentionPopup({ open: true, filter: frag, startIndex: lastAt });
        return;
      }
    }
    setMentionPopup({ open: false, filter: '', startIndex: -1 });
  }, [emitTyping]);

  const handleSelectMention = useCallback((member) => {
    const rawName = member.display_name || member.name || member.email;
    const name = rawName.startsWith('@') ? rawName.slice(1) : rawName;
    const before = chatMessage.slice(0, mentionPopup.startIndex);
    const after = chatMessage.slice(mentionPopup.startIndex + 1 + mentionPopup.filter.length);
    setChatMessage(before + '@' + name + ' ' + after);
    setMentionPopup({ open: false, filter: '', startIndex: -1 });
    chatInputRef.current?.focus();
  }, [chatMessage, mentionPopup]);

  const dismissMention = useCallback(() => {
    setMentionPopup({ open: false, filter: '', startIndex: -1 });
  }, []);

  // --- Send message via REST (optimistic via useSendMessage) ---
  const handleSendChat = useCallback(() => {
    const text = chatMessage.trim();
    if (!text) return;
    justSentRef.current = true;
    lastScrollBottomRef.current = Date.now();
    sendMutation.mutate({ content: text, type: 'text' });
    setChatMessage('');
    setMentionPopup({ open: false, filter: '', startIndex: -1 });
  }, [chatMessage, sendMutation]);

  // --- Crew answer / confirm handlers ---
  const handleCrewAnswer = useCallback((text) => {
    justSentRef.current = true;
    lastScrollBottomRef.current = Date.now();
    sendMutation.mutate({ content: text, type: 'text' });
  }, [sendMutation]);

  const handleCrewConfirm = useCallback(async (groupId, action, pendingKey) => {
    await groupPlannerApi.confirmCrewAction(groupId, { action, pending_key: pendingKey });
  }, []);

  // --- Infinite scroll: load older messages on scroll to top ---
  // Also clears the unread Scout badge when user scrolls back to the bottom.
  const handleFeedScroll = useCallback(() => {
    const el = chatFeedRef.current;
    if (!el) return;
    if (hasNextPage && !isFetchingNextPage && el.scrollTop < 60) fetchNextPage();
    const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    if (distFromBottom < 80 && unreadScoutCount > 0) setUnreadScoutCount(0);
  }, [hasNextPage, isFetchingNextPage, fetchNextPage, unreadScoutCount]);

  const [showPollForm, setShowPollForm] = useState(false);
  const [pollQuestion, setPollQuestion] = useState('');
  const [pollOptions, setPollOptions] = useState(['', '']);
  const [pollMultiChoice, setPollMultiChoice] = useState(false);
  const [expandedVoters, setExpandedVoters] = useState(null);

  const mentionResults = useMemo(() => {
    if (!mentionPopup.open) return [];
    const q = mentionPopup.filter.toLowerCase();
    return allMembers.filter((m) => {
      const name = (m.display_name || m.name || m.email || '').toLowerCase();
      return name.includes(q);
    });
  }, [mentionPopup, allMembers]);

  const handleVotePoll = async (pollId, optionIndex) => {
    try {
      await groupPlannerApi.voteOnPoll(groupId, pollId, optionIndex);
      queryClient.invalidateQueries({ queryKey: gpKeys.polls(groupId) });
    } catch {
      showToast('Failed to vote', 'error');
    }
  };

  const handleDeletePoll = async (pollId) => {
    try {
      await groupPlannerApi.deletePoll(groupId, pollId);
      queryClient.invalidateQueries({ queryKey: gpKeys.polls(groupId) });
      queryClient.invalidateQueries({ queryKey: gpKeys.activities(groupId) });
      showToast('Poll deleted');
    } catch {
      showToast('Failed to delete poll', 'error');
    }
  };

  const handleCreatePoll = async () => {
    const question = pollQuestion.trim();
    const opts = pollOptions.map((o) => o.trim()).filter(Boolean);
    if (!question || opts.length < 2) {
      showToast('Need a question and at least 2 options', 'error');
      return;
    }
    try {
      await groupPlannerApi.createPoll(groupId, { name: question, options: opts, is_multiple_choice: pollMultiChoice });
      queryClient.invalidateQueries({ queryKey: gpKeys.polls(groupId) });
      queryClient.invalidateQueries({ queryKey: gpKeys.activities(groupId) });
      setShowPollForm(false);
      setPollQuestion('');
      setPollOptions(['', '']);
      setPollMultiChoice(false);
      showToast('Poll created');
    } catch {
      showToast('Failed to create poll', 'error');
    }
  };

  return (
    <div className="gp-chat-container">
      <div className="gp-chat-header">
        <span className="gp-chat-header-label">Dialogue Feed</span>
        {unreadScoutCount > 0 && (
          <span className="gp-chat-unread-badge" onClick={() => {
            chatFeedRef.current?.scrollTo({ top: chatFeedRef.current.scrollHeight, behavior: 'smooth' });
            setUnreadScoutCount(0);
          }}>
            {unreadScoutCount} new
          </span>
        )}
        <div className="gp-engines-active"><span className="gp-engines-dot" /></div>
      </div>

      <div className="gp-chat-feed" ref={chatFeedRef} onScroll={handleFeedScroll}>
        {isFetchingNextPage && (
          <div className="gp-chat-loading-older"><Loader2 size={14} className="gp-spin" /> Loading older messages...</div>
        )}

        {messages.length === 0 && polls.length === 0 && (
          <div className="gp-empty-agenda">Start a conversation with your group.</div>
        )}

        {/* Polls */}
        {polls.map((poll) => {
          const totalVotes = poll.voted_by ? poll.voted_by.length : 0;
          return (
            <div key={'poll-' + poll.id} className="gp-poll-chat-wrap">
              <div className="gp-poll-avatar-badge">POLL</div>
              <div className="gp-poll-card-v2">
                <div className="gp-poll-card-v2-top">
                  <span className="gp-poll-card-v2-question">{poll.name}</span>
                  <div className="gp-poll-card-v2-meta">
                    <span className="gp-poll-card-v2-votes">{totalVotes} vote{totalVotes !== 1 ? 's' : ''}</span>
                    {poll.is_multiple_choice && <span className="gp-poll-card-v2-multi">Multi</span>}
                  </div>
                </div>
                <div className="gp-poll-card-v2-options">
                  {(poll.options || []).map((opt, oi) => {
                    const count = poll.votes?.[opt] || 0;
                    const pct = totalVotes > 0 ? Math.round((count / totalVotes) * 100) : 0;
                    const voters = poll.votes_detail?.[opt] || [];
                    const myVote = voters.includes(userId) || voters.includes(uidNum);
                    return (
                      <div key={oi} className={'gp-poll-opt-v2' + (myVote ? ' voted' : '')} onClick={() => handleVotePoll(poll.id, oi)}>
                        <div className="gp-poll-opt-v2-bar" style={{ width: pct + '%' }} />
                        <div className="gp-poll-opt-v2-content">
                          <span className="gp-poll-opt-v2-text">
                            {myVote && <Check size={12} style={{ marginRight: 4 }} />}
                            {opt}
                          </span>
                          <span className="gp-poll-opt-v2-pct">{count > 0 ? pct + '%' : ''}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div className="gp-poll-card-v2-footer">
                  <div className="gp-poll-card-v2-author">
                    {poll.created_by_name && <span>by {poll.created_by_name}</span>}
                    <span className="gp-poll-card-v2-time">{formatRelativeTime(poll.created_at)}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <button className="gp-poll-view-btn" onClick={() => setExpandedVoters(expandedVoters === poll.id ? null : poll.id)}>View Voters</button>
                    <button className="gp-itinerary-edit-btn" onClick={() => handleDeletePoll(poll.id)} title="Delete poll"><Trash2 size={11} /></button>
                  </div>
                </div>
                {expandedVoters === poll.id && (
                  <div className="gp-poll-voters-panel">
                    {(poll.options || []).map((opt, oi) => {
                      const voters = poll.votes_detail?.[opt] || [];
                      if (voters.length === 0) return null;
                      const voterNames = voters.map((vid) => {
                        const m = members.find((mb) => String(mb.id) === String(vid) || String(mb.user_id) === String(vid));
                        return m ? (m.display_name || m.name || m.email) : null;
                      }).filter(Boolean);
                      return (
                        <div key={oi} className="gp-poll-voters-row">
                          <span className="gp-poll-voters-opt-label">{opt}</span>
                          <div className="gp-poll-voters-names">
                            {voterNames.map((name, ni) => <span key={ni} className="gp-poll-voter-chip-v2">{name}</span>)}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {/* Scout floating pill — appears when new Scout reply is off-screen (user scrolled up) */}
        {unreadScoutCount > 0 && (
          <button
            className="gp-scout-reply-pill"
            onClick={() => {
              chatFeedRef.current?.scrollTo({ top: chatFeedRef.current.scrollHeight, behavior: 'smooth' });
              setUnreadScoutCount(0);
            }}
          >
            ↓ Scout replied
          </button>
        )}

        {/* Chat Messages (reversed: API returns newest-first, display oldest at top) */}
        {[...messages].reverse().map((msg) => {
          if (msg.is_deleted) return null;
          const isMine = String(msg.sender_id) === uidStr;
          const isAi = msg.sender_type === 'ai' || msg.sender_type === 'system';
          const isNewGlow = isAi && glowMsgIds.has(msg.id);
          const agentName = msg.metadata_json?.agent;
          const glowClass = isNewGlow ? (agentName === 'crew' ? ' gp-chat-crew-new' : ' gp-chat-scout-new') : '';

          // Consent prompt renders as standalone card, not inside a chat bubble
          if (msg.metadata_json?.needs_consent) {
            return (
              <div key={msg.id} className="gp-chat-message gp-chat-ai">
                <ScoutConsentCard
                  groupId={groupId}
                  originalQuery={msg.metadata_json?.original_query}
                  onRetry={(query) => sendMutation.mutate({ content: query, type: 'text' })}
                  onDismiss={() => {}}
                />
              </div>
            );
          }

          // --- Crew card types (private cards filtered by target_user_id) ---
          if (msg.type === 'crew_question') {
            if (msg.metadata_json?.target_user_id && String(msg.metadata_json.target_user_id) !== String(userId)) return null;
            return (
              <div key={msg.id} className={'gp-chat-message gp-chat-ai' + glowClass}>
                <CrewQuestionCard
                  question={msg.metadata_json?.question || msg.content}
                  options={msg.metadata_json?.options || []}
                  allFields={msg.metadata_json?.all_fields}
                  onAnswer={handleCrewAnswer}
                  createdAt={msg.created_at}
                />
              </div>
            );
          }

          if (msg.type === 'crew_confirm') {
            if (msg.metadata_json?.target_user_id && String(msg.metadata_json.target_user_id) !== String(userId)) return null;
            const pendingKey = msg.metadata_json?.pending_key;
            return (
              <div key={msg.id} className={'gp-chat-message gp-chat-ai' + glowClass}>
                <CrewConfirmCard
                  entityName={msg.metadata_json?.entity_name || ''}
                  entityType={msg.metadata_json?.entity_type || 'item'}
                  onConfirm={() => handleCrewConfirm(groupId, 'confirm', pendingKey)}
                  onCancel={() => handleCrewConfirm(groupId, 'cancel', pendingKey)}
                  createdAt={msg.created_at}
                />
              </div>
            );
          }

          if (msg.type === 'crew_place') {
            return (
              <div key={msg.id} className={'gp-chat-message gp-chat-ai' + glowClass}>
                <CrewPlaceCard
                  placeName={msg.metadata_json?.place_name || msg.content}
                  address={msg.metadata_json?.address}
                  source={msg.metadata_json?.source || 'library'}
                  addedBy={msg.metadata_json?.added_by}
                  createdAt={msg.created_at}
                />
              </div>
            );
          }

          if (msg.type === 'crew_poll_created') {
            const pollMeta = msg.metadata_json?.poll || {};
            const pollName = pollMeta.name || msg.metadata_json?.question || msg.content;
            const pollOpts = pollMeta.options || [];
            const pollId = pollMeta.id || msg.metadata_json?.poll_id;
            return (
              <div key={msg.id} className={'gp-chat-message gp-chat-ai' + glowClass}>
                <div className="gp-crew-poll-created-card">
                  <div className="gp-crew-card-label">Crew</div>
                  <div className="gp-poll-card-v2">
                    <div className="gp-poll-card-v2-top">
                      <span className="gp-poll-card-v2-question">{pollName}</span>
                      <div className="gp-poll-card-v2-meta">
                        <span className="gp-poll-card-v2-votes">0 votes</span>
                      </div>
                    </div>
                    <div className="gp-poll-card-v2-options">
                      {pollOpts.map((opt, oi) => (
                        <div key={oi} className="gp-poll-opt-v2" onClick={() => pollId && handleVotePoll(pollId, oi)}>
                          <div className="gp-poll-opt-v2-bar" style={{ width: '0%' }} />
                          <div className="gp-poll-opt-v2-content">
                            <span className="gp-poll-opt-v2-text">{opt}</span>
                            <span className="gp-poll-opt-v2-pct"></span>
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className="gp-poll-card-v2-footer">
                      <span className="gp-poll-card-v2-time">{formatRelativeTime(msg.created_at)}</span>
                    </div>
                  </div>
                </div>
              </div>
            );
          }

          if (msg.type === 'crew_error') {
            if (msg.metadata_json?.target_user_id && String(msg.metadata_json.target_user_id) !== String(userId)) return null;
          }

          return (
            <div
              key={msg.id}
              className={'gp-chat-message' + (isMine ? ' gp-chat-mine' : isAi ? ' gp-chat-ai' : '') + glowClass}
              onMouseEnter={isNewGlow ? () => { emitRead(msg.id); } : undefined}
            >
              <div className="gp-chat-bubble">
                {!isMine && msg.sender_name && (
                  <span className="gp-chat-sender-name">{msg.sender_name}</span>
                )}
                {isAi && <span className="gp-chat-bot-label">{agentName === 'scout' ? 'Scout' : agentName === 'crew' ? 'Crew' : (msg.sender_name || 'AI')}</span>}
                {isAi ? renderScoutMessage(msg.content) : (
                  <p className="gp-chat-text">
                    {msg.content.startsWith('__crew_fields__:') ? 'Filled the form for @crew' : msg.content}
                  </p>
                )}
                <span className="gp-chat-time">{formatRelativeTime(msg.created_at)}</span>
                {isMine && !msg._optimistic && (
                  <button className="gp-chat-delete-btn" onClick={() => deleteMutation.mutate(msg.id)} title="Delete message">
                    <Trash2 size={10} />
                  </button>
                )}
                {msg._optimistic && <span className="gp-chat-sending">Sending...</span>}
              </div>
            </div>
          );
        })}

        {/* Typing indicator */}
        {typingUsers.length > 0 && (
          <>
            {typingUsers.some((u) => u.is_ai) && (
              <div className="gp-chat-message gp-chat-ai">
                <div className="gp-chat-bubble gp-scout-thinking">
                  <span className="gp-chat-bot-label">Scout</span>
                  <div className="gp-scout-thinking-dots">
                    <span></span><span></span><span></span>
                  </div>
                </div>
              </div>
            )}
            {typingUsers.some((u) => !u.is_ai) && (
              <div className="gp-chat-typing">
                {typingUsers.filter((u) => !u.is_ai).map((u) => u.email).join(', ')} typing...
              </div>
            )}
          </>
        )}
      </div>

      {/* Chat Input */}
      <div className="gp-chat-input-area">
        {mentionPopup.open && mentionResults.length > 0 && (
          <div className="gp-mention-popup">
            {mentionResults.map((m) => (
              <div key={m.id || m.user_id} className="gp-mention-item" onClick={() => handleSelectMention(m)}>
                {m.type === 'ai' ? (
                  <div className="gp-mention-avatar gp-mention-avatar-ai">AI</div>
                ) : m.photo_url || m.avatar ? (
                  <img src={m.photo_url || m.avatar} alt={m.display_name || m.name} className="gp-mention-avatar-img" />
                ) : (
                  <div className="gp-mention-avatar">{getInitials(m.display_name || m.name || m.email || 'U')}</div>
                )}
                <span className="gp-mention-name">{m.display_name || m.name || m.email}</span>
                {m.type === 'ai' && <span className="gp-mention-tag">Bot</span>}
              </div>
            ))}
          </div>
        )}
        <div className="gp-chat-input-row">
          <button className={'gp-chat-poll-btn' + (showPollForm ? ' active' : '')} onClick={() => setShowPollForm((v) => !v)} title="Create poll">
            <BarChart3 size={18} />
          </button>
          <div className="gp-chat-input-wrapper">
            <input
              ref={chatInputRef}
              type="text"
              className="gp-chat-input"
              placeholder="Talk with @scout or @crew..."
              value={chatMessage}
              onChange={handleChatInputChange}
              onKeyDown={(e) => {
                if (mentionPopup.open && e.key === 'Escape') { e.preventDefault(); dismissMention(); return; }
                if (e.key === 'Enter') handleSendChat();
              }}
            />
            <button className="gp-chat-send-btn" onClick={handleSendChat}><Send size={16} /></button>
          </div>
        </div>
      </div>

      {/* Poll Creation Modal */}
      {showPollForm && (
        <div className="gp-modal-overlay" onClick={() => { setShowPollForm(false); setPollQuestion(''); setPollOptions(['', '']); setPollMultiChoice(false); }}>
          <div className="gp-poll-modal" onClick={(e) => e.stopPropagation()}>
            <div className="gp-poll-create-header">
              <span className="gp-poll-create-title">Create a Poll</span>
              <button className="gp-poll-cancel-btn" onClick={() => { setShowPollForm(false); setPollQuestion(''); setPollOptions(['', '']); setPollMultiChoice(false); }}><X size={14} /></button>
            </div>
            <input className="gp-poll-create-input" placeholder="What's your question?" value={pollQuestion} onChange={(e) => setPollQuestion(e.target.value)} autoFocus />
            <div className="gp-poll-create-options">
              {pollOptions.map((opt, i) => (
                <div key={i} className="gp-poll-create-opt-row">
                  <input className="gp-poll-create-input gp-poll-create-opt-input" placeholder={`Option ${i + 1}`} value={opt} onChange={(e) => { const next = [...pollOptions]; next[i] = e.target.value; setPollOptions(next); }} />
                  {pollOptions.length > 2 && (
                    <button className="gp-poll-create-opt-remove" onClick={() => setPollOptions(pollOptions.filter((_, j) => j !== i))}><X size={12} /></button>
                  )}
                </div>
              ))}
            </div>
            <div className="gp-poll-create-actions">
              <div className="gp-poll-create-actions-left">
                {pollOptions.length < 10 && <button className="gp-poll-create-add" onClick={() => setPollOptions([...pollOptions, ''])}>+ Add Option</button>}
                <label className="gp-poll-create-multi">
                  <input type="checkbox" checked={pollMultiChoice} onChange={(e) => setPollMultiChoice(e.target.checked)} /> Multi-select
                </label>
              </div>
              <button className="gp-poll-create-submit" onClick={handleCreatePoll}>Create Poll</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

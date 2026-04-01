import { useState, useRef, useCallback } from 'react';

/**
 * Client-side chat state hook.
 * Manages chatFeed, chatMessage, mention popup, and bot responses.
 * Will be replaced by useChatQuery + useChatSocket in Phase 4.
 */
export default function useChatState(destination) {
  const [chatFeed, setChatFeed] = useState([]);
  const [chatMessage, setChatMessage] = useState('');
  const [mentionPopup, setMentionPopup] = useState({ open: false, filter: '', startIndex: -1 });

  const chatFeedRef = useRef(null);
  const chatInputRef = useRef(null);

  const handleChatInputChange = useCallback((e) => {
    const val = e.target.value;
    setChatMessage(val);
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
  }, []);

  const handleSelectMention = useCallback((member) => {
    const rawName = member.display_name || member.name || member.email;
    const name = rawName.startsWith('@') ? rawName.slice(1) : rawName;
    const before = chatMessage.slice(0, mentionPopup.startIndex);
    const after = chatMessage.slice(mentionPopup.startIndex + 1 + mentionPopup.filter.length);
    setChatMessage(before + '@' + name + ' ' + after);
    setMentionPopup({ open: false, filter: '', startIndex: -1 });
    chatInputRef.current?.focus();
  }, [chatMessage, mentionPopup]);

  const handleSendChat = useCallback(() => {
    const text = chatMessage.trim();
    if (!text) return;
    setChatFeed((prev) => [
      ...prev,
      { from: 'me', text, time: new Date().toLocaleTimeString() },
    ]);
    setChatMessage('');
    setMentionPopup({ open: false, filter: '', startIndex: -1 });

    if (text.toLowerCase().includes('@guide')) {
      setTimeout(() => {
        setChatFeed((prev) => [
          ...prev,
          { from: 'ai', bot: '@guide', text: 'I\'m your travel guide. Ask me about ' + (destination || 'your destination') + ' -- sights, food, local tips, anything.', time: new Date().toLocaleTimeString() },
        ]);
        chatFeedRef.current?.scrollTo(0, chatFeedRef.current.scrollHeight);
      }, 600);
    }

    if (text.toLowerCase().includes('@plan')) {
      setTimeout(() => {
        setChatFeed((prev) => [
          ...prev,
          { from: 'ai', bot: '@plan', text: 'I\'m your trip planner. I can help organize your itinerary, suggest schedules, and optimize your route.', time: new Date().toLocaleTimeString() },
        ]);
        chatFeedRef.current?.scrollTo(0, chatFeedRef.current.scrollHeight);
      }, 600);
    }

    setTimeout(() => chatFeedRef.current?.scrollTo(0, chatFeedRef.current.scrollHeight), 50);
  }, [chatMessage, destination]);

  const dismissMention = useCallback(() => {
    setMentionPopup({ open: false, filter: '', startIndex: -1 });
  }, []);

  return {
    chatFeed,
    chatMessage,
    mentionPopup,
    chatFeedRef,
    chatInputRef,
    handleChatInputChange,
    handleSelectMention,
    handleSendChat,
    dismissMention,
  };
}

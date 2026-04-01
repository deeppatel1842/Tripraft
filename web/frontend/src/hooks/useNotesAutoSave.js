import { useState, useCallback } from 'react';

export default function useNotesAutoSave(groupId) {
  const storageKey = `notes-draft:${groupId}`;

  const [draft, setDraft] = useState(() => {
    try {
      return localStorage.getItem(storageKey) || '';
    } catch {
      return '';
    }
  });

  const updateDraft = useCallback((text) => {
    setDraft(text);
    try {
      localStorage.setItem(storageKey, text);
    } catch { /* Storage full or unavailable */ }
  }, [storageKey]);

  const clearDraft = useCallback(() => {
    setDraft('');
    try {
      localStorage.removeItem(storageKey);
    } catch { /* Ignore */ }
  }, [storageKey]);

  const hasDraft = draft.length > 0;

  return { draft, updateDraft, clearDraft, hasDraft };
}

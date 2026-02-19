import React, { useRef, useEffect, useState, useCallback } from 'react';
import { FileText, Bold, Italic, List, Underline, Cloud } from 'lucide-react';
import '../css/NotesSection.css';

export default function NotesSection({
  initialContent = '',
  onContentChange,
  lastSaved = 'Auto-saving...',
}) {
  const editorRef = useRef(null);
  const [saveStatus, setSaveStatus] = useState('Saved');
  const saveTimeoutRef = useRef(null);
  const contentInitialized = useRef(false);

  // Initialize editor content once
  useEffect(() => {
    if (editorRef.current && !contentInitialized.current) {
      if (initialContent && initialContent.trim()) {
        editorRef.current.innerHTML = initialContent;
      } else {
        editorRef.current.innerHTML = getDefaultContent();
      }
      contentInitialized.current = true;
    }
  }, [initialContent]);

  // Update save status from prop
  useEffect(() => {
    if (lastSaved === 'Saved' || lastSaved === 'Auto-saving...') {
      setSaveStatus(lastSaved === 'Auto-saving...' ? 'Saved' : lastSaved);
    }
  }, [lastSaved]);

  const getDefaultContent = () => {
    return `<h2>Trip Notes</h2>
<p>Start planning your trip here. This document auto-saves as you type.</p>
<ul>
<li>Add your travel ideas</li>
<li>Share notes with your group</li>
<li>Use formatting tools above</li>
</ul>`;
  };

  const handleFormat = useCallback((command, value = null) => {
    document.execCommand(command, false, value);
    editorRef.current?.focus();
  }, []);

  const handleInput = useCallback(() => {
    if (!editorRef.current) return;
    
    setSaveStatus('Saving...');
    
    // Clear previous timeout
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    
    // Debounce save
    saveTimeoutRef.current = setTimeout(() => {
      if (onContentChange && editorRef.current) {
        onContentChange(editorRef.current.innerHTML);
      }
      setSaveStatus('Saved');
    }, 1000);
  }, [onContentChange]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, []);

  return (
    <div className="ns-container">
      <div className="ns-toolbar">
        <div className="ns-toolbar-left">
          <span className="ns-toolbar-title">
            <FileText className="ns-toolbar-icon" />
            Trip Notes
          </span>
          <div className="ns-toolbar-divider" />
          <button 
            className="ns-format-btn" 
            onClick={() => handleFormat('bold')}
            title="Bold (Ctrl+B)"
            type="button"
          >
            <Bold className="ns-format-icon" />
          </button>
          <button 
            className="ns-format-btn" 
            onClick={() => handleFormat('italic')}
            title="Italic (Ctrl+I)"
            type="button"
          >
            <Italic className="ns-format-icon" />
          </button>
          <button 
            className="ns-format-btn" 
            onClick={() => handleFormat('underline')}
            title="Underline (Ctrl+U)"
            type="button"
          >
            <Underline className="ns-format-icon" />
          </button>
          <button 
            className="ns-format-btn" 
            onClick={() => handleFormat('insertUnorderedList')}
            title="Bullet List"
            type="button"
          >
            <List className="ns-format-icon" />
          </button>
        </div>
        <span className={`ns-autosave ${saveStatus === 'Saved' ? 'ns-autosave-saved' : ''}`}>
          {saveStatus === 'Saved' ? (
            <>
              <Cloud size={12} className="ns-save-icon" />
              Saved
            </>
          ) : (
            <>
              <span className="ns-saving-dot" />
              Saving...
            </>
          )}
        </span>
      </div>

      <div
        ref={editorRef}
        className="ns-editor"
        contentEditable
        suppressContentEditableWarning
        onInput={handleInput}
        spellCheck="true"
        data-placeholder="Start typing your trip notes..."
      />
    </div>
  );
}

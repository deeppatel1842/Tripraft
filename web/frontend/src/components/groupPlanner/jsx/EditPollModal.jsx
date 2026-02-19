import React, { useState, useEffect } from 'react';
import { X, Save, Plus, Trash2 } from 'lucide-react';
import '../css/EditPollModal.css';

export default function EditPollModal({
  isOpen,
  onClose,
  onSave,
  poll,
  isLoading = false,
}) {
  const [question, setQuestion] = useState('');
  const [options, setOptions] = useState(['', '']);

  useEffect(() => {
    if (poll) {
      setQuestion(poll.question || poll.name || '');
      const pollOptions = poll.options?.map(opt => 
        typeof opt === 'string' ? opt : opt.label
      ) || ['', ''];
      setOptions(pollOptions.length >= 2 ? pollOptions : ['', '']);
    } else {
      setQuestion('');
      setOptions(['', '']);
    }
  }, [poll]);

  const handleAddOption = () => {
    if (options.length < 6) {
      setOptions([...options, '']);
    }
  };

  const handleRemoveOption = (index) => {
    if (options.length > 2) {
      setOptions(options.filter((_, i) => i !== index));
    }
  };

  const handleOptionChange = (index, value) => {
    const newOptions = [...options];
    newOptions[index] = value;
    setOptions(newOptions);
  };

  const handleSave = () => {
    if (!question.trim()) return;
    const validOptions = options.filter(opt => opt.trim());
    if (validOptions.length < 2) return;
    
    onSave({
      id: poll?.id,
      name: question.trim(),
      options: validOptions,
    });
  };

  const isValid = question.trim() && options.filter(opt => opt.trim()).length >= 2;

  if (!isOpen) return null;

  return (
    <div className="epm-overlay" onClick={onClose}>
      <div className="epm-modal" onClick={(e) => e.stopPropagation()}>
        <div className="epm-header">
          <h2 className="epm-title">
            {poll ? 'Edit Poll' : 'Create Poll'}
          </h2>
          <button className="epm-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="epm-body">
          <div className="epm-field">
            <label className="epm-label">Poll Question</label>
            <input
              type="text"
              className="epm-input"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="What should we do for dinner?"
              autoFocus
            />
          </div>

          <div className="epm-field">
            <label className="epm-label">Options</label>
            <div className="epm-options">
              {options.map((option, index) => (
                <div key={index} className="epm-option-row">
                  <input
                    type="text"
                    className="epm-input epm-option-input"
                    value={option}
                    onChange={(e) => handleOptionChange(index, e.target.value)}
                    placeholder={`Option ${index + 1}`}
                  />
                  {options.length > 2 && (
                    <button
                      className="epm-remove-btn"
                      onClick={() => handleRemoveOption(index)}
                      type="button"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              ))}
            </div>
            
            {options.length < 6 && (
              <button
                className="epm-add-option-btn"
                onClick={handleAddOption}
                type="button"
              >
                <Plus size={14} />
                Add Option
              </button>
            )}
          </div>
        </div>

        <div className="epm-footer">
          <button className="epm-btn epm-btn-cancel" onClick={onClose}>
            Cancel
          </button>
          <button
            className="epm-btn epm-btn-save"
            onClick={handleSave}
            disabled={isLoading || !isValid}
          >
            <Save size={14} />
            {isLoading ? 'Saving...' : 'Save Poll'}
          </button>
        </div>
      </div>
    </div>
  );
}

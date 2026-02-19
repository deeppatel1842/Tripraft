/**
 * CreatePollModal - Modal for creating a new poll
 * Features question input, multiple options with add/remove
 */
import React, { useState, useEffect } from 'react';
import { X, Plus, Trash2, BarChart2 } from 'lucide-react';
import '../css/CreatePollModal.css';

export default function CreatePollModal({
  isOpen,
  onClose,
  onCreatePoll,
  isLoading = false,
}) {
  const [question, setQuestion] = useState('');
  const [options, setOptions] = useState(['', '']);
  const [error, setError] = useState('');

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setQuestion('');
      setOptions(['', '']);
      setError('');
    }
  }, [isOpen]);

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

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');
    
    // Validate
    if (!question.trim()) {
      setError('Please enter a question');
      return;
    }
    
    const validOptions = options.map(o => o.trim()).filter(o => o);
    if (validOptions.length < 2) {
      setError('Please enter at least 2 options');
      return;
    }
    
    onCreatePoll({
      name: question.trim(),
      options: validOptions,
    });
  };

  if (!isOpen) return null;

  return (
    <div className="cpm-overlay" onClick={onClose}>
      <div className="cpm-modal" onClick={(e) => e.stopPropagation()}>
        <div className="cpm-header">
          <div className="cpm-header-title">
            <BarChart2 size={20} className="cpm-header-icon" />
            <h2 className="cpm-title">Create Poll</h2>
          </div>
          <button className="cpm-close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="cpm-form">
          {/* Question */}
          <div className="cpm-field">
            <label className="cpm-label">Question</label>
            <input
              type="text"
              className="cpm-input"
              placeholder="e.g., Where should we eat dinner?"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              autoFocus
            />
          </div>

          {/* Options */}
          <div className="cpm-field">
            <label className="cpm-label">Options</label>
            <div className="cpm-options-list">
              {options.map((option, index) => (
                <div key={index} className="cpm-option-row">
                  <span className="cpm-option-number">{index + 1}</span>
                  <input
                    type="text"
                    className="cpm-input cpm-option-input"
                    placeholder={`Option ${index + 1}`}
                    value={option}
                    onChange={(e) => handleOptionChange(index, e.target.value)}
                  />
                  {options.length > 2 && (
                    <button
                      type="button"
                      className="cpm-remove-option-btn"
                      onClick={() => handleRemoveOption(index)}
                      title="Remove option"
                    >
                      <Trash2 size={16} />
                    </button>
                  )}
                </div>
              ))}
            </div>
            
            {options.length < 6 && (
              <button
                type="button"
                className="cpm-add-option-btn"
                onClick={handleAddOption}
              >
                <Plus size={16} />
                Add Option
              </button>
            )}
          </div>

          {/* Error message */}
          {error && (
            <div className="cpm-error">{error}</div>
          )}

          {/* Actions */}
          <div className="cpm-actions">
            <button type="button" className="cpm-cancel-btn" onClick={onClose}>
              Cancel
            </button>
            <button 
              type="submit" 
              className="cpm-submit-btn"
              disabled={isLoading}
            >
              {isLoading ? 'Creating...' : 'Create Poll'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

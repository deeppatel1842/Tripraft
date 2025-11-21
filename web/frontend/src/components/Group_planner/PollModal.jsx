import React, { useState } from 'react';

export default function PollModal({ isOpen, onClose, onSubmit }) {
  const [pollName, setPollName] = useState('');
  const [options, setOptions] = useState(['', '']);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    const filledOptions = options.filter((o) => o.trim());
    if (!pollName.trim() || filledOptions.length < 2) {
      console.error('Poll must have a name and at least 2 options');
      return;
    }
    setLoading(true);
    try {
      await onSubmit({ name: pollName, options: filledOptions });
      setPollName('');
      setOptions(['', '']);
      onClose();
    } catch (error) {
      console.error('Error creating poll:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleOptionChange = (index, value) => {
    const newOptions = [...options];
    newOptions[index] = value;
    setOptions(newOptions);
  };

  const addOption = () => {
    setOptions([...options, '']);
  };

  const removeOption = (index) => {
    if (options.length > 2) {
      setOptions(options.filter((_, i) => i !== index));
    }
  };

  if (!isOpen) return null;

  return (
    <div className={`demo-modal ${isOpen ? 'show' : ''}`} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="demo-dialog">
        <header>
          <strong>Create New Poll</strong>
          <button className="demo-close" onClick={onClose}>×</button>
        </header>
        <div className="demo-body">
          <div className="demo-field">
            <input
              type="text"
              className="demo-input"
              placeholder="Poll question..."
              value={pollName}
              onChange={(e) => setPollName(e.target.value)}
            />
          </div>
          <div id="pollOptions" style={{ marginTop: '12px', marginBottom: '12px' }}>
            {options.map((option, index) => (
              <div key={index} className="demo-field" style={{ marginTop: '8px' }}>
                <input
                  type="text"
                  className="demo-input"
                  placeholder={`Option ${index + 1}`}
                  value={option}
                  onChange={(e) => handleOptionChange(index, e.target.value)}
                />
                {options.length > 2 && (
                  <button
                    className="demo-danger"
                    onClick={() => removeOption(index)}
                  >
                    ✖
                  </button>
                )}
              </div>
            ))}
          </div>
          <button className="demo-ghost" onClick={addOption} style={{ fontSize: '12px', width: '100%' }}>
            ＋ Add Option
          </button>
        </div>
        <div className="demo-foot">
          <button className="demo-ghost" onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button className="demo-primary" onClick={handleSubmit} disabled={loading}>
            {loading ? 'Creating...' : 'Create Poll'}
          </button>
        </div>
      </div>
    </div>
  );
}

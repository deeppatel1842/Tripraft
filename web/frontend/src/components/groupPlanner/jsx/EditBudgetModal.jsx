/**
 * EditBudgetModal
 * Allows the group owner (or any member) to update the estimated budget.
 *
 * Props:
 *   isOpen        — boolean controlling visibility
 *   onClose       — callback to close the modal
 *   onSave        — (budget: number, currency: string) => Promise<void>
 *   currentBudget — current estimated budget (number)
 *   currentCurrency — current currency code (string, default 'USD')
 *   isSaving      — boolean, true while the save request is in-flight
 */

import React, { useState, useEffect, useRef } from 'react';
import { X, DollarSign } from 'lucide-react';
import '../css/EditBudgetModal.css';

const CURRENCIES = [
  { code: 'USD', symbol: '$' },
  { code: 'EUR', symbol: '\u20AC' },
  { code: 'GBP', symbol: '\u00A3' },
  { code: 'JPY', symbol: '\u00A5' },
  { code: 'INR', symbol: '\u20B9' },
  { code: 'CAD', symbol: 'C$' },
  { code: 'AUD', symbol: 'A$' },
];

export default function EditBudgetModal({
  isOpen,
  onClose,
  onSave,
  currentBudget = 0,
  currentCurrency = 'USD',
  isSaving = false,
}) {
  const [budget, setBudget] = useState('');
  const [currency, setCurrency] = useState(currentCurrency);
  const [error, setError] = useState('');
  const inputRef = useRef(null);

  // Sync local state when modal opens
  useEffect(() => {
    if (isOpen) {
      setBudget(currentBudget > 0 ? String(currentBudget) : '');
      setCurrency(currentCurrency);
      setError('');
      // Auto-focus the input after a tick
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen, currentBudget, currentCurrency]);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();

    const parsed = parseFloat(budget);
    if (Number.isNaN(parsed) || parsed < 0) {
      setError('Enter a valid budget amount.');
      return;
    }

    setError('');
    try {
      await onSave(parsed, currency);
      onClose();
    } catch {
      setError('Failed to update budget. Please try again.');
    }
  };

  const currencySymbol =
    CURRENCIES.find((c) => c.code === currency)?.symbol || '$';

  return (
    <div className="ebm-overlay" onClick={onClose}>
      <div className="ebm-modal" onClick={(e) => e.stopPropagation()}>
        <div className="ebm-header">
          <h3 className="ebm-title">
            <DollarSign size={18} />
            Edit Budget
          </h3>
          <button className="ebm-close" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>

        <form className="ebm-form" onSubmit={handleSubmit}>
          <div className="ebm-field">
            <label className="ebm-label" htmlFor="ebm-budget">
              Estimated Budget
            </label>
            <div className="ebm-input-wrap">
              <span className="ebm-currency">{currencySymbol}</span>
              <input
                ref={inputRef}
                id="ebm-budget"
                className="ebm-input"
                type="number"
                min="0"
                step="0.01"
                placeholder="0.00"
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                disabled={isSaving}
              />
            </div>
          </div>

          <div className="ebm-field">
            <label className="ebm-label" htmlFor="ebm-currency">
              Currency
            </label>
            <select
              id="ebm-currency"
              className="ebm-select"
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              disabled={isSaving}
            >
              {CURRENCIES.map((c) => (
                <option key={c.code} value={c.code}>
                  {c.code} ({c.symbol})
                </option>
              ))}
            </select>
          </div>

          {error && <p className="ebm-error">{error}</p>}

          <div className="ebm-actions">
            <button
              type="button"
              className="ebm-btn ebm-btn-cancel"
              onClick={onClose}
              disabled={isSaving}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="ebm-btn ebm-btn-save"
              disabled={isSaving}
            >
              {isSaving ? 'Saving...' : 'Save Budget'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

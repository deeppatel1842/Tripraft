// Purpose: Collects debt-bounded settlement payments and displays currency-aware history and save errors.
import React, { useState, useEffect } from 'react';
import { formatMoney, settlementCap } from '../../../utils/money';
import '../css/SettlementModal.css';

const SettlementModal = ({ isOpen, onClose, settlement, groupId, members, balances = [], currency = 'USD', onSuccess }) => {
  const [fromUser, setFromUser] = useState(settlement?.from || '');
  const [toUser, setToUser] = useState(settlement?.to || '');
  const [amount, setAmount] = useState(settlement?.amount || 0);
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [suggestedAmount, setSuggestedAmount] = useState(0);

  // Reset form when settlement changes
  useEffect(() => {
    if (isOpen) {
      setFromUser(settlement?.from || '');
      setToUser(settlement?.to || '');
      const suggAmount = settlement?.amount || 0;
      setAmount(suggAmount);
      setSuggestedAmount(suggAmount);
      setNotes('');
      setError('');
    }
  }, [isOpen, settlement]);

  const maxAmount = settlementCap(balances, fromUser, toUser);
  const isManualMode = !settlement?.from || !settlement?.to;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (loading) return;

    try {
      const finalFromUser = isManualMode ? fromUser : settlement.from;
      const finalToUser = isManualMode ? toUser : settlement.to;

      if (!finalFromUser || !finalToUser) {
        setError('Please select both payer and recipient');
        return;
      }

      if (finalFromUser === finalToUser) {
        setError('Payer and recipient cannot be the same person');
        return;
      }

      if (!Number.isFinite(Number(amount)) || Number(amount) <= 0 || Number(amount) > maxAmount) {
        setError('Enter an amount up to the current outstanding debt: ' + formatMoney(maxAmount, currency));
        return;
      }

      const settlementData = {
        from_user: finalFromUser,
        to_user: finalToUser,
        amount: parseFloat(amount),
        group_id: groupId,
        notes: notes.trim() || null
      };

      setLoading(true);
      if (!onSuccess) throw new Error('Settlement saving is unavailable.');
      await onSuccess(settlementData);
      onClose();


    } catch (err) {
      setError(err.message || 'Failed to record settlement. Please try again.');
    } finally { setLoading(false); }
  };

  if (!isOpen) return null;

  return (
    <div 
      className="settlement-modal-overlay"
      onClick={onClose}
    >
      <div 
        className="settlement-modal-content" 
        onClick={(e) => e.stopPropagation()}
      >
          <div className="modal-header">
            <h2>Record Settlement</h2>
            <button className="close-button" onClick={onClose}>&times;</button>
          </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && (
              <div className="alert alert-error" style={{ marginBottom: '1rem' }}>
                {error}
              </div>
            )}

            {!isManualMode ? (
              <div style={{ 
                background: '#f8f9fa', 
                padding: '1rem', 
                borderRadius: '8px',
                marginBottom: '1.5rem'
              }}>
                <div style={{ textAlign: 'center' }}>
                  <p style={{ marginBottom: '0.5rem', color: '#666' }}>
                    <span style={{ fontWeight: '600', color: '#e74c3c' }}>
                      {settlement?.fromName}
                    </span>
                    {' '}pays{' '}
                    <span style={{ fontWeight: '600', color: '#27ae60' }}>
                      {settlement?.toName}
                    </span>
                  </p>
                </div>
              </div>
            ) : (
              <>
                <div className="form-group">
                  <label htmlFor="fromUser">Who is paying? *</label>
                  <select
                    id="fromUser"
                    value={fromUser}
                    onChange={(e) => setFromUser(e.target.value)}
                    required
                  >
                    <option value="">Select payer...</option>
                    {members?.map((member) => {
                      const userId = member.user_id || member.id;
                      const displayName = member.user?.display_name || 
                                        member.user?.username || 
                                        member.display_name ||
                                        member.username ||
                                        'Unknown User';
                      return (
                        <option key={userId} value={userId}>
                          {displayName}
                        </option>
                      );
                    })}
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="toUser">Who is receiving? *</label>
                  <select
                    id="toUser"
                    value={toUser}
                    onChange={(e) => setToUser(e.target.value)}
                    required
                  >
                    <option value="">Select recipient...</option>
                    {members?.map((member) => {
                      const userId = member.user_id || member.id;
                      const displayName = member.user?.display_name || 
                                        member.user?.username || 
                                        member.display_name ||
                                        member.username ||
                                        'Unknown User';
                      return (
                        <option key={userId} value={userId}>
                          {displayName}
                        </option>
                      );
                    })}
                  </select>
                </div>
              </>
            )}

            <div className="form-group">
              <label htmlFor="amount">Amount *</label>
              <input
                type="number"
                id="amount"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                step="0.01"
                min="0.01"
                max={maxAmount}
                required
                placeholder="Enter amount"
              />
              {!isManualMode && suggestedAmount > 0 && (
                <div style={{ marginTop: '0.5rem' }}>
                  <small style={{ color: '#666', display: 'block' }}>
                    Full settlement amount: {formatMoney(suggestedAmount, currency)}
                  </small>
                  {amount < suggestedAmount && amount > 0 && (
                    <small style={{ color: '#f39c12', display: 'block', marginTop: '0.25rem', fontWeight: '500' }}>
                       Partial payment: {formatMoney(Number(suggestedAmount) - Number(amount), currency)} will remain
                    </small>
                  )}
                </div>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="notes">Notes (Optional)</label>
              <textarea
                id="notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add a note about this payment (e.g., 'Paid via Venmo', 'Cash payment')"
                rows="3"
              />
            </div>
          </div>

          <div className="modal-footer">
            <button 
              type="button" 
              onClick={onClose}
              className="btn btn-secondary"
            >
              Cancel
            </button>
            <button 
              type="submit" 
              className="btn btn-primary"
              disabled={loading || !amount || Number(amount) <= 0 || Number(amount) > maxAmount}
            >
              Record Payment
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default SettlementModal;

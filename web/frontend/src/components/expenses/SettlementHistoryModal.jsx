import React from 'react';
import './SettlementHistoryModal.css';

const SettlementHistoryModal = ({ isOpen, onClose, settlements = [], currency = 'USD' }) => {
  if (!isOpen) return null;

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', { 
      style: 'currency', 
      currency: currency 
    }).format(Math.abs(amount));
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      day: '2-digit',
      month: 'short',
      year: '2-digit'
    });
  };

  const totalSettled = settlements.reduce((sum, s) => sum + (s.amount || 0), 0);

  return (
    <>
      <div className="settlement-modal-overlay" onClick={onClose} />
      <div className="settlement-receipt-modal">
        
        {/* Receipt Header */}
        <div className="receipt-header">
          <div>
            <h2>Settlement History</h2>
            <p className="receipt-subtitle">Payment Records</p>
          </div>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <div className="receipt-body">
          {settlements.length === 0 ? (
            <div className="empty-receipt">
              <p className="empty-title">No Settlements</p>
              <p className="empty-subtitle">Payments between members will appear here</p>
            </div>
          ) : (
            <>
              {/* Summary Box */}
              <div className="receipt-summary-box">
                <div className="summary-row-main">
                  <span>Total Settled</span>
                  <span className="total-value">{formatCurrency(totalSettled)}</span>
                </div>
                <div className="summary-row-sub">
                  <span>{settlements.length} payment{settlements.length !== 1 ? 's' : ''} recorded</span>
                </div>
              </div>

              {/* Table Layout */}
              <div className="settlement-table">
                <div className="table-header">
                  <div className="col-description">DESCRIPTION</div>
                  <div className="col-from">FROM</div>
                  <div className="col-to">TO</div>
                  <div className="col-status">STATUS</div>
                  <div className="col-date">DATE</div>
                  <div className="col-amount">AMOUNT</div>
                </div>

                <div className="table-body">
                  {settlements.map((settlement, index) => {
                    const status = settlement.payment_status || 'Full Payment';
                    const statusClass = status === 'Full Payment' ? 'status-full' : 'status-partial';
                    
                    return (
                      <div key={settlement.settlement_id || index} className="table-row">
                        <div className="col-description">
                          <div className="payment-desc">
                            {settlement.notes || `Payment #${settlements.length - index}`}
                          </div>
                        </div>
                        <div className="col-from">
                          <span className="user-name">{settlement.from_display_name || 'Unknown'}</span>
                        </div>
                        <div className="col-to">
                          <span className="user-name">{settlement.to_display_name || 'Unknown'}</span>
                        </div>
                        <div className="col-status">
                          <span className={`status-badge ${statusClass}`}>{status}</span>
                        </div>
                        <div className="col-date">
                          {formatDate(settlement.created_at || settlement.date)}
                        </div>
                        <div className="col-amount">
                          <span className="amount-positive">{formatCurrency(settlement.amount)}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Footer Total */}
              <div className="receipt-footer-total">
                <span>TOTAL</span>
                <span>{formatCurrency(totalSettled)}</span>
              </div>
              
              <p className="receipt-note">
                All settlements are recorded and applied to group balances
              </p>
            </>
          )}
        </div>
      </div>
    </>
  );
};

export default SettlementHistoryModal;

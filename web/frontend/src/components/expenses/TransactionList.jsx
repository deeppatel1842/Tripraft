import React, { useState } from 'react';
import { Edit2, Trash2, FolderOpen, Info, ChevronLeft, ChevronRight, History, RefreshCw } from 'lucide-react';
import ExpenseHistoryModal from './ExpenseHistoryModal';
import './ExpenseHistoryModal.css';

const TransactionList = ({ 
  transactions, 
  filter, 
  mode, 
  activeGroup,
  members,
  allMembersMap = {},  // Phase 17 Bug Fix: Include removed members for history display
  currentUserId, // Add current user ID to check ownership
  onEdit, 
  onDelete, 
  onFilterChange 
}) => {
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [selectedTransaction, setSelectedTransaction] = useState(null);
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [historyTransaction, setHistoryTransaction] = useState(null);
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
  };

  // Helper function to get member display name
  // Phase 17 Bug Fix: Also check allMembersMap for removed members
  const getMemberName = (userId) => {
    if (!userId) return 'Unknown User';
    
    // First: Check active members array
    if (members && members.length > 0) {
      const member = members.find(m => (m.user_id || m.id) === userId);
      if (member) {
        return member.user?.display_name || 
               member.user?.username || 
               member.user?.email ||
               member.display_name ||
               member.username || 
               member.email ||
               'Unknown User';
      }
    }
    
    // Second: Check allMembersMap (includes removed members)
    if (allMembersMap && allMembersMap[userId]) {
      return allMembersMap[userId].display_name || `Former Member (${userId.slice(0, 8)})`;
    }
    
    return 'Unknown User';
  };

  // Check if split is equal
  const isEqualSplit = (transaction) => {
    if (!transaction.splits || !Array.isArray(transaction.splits) || transaction.splits.length === 0) return false;
    
    // Ensure all splits have valid amounts
    const validSplits = transaction.splits.filter(split => split && typeof split.amount === 'number');
    if (validSplits.length === 0) return false;
    
    const firstAmount = validSplits[0].amount;
    return validSplits.every(split => Math.abs(split.amount - firstAmount) < 0.01);
  };

  // Get split summary for display
  const getSplitSummary = (transaction) => {
    if (!transaction.splits || !Array.isArray(transaction.splits) || transaction.splits.length === 0) return 'No split';
    
    // Filter out invalid splits
    const validSplits = transaction.splits.filter(split => split && typeof split.amount === 'number');
    if (validSplits.length === 0) return 'No split info';
    
    const totalPeople = validSplits.length;
    
    if (isEqualSplit(transaction)) {
      return `Equal split (${totalPeople} ${totalPeople === 1 ? 'person' : 'people'})`;
    }
    
    // For unequal splits, show count
    const othersCount = validSplits.filter(s => s.user_id !== transaction.paid_by).length;
    if (othersCount === 0) return 'Paid for self';
    if (othersCount === 1) return '1 person';
    return `${othersCount} people`;
  };

  // Helper function to get split members names
  const getSplitWithNames = (transaction) => {
    if (!transaction.splits || transaction.splits.length === 0) return '';
    
    const splitUserIds = transaction.splits
      .map(s => s.user_id)
      .filter(id => id !== transaction.paid_by); // Exclude the payer
    
    if (splitUserIds.length === 0) return 'themselves';
    
    const names = splitUserIds.map(id => getMemberName(id));
    
    if (names.length === 1) return names[0];
    if (names.length === 2) return names.join(' and ');
    return names.slice(0, -1).join(', ') + ', and ' + names[names.length - 1];
  };

  const handleViewDetails = (transaction) => {
    setSelectedTransaction(transaction);
    setShowDetailsModal(true);
  };

  // Phase 12: Handle viewing expense history
  const handleViewHistory = (transaction) => {
    setHistoryTransaction(transaction);
    setShowHistoryModal(true);
  };

  // Check if expense was edited
  // Checks: is_edited flag, edit_count > 0, or updated_at differs from created_at
  const wasEdited = (transaction) => {
    // Check explicit edit flag
    if (transaction.is_edited === true) return true;
    if (transaction.edit_count && transaction.edit_count > 0) return true;
    
    // Check timestamps
    if (transaction.updated_at && transaction.created_at) {
      const created = new Date(transaction.created_at).getTime();
      const updated = new Date(transaction.updated_at).getTime();
      // Consider edited if updated more than 1 minute after creation
      if ((updated - created) > 60000) return true;
    }
    
    return false;
  };

  // Check if current user can edit/delete this expense
  // Role-based permissions:
  // - Group owner can edit/delete ANY expense
  // - Members can only edit/delete their OWN expenses (created_by matches)
  const canUserEditDelete = (transaction) => {
    if (mode !== 'group') {
      // Personal mode: user can edit their own expenses
      return transaction.paid_by === currentUserId || transaction.created_by === currentUserId;
    }
    
    // Group mode: Check if user is group owner
    const isGroupOwner = activeGroup?.created_by === currentUserId;
    if (isGroupOwner) {
      // Group owner can edit/delete ANY expense
      return true;
    }
    
    // Members can only edit/delete expenses they created
    const isCreator = transaction.created_by === currentUserId;
    return isCreator;
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    
    // Handle different date formats
    let date;
    if (dateString.includes('T')) {
      // ISO format: "2025-10-15T23:33:42.864730"
      date = new Date(dateString.split('T')[0] + 'T00:00:00');
    } else {
      // Simple format: "2025-10-15"
      date = new Date(dateString + 'T00:00:00');
    }
    
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric' 
    });
  };

  // Income category check - only Salary is income
  const isIncome = (category) => {
    return category && category.toLowerCase() === 'salary';
  };

  const getFilteredAndSortedTransactions = () => {
    let filtered = transactions;
    
    if (filter.type === 'income') {
      filtered = filtered.filter(t => isIncome(t.category));
    } else if (filter.type === 'expense') {
      filtered = filtered.filter(t => !isIncome(t.category));
    }

    return filtered.sort((a, b) => {
      switch (filter.sortBy) {
        case 'date-asc': return new Date(a.date) - new Date(b.date);
        case 'amount-desc': return b.amount - a.amount;
        case 'amount-asc': return a.amount - b.amount;
        default: return new Date(b.date) - new Date(a.date);
      }
    });
  };

  const filteredTransactions = getFilteredAndSortedTransactions();
  
  // Pagination calculations
  const totalPages = Math.ceil(filteredTransactions.length / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const paginatedTransactions = filteredTransactions.slice(startIndex, endIndex);
  
  // Reset to page 1 when filters change
  React.useEffect(() => {
    setCurrentPage(1);
  }, [filter.type, filter.sortBy, transactions.length]);
  
  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
    }
  };
  
  const handlePageSizeChange = (newSize) => {
    setPageSize(Number(newSize));
    setCurrentPage(1); // Reset to first page
  };

  return (
    <div className="card transactions-card">
      <div className="transactions-header">
        <h2>Transaction History</h2>
        <div className="filters">
          <select 
            value={filter.type}
            onChange={(e) => onFilterChange('type', e.target.value)}
          >
            <option value="all">All Types</option>
            <option value="income">Income</option>
            <option value="expense">Expense</option>
          </select>
          <select 
            value={filter.sortBy}
            onChange={(e) => onFilterChange('sortBy', e.target.value)}
          >
            <option value="date-desc">Date (Newest)</option>
            <option value="date-asc">Date (Oldest)</option>
            <option value="amount-desc">Amount (High-Low)</option>
            <option value="amount-asc">Amount (Low-High)</option>
          </select>
        </div>
      </div>

      {filteredTransactions.length === 0 ? (
        <div className="no-transactions">
          <FolderOpen size={48} />
          <p>{mode === 'group' && !activeGroup 
            ? 'Please select or create a group to start.' 
            : 'No transactions yet.'}</p>
        </div>
      ) : (
        <>
          <div className="pagination-controls-top">
            <div className="pagination-info">
              Showing {startIndex + 1}-{Math.min(endIndex, filteredTransactions.length)} of {filteredTransactions.length} transactions
            </div>
            <div className="page-size-selector">
              <label>Show: </label>
              <select value={pageSize} onChange={(e) => handlePageSizeChange(e.target.value)}>
                <option value="5">5</option>
                <option value="10">10</option>
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
              </select>
              <span> per page</span>
            </div>
          </div>
          
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Description</th>
                  <th className="hide-mobile">Category</th>
                  <th className="hide-tablet">Date</th>
                  {mode === 'group' && <th>Added By</th>}
                  {mode === 'group' && <th className="hide-mobile">Split With</th>}
                  <th>Amount</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {paginatedTransactions.map((t, index) => {
                const isIncomeTransaction = isIncome(t.category);
                const addedByName = mode === 'group' ? getMemberName(t.paid_by) : '';
                const splitSummary = mode === 'group' ? getSplitSummary(t) : '';
                const canEditDelete = canUserEditDelete(t);
                const isEdited = wasEdited(t);
                const isDeleted = t.is_deleted === true;
                const isSyncing = t._optimistic === true; // Phase 17.5: Show syncing indicator

                return (
                  <tr 
                    key={t.id || t.expense_id || index}
                    className={`${isDeleted ? 'transaction-deleted' : ''} ${isSyncing ? 'transaction-syncing' : ''}`}
                  >
                    <td>
                      <p className={`description ${isDeleted ? 'deleted-text' : ''}`}>
                        {t.description}
                        {isDeleted && <span className="deleted-badge">Deleted</span>}
                        {isSyncing && (
                          <span className="syncing-badge" title="Saving to server...">
                            <RefreshCw size={10} className="spin" />
                            Syncing
                          </span>
                        )}
                      </p>
                      <p className="mobile-info">
                        {t.category} - {formatDate(t.date)}
                        {mode === 'group' && <><br/>Added by: {addedByName}</>}
                        {isEdited && (
                          <span 
                            className="edited-badge"
                            onClick={() => handleViewHistory(t)}
                            style={{ marginLeft: '8px' }}
                          >
                            <History size={10} />
                            Edited
                          </span>
                        )}
                      </p>
                    </td>
                    <td className="hide-mobile">
                      <span className="category-badge">{t.category}</span>
                    </td>
                    <td className="hide-tablet">{formatDate(t.date)}</td>
                    {mode === 'group' && <td>{addedByName}</td>}
                    {mode === 'group' && (
                      <td className="hide-mobile">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span>{splitSummary}</span>
                          <button 
                            className="btn-icon"
                            onClick={() => handleViewDetails(t)}
                            title="View split details"
                            style={{ padding: '4px' }}
                          >
                            <Info size={14} />
                          </button>
                        </div>
                      </td>
                    )}
                    <td className={`${isIncomeTransaction ? 'amount-green' : 'amount-red'} ${isDeleted ? 'deleted-amount' : ''}`}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span className={isDeleted ? 'deleted-text' : ''}>{formatCurrency(t.amount)}</span>
                        {isEdited && !isDeleted && (
                          <button 
                            className="btn-icon"
                            onClick={() => handleViewHistory(t)}
                            title="View edit history"
                            style={{ padding: '4px' }}
                          >
                            <History size={14} />
                          </button>
                        )}
                      </div>
                    </td>
                    <td className="actions">
                      {isDeleted ? (
                        <span className="deleted-indicator">
                          <Trash2 size={14} />
                        </span>
                      ) : canEditDelete ? (
                        <>
                          <button 
                            className="btn-icon btn-edit"
                            onClick={() => onEdit(t)}
                            title="Edit transaction"
                          >
                            <Edit2 size={16} />
                          </button>
                          <button 
                            className="btn-icon btn-delete"
                            onClick={() => {
                              const expenseId = t.id || t.expense_id;
                              if (expenseId && !expenseId.toString().startsWith('temp')) {
                                onDelete(expenseId);
                              } else {
                                console.warn('⚠️ Cannot delete expense without valid ID:', expenseId);
                              }
                            }}
                            title="Delete transaction"
                            disabled={!t.id && !t.expense_id}
                          >
                            <Trash2 size={16} />
                          </button>
                        </>
                      ) : mode === 'group' ? (
                        <span style={{ fontSize: '0.75rem', color: '#999' }}>
                          View only
                        </span>
                      ) : null}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        
        {totalPages > 1 && (
          <div className="pagination-controls">
            <button 
              className="btn-pagination"
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
              title="Previous page"
            >
              <ChevronLeft size={18} />
              Previous
            </button>
            
            <div className="pagination-pages">
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                let pageNum;
                if (totalPages <= 5) {
                  pageNum = i + 1;
                } else if (currentPage <= 3) {
                  pageNum = i + 1;
                } else if (currentPage >= totalPages - 2) {
                  pageNum = totalPages - 4 + i;
                } else {
                  pageNum = currentPage - 2 + i;
                }
                
                return (
                  <button
                    key={pageNum}
                    className={`btn-page ${currentPage === pageNum ? 'active' : ''}`}
                    onClick={() => handlePageChange(pageNum)}
                  >
                    {pageNum}
                  </button>
                );
              })}
            </div>
            
            <button 
              className="btn-pagination"
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
              title="Next page"
            >
              Next
              <ChevronRight size={18} />
            </button>
          </div>
        )}
      </>
      )}

      {/* Split Details Modal - Receipt Style */}
      {showDetailsModal && selectedTransaction && (
        <div className="modal-backdrop" onClick={() => setShowDetailsModal(false)}>
          <div className="modal receipt-modal" onClick={(e) => e.stopPropagation()}>
            <div className="receipt-header">
              <div className="receipt-title">RECEIPT</div>
              <div className="receipt-line"></div>
            </div>
            
            <div className="receipt-body">
              <div className="receipt-item">
                <span className="receipt-label">TRANSACTION</span>
                <span className="receipt-value">{selectedTransaction.description}</span>
              </div>
              
              <div className="receipt-divider"></div>
              
              <div className="receipt-item">
                <span className="receipt-label">PAID BY</span>
                <span className="receipt-value">{getMemberName(selectedTransaction.paid_by)}</span>
              </div>
              
              <div className="receipt-item">
                <span className="receipt-label">SPLIT TYPE</span>
                <span className="receipt-value">{isEqualSplit(selectedTransaction) ? 'Equal Split' : 'Custom Split'}</span>
              </div>
              
              <div className="receipt-divider"></div>
              
              <div className="receipt-breakdown">
                <div className="receipt-label">SPLIT BREAKDOWN</div>
                {selectedTransaction.splits && Array.isArray(selectedTransaction.splits) && selectedTransaction.splits.map((split, idx) => (
                  <div key={idx} className="receipt-split-item">
                    <span className="split-name">{getMemberName(split.user_id)}</span>
                    <span className="split-dots"></span>
                    <span className="split-amt">{formatCurrency(split.amount)}</span>
                  </div>
                ))}
              </div>
              
              <div className="receipt-divider-bold"></div>
              
              <div className="receipt-total">
                <span className="total-label">TOTAL AMOUNT</span>
                <span className="total-value">{formatCurrency(selectedTransaction.amount)}</span>
              </div>
            </div>
            
            <div className="receipt-footer">
              <button 
                className="btn-receipt-close"
                onClick={() => setShowDetailsModal(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Phase 12: Expense History Modal */}
      {showHistoryModal && historyTransaction && (
        <ExpenseHistoryModal
          expense={historyTransaction}
          members={members}
          onClose={() => {
            setShowHistoryModal(false);
            setHistoryTransaction(null);
          }}
        />
      )}
    </div>
  );
};

export default TransactionList;

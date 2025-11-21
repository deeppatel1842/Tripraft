import React, { useState } from 'react';
import { Edit2, Trash2, FolderOpen, Info, ChevronLeft, ChevronRight } from 'lucide-react';

const TransactionList = ({ 
  transactions, 
  filter, 
  mode, 
  activeGroup,
  members,
  currentUserId, // Add current user ID to check ownership
  onEdit, 
  onDelete, 
  onFilterChange 
}) => {
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [selectedTransaction, setSelectedTransaction] = useState(null);
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
  };

  // Helper function to get member display name
  const getMemberName = (userId) => {
    if (!userId || !members || members.length === 0) return 'Unknown User';
    
    const member = members.find(m => (m.user_id || m.id) === userId);
    if (!member) return 'Unknown User';
    
    return member.user?.display_name || 
           member.user?.username || 
           member.user?.email ||
           member.display_name ||
           member.username || 
           member.email ||
           'Unknown User';
  };

  // Check if split is equal
  const isEqualSplit = (transaction) => {
    if (!transaction.splits || transaction.splits.length === 0) return false;
    
    const firstAmount = transaction.splits[0].amount;
    return transaction.splits.every(split => Math.abs(split.amount - firstAmount) < 0.01);
  };

  // Get split summary for display
  const getSplitSummary = (transaction) => {
    if (!transaction.splits || transaction.splits.length === 0) return 'No split';
    
    const totalPeople = transaction.splits.length;
    
    if (isEqualSplit(transaction)) {
      return `Equal split (${totalPeople} ${totalPeople === 1 ? 'person' : 'people'})`;
    }
    
    // For unequal splits, show count
    const othersCount = transaction.splits.filter(s => s.user_id !== transaction.paid_by).length;
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

  // Check if current user can edit/delete this expense
  const canUserEditDelete = (transaction) => {
    if (mode !== 'group') {
      // Personal mode: user can edit their own expenses
      return transaction.paid_by === currentUserId;
    }
    
    // Group mode: user can edit if they're involved (payer OR in the split)
    const isPayer = transaction.paid_by === currentUserId;
    const isInSplit = transaction.splits && transaction.splits.some(
      split => split.user_id === currentUserId
    );
    
    return isPayer || isInSplit;
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

                return (
                  <tr key={t.id || t.expense_id || index}>
                    <td>
                      <p className="description">{t.description}</p>
                      <p className="mobile-info">
                        {t.category} - {formatDate(t.date)}
                        {mode === 'group' && <><br/>Added by: {addedByName}</>}
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
                    <td className={isIncomeTransaction ? 'amount-green' : 'amount-red'}>
                      {formatCurrency(t.amount)}
                    </td>
                    <td className="actions">
                      {canEditDelete && (
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
                            onClick={() => onDelete(t.id || t.expense_id)}
                            title="Delete transaction"
                          >
                            <Trash2 size={16} />
                          </button>
                        </>
                      )}
                      {!canEditDelete && mode === 'group' && (
                        <span style={{ fontSize: '0.75rem', color: '#999' }}>
                          View only
                        </span>
                      )}
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
                {selectedTransaction.splits && selectedTransaction.splits.map((split, idx) => (
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
    </div>
  );
};

export default TransactionList;

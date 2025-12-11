import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';

const TransactionModal = ({ 
  mode, 
  activeGroup,
  members, 
  editingTransaction, 
  onSave, 
  onClose, 
  onAlert,
  currentUser
}) => {
  const [formData, setFormData] = useState({
    type: 'expense',
    description: '',
    amount: '',
    category: 'Food',
    date: new Date().toISOString().split('T')[0],
    paidBy: '',
    splitWith: []
  });

  // Helper function to get member display name
  const getMemberName = (member) => {
    return member.user?.display_name || 
           member.user?.username || 
           member.user?.email ||
           member.display_name ||
           member.username || 
           member.email ||
           'Unknown User';
  };

  // Helper function to get member ID
  const getMemberId = (member) => {
    return member.user_id || member.id;
  };

  useEffect(() => {
    if (editingTransaction) {
      // Determine type based on category
      const isIncome = editingTransaction.category && editingTransaction.category.toLowerCase() === 'salary';
      
      // 🔧 CRITICAL FIX: Backend uses snake_case (paid_by), frontend uses camelCase (paidBy)
      const paidByValue = editingTransaction.paidBy || editingTransaction.paid_by || '';
      const splitWithValue = editingTransaction.splitWith || 
        (editingTransaction.splits ? editingTransaction.splits.map(s => s.user_id) : []);
      
      // 🔧 FIX: Format date to yyyy-MM-dd for HTML date input
      // Backend may return ISO format like "2025-11-26T00:00:00", expense_date field, or Firestore Timestamp
      let dateValue = editingTransaction.date || editingTransaction.expense_date || new Date().toISOString();
      
      // Handle Firestore Timestamp objects
      if (dateValue && typeof dateValue === 'object' && dateValue.toDate) {
        dateValue = dateValue.toDate().toISOString().split('T')[0];
      } else if (dateValue && typeof dateValue === 'object' && dateValue.seconds) {
        // Firestore Timestamp as plain object
        dateValue = new Date(dateValue.seconds * 1000).toISOString().split('T')[0];
      } else if (typeof dateValue === 'string' && dateValue.includes('T')) {
        // ISO format - extract just the date part
        dateValue = dateValue.split('T')[0];
      } else if (typeof dateValue === 'string' && dateValue.includes(' ')) {
        // Datetime with space - extract just the date part
        dateValue = dateValue.split(' ')[0];
      }
      // Ensure valid format, fallback to today
      if (!dateValue || !/^\d{4}-\d{2}-\d{2}$/.test(dateValue)) {
        dateValue = new Date().toISOString().split('T')[0];
      }
      
      setFormData({
        type: isIncome ? 'income' : 'expense',
        description: editingTransaction.description || '',
        amount: editingTransaction.amount || '',
        category: editingTransaction.category || 'Food',
        date: dateValue,
        paidBy: paidByValue,
        splitWith: splitWithValue
      });
      
      console.log('📝 Editing transaction loaded:', {
        id: editingTransaction.id,
        paidBy: paidByValue,
        splitWith: splitWithValue,
        date: dateValue
      });
    } else if (mode === 'group' && members && members.length > 0) {
      const firstMemberId = getMemberId(members[0]);
      const allMemberIds = members.map(m => getMemberId(m));
      setFormData(prev => ({
        ...prev,
        type: 'expense',
        paidBy: currentUser?.uid || firstMemberId,
        splitWith: allMemberIds
      }));
    }
  }, [editingTransaction, mode, members, currentUser]);

  // When type changes to income, set category to Salary
  const handleTypeChange = (newType) => {
    setFormData(prev => ({
      ...prev,
      type: newType,
      category: newType === 'income' ? 'Salary' : 'Food'
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (mode === 'group' && formData.splitWith.length === 0) {
      onAlert('You must split the expense with at least one person.');
      return;
    }

    const transactionData = {
      type: mode === 'group' ? 'expense' : formData.type,
      description: formData.description,
      amount: parseFloat(formData.amount),
      category: formData.category,
      date: formData.date,
      ...(mode === 'group' && {
        paidBy: formData.paidBy,
        splitWith: formData.splitWith
      })
    };

    console.log('💾 TransactionModal - Submitting data:', transactionData);
    console.log('   paidBy value:', formData.paidBy, 'Type:', typeof formData.paidBy);
    onSave(transactionData);
  };

  const handleSplitToggle = (memberId) => {
    setFormData(prev => ({
      ...prev,
      splitWith: prev.splitWith.includes(memberId)
        ? prev.splitWith.filter(id => id !== memberId)
        : [...prev.splitWith, memberId]
    }));
  };

  // Use members prop directly instead of activeGroup.members
  const groupMembers = members || [];

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{editingTransaction ? 'Edit Transaction' : (mode === 'personal' ? 'Add Personal Transaction' : 'Add Group Expense')}</h2>
          <button className="btn-close" onClick={onClose}>
            <X size={24} />
          </button>
        </div>
        <form onSubmit={handleSubmit}>
          {mode === 'personal' && (
            <div className="form-group">
              <label>Transaction Type</label>
              <div className="radio-group">
                <label className={formData.type === 'income' ? 'active' : ''}>
                  <input 
                    type="radio" 
                    name="type" 
                    value="income"
                    checked={formData.type === 'income'}
                    onChange={(e) => handleTypeChange(e.target.value)}
                  />
                  <span>Income</span>
                </label>
                <label className={formData.type === 'expense' ? 'active' : ''}>
                  <input 
                    type="radio" 
                    name="type" 
                    value="expense"
                    checked={formData.type === 'expense'}
                    onChange={(e) => handleTypeChange(e.target.value)}
                  />
                  <span>Expense</span>
                </label>
              </div>
            </div>
          )}

          <div className="form-group">
            <label htmlFor="description">Description</label>
            <input 
              type="text" 
              id="description"
              placeholder="e.g., Groceries, Dinner"
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="amount">Amount</label>
            <div className="amount-input">
              <span className="currency-symbol">$</span>
              <input 
                type="number" 
                id="amount"
                placeholder="0.00"
                min="0.01"
                step="0.01"
                value={formData.amount}
                onChange={(e) => setFormData(prev => ({ ...prev, amount: e.target.value }))}
                required
              />
            </div>
          </div>

          {mode === 'group' && groupMembers.length > 0 && (
            <>
              <div className="form-group">
                <label htmlFor="paidBy">Paid By</label>
                <select 
                  id="paidBy"
                  value={formData.paidBy}
                  onChange={(e) => setFormData(prev => ({ ...prev, paidBy: e.target.value }))}
                  required
                >
                  {groupMembers.map(member => {
                    const memberId = getMemberId(member);
                    const memberName = getMemberName(member);
                    return (
                      <option key={memberId} value={memberId}>
                        {memberName}
                        {memberId === currentUser?.uid ? ' (You)' : ''}
                      </option>
                    );
                  })}
                </select>
              </div>

              <div className="form-group">
                <label>Split Between</label>
                <div className="checkbox-list">
                  {groupMembers.map(member => {
                    const memberId = getMemberId(member);
                    const memberName = getMemberName(member);
                    return (
                      <label key={memberId}>
                        <input 
                          type="checkbox" 
                          value={memberId}
                          checked={formData.splitWith.includes(memberId)}
                          onChange={() => handleSplitToggle(memberId)}
                        />
                        <span>
                          {memberName}
                          {memberId === currentUser?.uid ? ' (You)' : ''}
                        </span>
                      </label>
                    );
                  })}
                </div>
              </div>
            </>
          )}

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="category">Category</label>
              <select 
                id="category"
                value={formData.category}
                onChange={(e) => setFormData(prev => ({ ...prev, category: e.target.value }))}
                disabled={mode === 'personal' && formData.type === 'income'}
                required
              >
                {mode === 'personal' && formData.type === 'income' ? (
                  <option value="Salary">Salary</option>
                ) : (
                  <>
                    <option value="Food">Food</option>
                    <option value="Transport">Transport</option>
                    <option value="Bills">Bills</option>
                    <option value="Entertainment">Entertainment</option>
                    <option value="Shopping">Shopping</option>
                    <option value="Health">Health</option>
                    <option value="Other">Other</option>
                  </>
                )}
              </select>
            </div>
            <div className="form-group">
              <label htmlFor="date">Date</label>
              <input 
                type="date" 
                id="date"
                value={formData.date}
                max={new Date().toISOString().split('T')[0]}
                onChange={(e) => setFormData(prev => ({ ...prev, date: e.target.value }))}
                required
              />
            </div>
          </div>

          <div className="modal-actions">
            <button 
              type="button" 
              className="btn-cancel"
              onClick={onClose}
            >
              Cancel
            </button>
            <button type="submit" className="btn-save">Save</button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default TransactionModal;

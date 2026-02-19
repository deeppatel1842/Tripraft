import React, { useState, useEffect } from 'react';
import {
  Pencil,
  Trash2,
  Map,
  BarChart2,
  CheckSquare,
  Plus,
  ArrowRight,
  AlertCircle,
} from 'lucide-react';
import EditBudgetModal from './EditBudgetModal';
import '../css/RightSidebar.css';

const DEMO_EXPENSES = {
  totalEstimated: 1200,
  spent: 450,
  perPerson: 150,
};

const DEMO_ITINERARY = [
  {
    id: 1,
    order: 1,
    name: 'Space Needle',
    category: 'Sightseeing',
    duration: '2 hrs',
    color: 'indigo',
  },
  {
    id: 2,
    order: 2,
    name: 'The Pink Door',
    category: 'Dinner Reservation',
    time: '7:00 PM',
    color: 'orange',
  },
];

const DEMO_POLLS = [
  {
    id: 1,
    question: 'Dinner Saturday Night?',
    options: [
      { id: 1, label: 'Sushi', emoji: '', votes: 3 },
      { id: 2, label: 'Pizza', emoji: '', votes: 1 },
    ],
  },
];

const DEMO_CHECKLIST = [
  { id: 1, label: 'Book rental car', completed: false },
  { id: 2, label: 'Buy flight tickets', completed: true },
  { id: 3, label: 'Buy sunscreen', completed: false },
];

export default function RightSidebar({
  expenses = DEMO_EXPENSES,
  itinerary = DEMO_ITINERARY,
  polls = DEMO_POLLS,
  checklist = DEMO_CHECKLIST,
  onEditExpense,
  onSaveBudget,
  isSavingBudget = false,
  onLinkSplitwise,
  isLinkingExpense = false,
  onEditItinerary,
  onDeleteItinerary,
  onShowItineraryMap,
  showingItineraryMap = false,
  onCreatePoll,
  onEditPoll,
  onDeletePoll,
  onVotePoll,
  onAddChecklistItem,
  onEditChecklistItem,
  onDeleteChecklistItem,
  onToggleChecklistItem,
  onExport,
}) {
  const [checklistItems, setChecklistItems] = useState(checklist);
  const [isBudgetModalOpen, setIsBudgetModalOpen] = useState(false);

  // Update local state when prop changes
  useEffect(() => {
    setChecklistItems(checklist);
  }, [checklist]);

  const handleToggleItem = (itemId) => {
    setChecklistItems(prev =>
      prev.map(item =>
        item.id === itemId ? { ...item, completed: !item.completed } : item
      )
    );
    if (onToggleChecklistItem) {
      onToggleChecklistItem(itemId);
    }
  };

  const getTotalVotes = (options) => {
    return options.reduce((sum, opt) => sum + opt.votes, 0);
  };

  return (
    <aside className="rs-sidebar">
      {/* Expenses Section */}
      <div className="rs-section rs-expenses-section">
        <div className="rs-section-header">
          <h3 className="rs-section-title">Expenses</h3>
          <div className="rs-section-actions">
            {expenses.linked && (
              <span className="rs-linked-badge" title={`${expenses.expenseCount || 0} expenses tracked`}>
                Linked
              </span>
            )}
            <button
              className="rs-icon-btn"
              onClick={() => setIsBudgetModalOpen(true)}
              title="Edit Budget"
            >
              <Pencil className="rs-icon-sm" />
            </button>
            {!expenses.linked && (
              <button 
                className="rs-link-btn" 
                onClick={onLinkSplitwise}
                disabled={isLinkingExpense}
              >
                {isLinkingExpense ? 'Linking...' : 'Link to Expenses'}
              </button>
            )}
          </div>
        </div>

        <div className="rs-expense-cards">
          <div className="rs-expense-card">
            <p className="rs-expense-label">Total Est.</p>
            <p className="rs-expense-value">${(expenses.totalEstimated || 0).toLocaleString()}</p>
          </div>
          <div className="rs-expense-card rs-expense-card-primary">
            <p className="rs-expense-label rs-expense-label-primary">Spent</p>
            <p className="rs-expense-value rs-expense-value-primary">
              ${(expenses.spent || 0).toLocaleString()}
            </p>
          </div>
          <div className="rs-expense-card">
            <p className="rs-expense-label">Your Expenses</p>
            <p className="rs-expense-value">${(expenses.userSpent || 0).toLocaleString()}</p>
          </div>
        </div>
      </div>

      {/* Scrollable Content */}
      <div className="rs-scrollable">
        {/* Itinerary Section */}
        <div className="rs-section rs-itinerary-section">
          <div className="rs-section-header">
            <h3 className="rs-section-title">
              <Map className="rs-icon-sm" />
              Itinerary
            </h3>
            <div className="rs-section-actions">
              <button
                className={`rs-icon-btn ${showingItineraryMap ? 'rs-icon-btn-active' : ''}`}
                onClick={onShowItineraryMap}
                title={showingItineraryMap ? "Show all places on map" : "Show itinerary on map"}
              >
                <Map className="rs-icon-sm" />
              </button>
              <span className="rs-badge">{itinerary.length}</span>
            </div>
          </div>

          <div className="rs-itinerary-list">
            {itinerary.map((item) => (
              <div key={item.id} className="rs-itinerary-item">
                <div
                  className={`rs-itinerary-number rs-itinerary-number-${item.color}`}
                >
                  {item.order}
                </div>
                <div className="rs-itinerary-info">
                  <p className="rs-itinerary-name">{item.name}</p>
                  <p className="rs-itinerary-meta">
                    {item.category} • {item.duration || item.time || '1 hr'}
                    {item.date && ` • ${item.date}`}
                  </p>
                  {item.notes && (
                    <p className="rs-itinerary-notes">{item.notes}</p>
                  )}
                </div>
                <div className="rs-itinerary-actions">
                  <button
                    className="rs-action-btn rs-action-btn-edit"
                    onClick={() => onEditItinerary && onEditItinerary(item.id)}
                    title="Edit"
                  >
                    <Pencil className="rs-icon-xs" />
                  </button>
                  <button
                    className="rs-action-btn rs-action-btn-delete"
                    onClick={() => onDeleteItinerary && onDeleteItinerary(item.id)}
                    title="Delete"
                  >
                    <Trash2 className="rs-icon-xs" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Polls Section */}
        <div className="rs-section">
          <div className="rs-section-header">
            <h3 className="rs-section-title">
              <BarChart2 className="rs-icon-sm" />
              Active Polls
            </h3>
            <button className="rs-add-btn" onClick={onCreatePoll}>
              <Plus className="rs-icon-xs" />
            </button>
          </div>

          {polls.map((poll) => {
            const totalVotes = getTotalVotes(poll.options);
            return (
              <div key={poll.id} className="rs-poll-card">
                <div className="rs-poll-header">
                  <p className="rs-poll-question">{poll.question}</p>
                  <div className="rs-poll-actions">
                    <button
                      className="rs-action-btn-inline"
                      onClick={() => onEditPoll && onEditPoll(poll.id)}
                    >
                      <Pencil className="rs-icon-xs" />
                    </button>
                    <button
                      className="rs-action-btn-inline rs-action-btn-inline-delete"
                      onClick={() => onDeletePoll && onDeletePoll(poll.id)}
                    >
                      <Trash2 className="rs-icon-xs" />
                    </button>
                  </div>
                </div>

                <div className="rs-poll-options">
                  {poll.options.map((option) => {
                    const percentage = totalVotes > 0 ? (option.votes / totalVotes) * 100 : 0;
                    const isWinning = option.votes === Math.max(...poll.options.map(o => o.votes));
                    return (
                      <div
                        key={option.id}
                        className="rs-poll-option"
                        onClick={() => onVotePoll && onVotePoll(poll.id, option.id)}
                      >
                        <div
                          className={`rs-poll-bar ${isWinning ? 'rs-poll-bar-winning' : ''}`}
                          style={{ width: `${percentage}%` }}
                        ></div>
                        <div className="rs-poll-option-content">
                          <span className="rs-poll-option-label">
                            {option.label} {option.emoji}
                          </span>
                          <span className={`rs-poll-option-votes ${isWinning ? 'rs-poll-votes-winning' : ''}`}>
                            {option.votes} vote{option.votes !== 1 ? 's' : ''}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        {/* Packing List / Checklist Section */}
        <div className="rs-section">
          <div className="rs-section-header">
            <h3 className="rs-section-title">
              <CheckSquare className="rs-icon-sm" />
              Packing List
            </h3>
            <button className="rs-add-btn" onClick={onAddChecklistItem}>
              <Plus className="rs-icon-xs" />
            </button>
          </div>

          <div className="rs-checklist">
            {/* Sort by priority: high > medium > low, uncompleted first */}
            {[...checklistItems]
              .sort((a, b) => {
                // Completed items go to bottom
                if (a.completed !== b.completed) {
                  return a.completed ? 1 : -1;
                }
                // Sort by priority
                const priorityOrder = { high: 0, medium: 1, low: 2 };
                const aPriority = priorityOrder[a.priority] ?? 1;
                const bPriority = priorityOrder[b.priority] ?? 1;
                return aPriority - bPriority;
              })
              .map((item) => (
              <div key={item.id} className={`rs-checklist-item ${item.priority === 'high' ? 'rs-checklist-high' : ''}`}>
                <label className="rs-checklist-label">
                  <input
                    type="checkbox"
                    className="rs-checkbox"
                    checked={item.completed}
                    onChange={() => handleToggleItem(item.id)}
                  />
                  <div className="rs-checklist-content">
                    <div className="rs-checklist-row">
                      {item.priority === 'high' && (
                        <AlertCircle className="rs-priority-icon rs-priority-high" size={12} />
                      )}
                      {item.priority === 'low' && (
                        <span className="rs-priority-icon rs-priority-low">-</span>
                      )}
                      <span className={`rs-checklist-text ${item.completed ? 'rs-checklist-completed' : ''}`}>
                        {item.label}
                      </span>
                    </div>
                    {item.author && (
                      <span className="rs-checklist-author">by {item.author}</span>
                    )}
                  </div>
                </label>
                <div className="rs-checklist-actions">
                  <button
                    className="rs-action-btn-inline"
                    onClick={() => onEditChecklistItem && onEditChecklistItem(item.id)}
                  >
                    <Pencil className="rs-icon-xs" />
                  </button>
                  <button
                    className="rs-action-btn-inline rs-action-btn-inline-delete"
                    onClick={() => onDeleteChecklistItem && onDeleteChecklistItem(item.id)}
                  >
                    <Trash2 className="rs-icon-xs" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Export Button */}
      <div className="rs-footer">
        <button className="rs-export-btn" onClick={onExport}>
          <span>Export Final Itinerary</span>
          <ArrowRight className="rs-icon-sm" />
        </button>
      </div>

      {/* Edit Budget Modal */}
      <EditBudgetModal
        isOpen={isBudgetModalOpen}
        onClose={() => setIsBudgetModalOpen(false)}
        onSave={onSaveBudget || onEditExpense || (() => Promise.resolve())}
        currentBudget={expenses.totalEstimated || 0}
        currentCurrency={expenses.currency || 'USD'}
        isSaving={isSavingBudget}
      />
    </aside>
  );
}

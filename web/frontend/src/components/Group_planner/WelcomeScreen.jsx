import React, { useState } from 'react';
import { MapPin, FileText, Send, List, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useGroupPlanner } from '../../context/GroupPlannerContext';
import { useGroupPlannerAuth } from '../../hooks/useGroupPlannerAuth';
import LoginPromptModal from '../common/LoginPromptModal';
import './WelcomeScreen.css';

/**
 * WelcomeScreen - Initial view for users with no groups
 * Uses useGroupPlanner() context for creating groups and invitations
 * All operations automatically cached after creation
 */
export default function WelcomeScreen({ onGroupCreated }) {
  const navigate = useNavigate();
  const { isAuthenticated } = useGroupPlannerAuth();
  const { createGroup, createInvitation } = useGroupPlanner();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState({
    groupName: '',
    destination: '',
    invites: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [showLoginPrompt, setShowLoginPrompt] = useState(false);

  const handleOpenModal = () => {
    // Check if user is logged in before allowing group creation
    if (!isAuthenticated) {
      setShowLoginPrompt(true);
      return;
    }
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setFormData({
      groupName: '',
      destination: '',
      invites: ''
    });
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  /**
   * Handle group creation with optional invitations
   * @param {Event} e - Form submit event
   */
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.groupName.trim()) {
      console.error('Group name is required');
      return;
    }

    setIsSubmitting(true);
    try {
      // Create group using context operation
      const newGroup = await createGroup(
        formData.groupName.trim(),
        formData.destination.trim() || null
      );
      
      // Get the group ID (handle both id and group_id properties)
      const groupId = newGroup.group_id || newGroup.id;
      console.log('✅ [WELCOME] Group created with ID:', groupId);
      
      // Handle invites if provided
      if (formData.invites.trim()) {
        const emails = formData.invites.split(',').map(e => e.trim()).filter(Boolean);
        console.log('📧 [WELCOME] Sending invitations to:', emails);
        for (const email of emails) {
          try {
            await createInvitation(groupId, email);
            console.log('✅ [WELCOME] Invitation sent to:', email);
          } catch (err) {
            console.error('❌ [WELCOME] Failed to invite:', email, err);
          }
        }
      }

      handleCloseModal();
      if (onGroupCreated) {
        onGroupCreated(newGroup);
      }
    } catch (error) {
      console.error('Failed to create group:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="welcome-screen">
      <div className="bg-glow" aria-hidden="true"></div>
      
      <div className="welcome-content">
        <p className="eyebrow">Your hub for collaborative travel planning</p>

        <h1 className="welcome-title">
          Seamlessly craft your <span className="accent">shared adventure</span>
        </h1>

        <p className="welcome-lead">
          Welcome to <strong>Group Planner</strong> — your centralized command center that turns complex group logistics
          into planning synergy. It's time to <strong>find places</strong>, <strong>set polls</strong>, and
          <strong> map your journey</strong> together.
        </p>

        <ul className="features-list">
          <li className="feature-chip">
            <MapPin size={18} />
            Find Places & Pin Maps
          </li>
          <li className="feature-chip">
            <FileText size={18} />
            Create Polls & Docs
          </li>
          <li className="feature-chip">
            <Send size={18} />
            Send Invitations
          </li>
          <li className="feature-chip">
            <List size={18} />
            Build Travel Plan
          </li>
        </ul>

        <button 
          className="btn-primary-welcome" 
          onClick={handleOpenModal}
          disabled={isSubmitting}
        >
          <span className="plus-icon">+</span>
          Create Your First Group
        </button>

        <p className="subnote">No credit card required. Invite friends in seconds.</p>
      </div>

      {/* Create Group Modal */}
      {isModalOpen && (
        <div className="modal-wrapper" onClick={handleCloseModal}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span className="modal-badge">
                  <MapPin size={18} />
                  New Group
                </span>
                <h2 className="modal-title">Create a Group</h2>
              </div>
              <button 
                className="modal-close-btn" 
                onClick={handleCloseModal}
                disabled={isSubmitting}
              >
                <X size={20} />
              </button>
            </div>

            <div className="modal-body">
              <p className="modal-hint">
                Name your group, pick dates, and invite friends. You can edit these later.
              </p>

              <form onSubmit={handleSubmit}>
                <div className="form-grid">
                  <div style={{ gridColumn: '1 / -1' }}>
                    <label htmlFor="groupName">Group name *</label>
                    <input
                      id="groupName"
                      name="groupName"
                      type="text"
                      placeholder="e.g., Bali Birthday Trip"
                      value={formData.groupName}
                      onChange={handleChange}
                      required
                      maxLength={60}
                      disabled={isSubmitting}
                    />
                    <div className="field-hint">Make it memorable and unique.</div>
                  </div>

                  <div style={{ gridColumn: '1 / -1' }}>
                    <label htmlFor="destination">Destination</label>
                    <input
                      id="destination"
                      name="destination"
                      type="text"
                      placeholder="e.g., Ubud, Indonesia"
                      value={formData.destination}
                      onChange={handleChange}
                      disabled={isSubmitting}
                    />
                  </div>

                  <div style={{ gridColumn: '1 / -1' }}>
                    <label htmlFor="invites">Invite emails (optional)</label>
                    <input
                      id="invites"
                      name="invites"
                      type="text"
                      placeholder="alice@example.com, bob@example.com"
                      value={formData.invites}
                      onChange={handleChange}
                      disabled={isSubmitting}
                    />
                    <div className="field-hint">Comma-separated. You can invite more people later.</div>
                  </div>
                </div>

                <div className="modal-footer">
                  <button 
                    type="button" 
                    className="btn-ghost" 
                    onClick={handleCloseModal}
                    disabled={isSubmitting}
                  >
                    Cancel
                  </button>
                  <button 
                    type="submit" 
                    className="btn-primary"
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? 'Creating...' : 'Create Group'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Login Prompt Modal */}
      <LoginPromptModal
        isOpen={showLoginPrompt}
        onClose={() => setShowLoginPrompt(false)}
        message="Please login first to create a group and start planning your trip."
      />
    </div>
  );
}

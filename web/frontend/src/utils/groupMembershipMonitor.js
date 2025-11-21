/**
 * 🐛 GROUP MEMBERSHIP MONITOR
 * ===========================
 * 
 * Detects when:
 * 1. User has been removed from a group (by owner)
 * 2. Group has been deleted (by owner)
 * 3. User should no longer see the group
 * 
 * Used to fix Bug #4: Member removal not reflecting in real-time
 */

export class GroupMembershipMonitor {
  constructor() {
    this.knownGroups = new Map(); // group_id => { memberCount, lastChecked }
    this.pollInterval = null;
    this.onGroupRemoved = null; // Callback when group is removed
    this.onMemberRemoved = null; // Callback when user is removed
  }

  /**
   * Start monitoring user's group memberships
   * @param {Function} fetchGroups - Function that fetches user's groups
   * @param {Function} onGroupRemoved - Callback when group is deleted
   * @param {Function} onMemberRemoved - Callback when user is removed from group
   * @param {number} interval - Poll interval in milliseconds (default: 15000)
   */
  startMonitoring(fetchGroups, onGroupRemoved, onMemberRemoved, interval = 15000) {
    this.fetchGroups = fetchGroups;
    this.onGroupRemoved = onGroupRemoved;
    this.onMemberRemoved = onMemberRemoved;

    // Initial fetch to populate known groups
    this.checkForChanges();

    // Poll for changes
    this.pollInterval = setInterval(() => {
      this.checkForChanges();
    }, interval);

    console.log('🔍 Group membership monitoring started (polling every 15s)');
  }

  /**
   * Stop monitoring
   */
  stopMonitoring() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
      console.log('🛑 Group membership monitoring stopped');
    }
  }

  /**
   * Check for changes in group memberships
   */
  async checkForChanges() {
    try {
      const response = await this.fetchGroups();
      const currentGroups = response?.groups || [];
      
      // Build map of current group IDs
      const currentGroupIds = new Set(currentGroups.map(g => g.group_id));

      // Check if any previously known groups are now missing
      for (const [groupId, groupInfo] of this.knownGroups.entries()) {
        if (!currentGroupIds.has(groupId)) {
          console.warn(`🚨 Group ${groupId} is no longer accessible - user was removed or group was deleted`);
          
          // Trigger callback
          if (this.onGroupRemoved) {
            this.onGroupRemoved(groupId, groupInfo);
          }

          // Remove from known groups
          this.knownGroups.delete(groupId);
        }
      }

      // Update known groups
      currentGroups.forEach(group => {
        this.knownGroups.set(group.group_id, {
          name: group.name,
          memberCount: group.members?.length || 0,
          lastChecked: Date.now()
        });
      });

    } catch (error) {
      console.error('❌ Error checking group memberships:', error);
    }
  }

  /**
   * Force immediate check (e.g., after getting a 403 error)
   */
  forceCheck() {
    console.log('🔄 Forcing immediate membership check...');
    this.checkForChanges();
  }
}

export const groupMembershipMonitor = new GroupMembershipMonitor();

// Purpose: Renders the Logistics Tab interface within apps\web\src\features\trips\jsx\tabs.
import React, { useState, useMemo, useRef, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useGroupMembers, useGroupChecklist, useToggleChecklistItem, useVaultFiles, useUploadVaultFile, useDeleteVaultFile, gpKeys } from '../../../../hooks/useGroupPlannerQuery';
import groupPlannerApi from '../../../../services/groupPlannerApi';
import apiClient from '../../../../utils/apiClient';
import GlobalConfig from '../../../../config/globalConfig';
import { useAuth } from '../../../../context/AuthContext';
import { toArray } from '../../utils/groupPlannerUtils';
import { formatFileSize } from '../../utils/formatters';
import { Eye, Trash2, X } from 'lucide-react';

/**
 * Logistics tab - checklist + vault file management.
 *
 * Props: groupId, showToast
 */
export default function LogisticsTab({ groupId, showToast }) {
  const queryClient = useQueryClient();
  const { currentUser } = useAuth();
  const { data: membersRaw } = useGroupMembers(groupId);
  const members = toArray(membersRaw, 'members');
  const isAdmin = members.some(m => String(m.user_id) === String(currentUser?.uid) && ['creator', 'admin'].includes(m.role));
  const { data: checklistRaw } = useGroupChecklist(groupId);
  const { data: vaultRaw } = useVaultFiles(groupId);
  const toggleChecklistMut = useToggleChecklistItem(groupId);
  const uploadVaultMut = useUploadVaultFile(groupId);
  const deleteVaultMut = useDeleteVaultFile(groupId);

  const checklist = useMemo(() => toArray(checklistRaw, 'checklist'), [checklistRaw]);
  const vault = useMemo(() => toArray(vaultRaw, 'documents'), [vaultRaw]);

  const vaultInputRef = useRef(null);
  const [showChecklistInput, setShowChecklistInput] = useState(false);
  const [newChecklistText, setNewChecklistText] = useState('');
  const [previewDoc, setPreviewDoc] = useState(null);
  const [previewBlobUrl, setPreviewBlobUrl] = useState(null);
  const [previewError, setPreviewError] = useState('');

  // Shared cookie-authenticated client owns timeout, refresh and binary responses.
  useEffect(() => {
    setPreviewBlobUrl(null);
    setPreviewError('');
    if (!previewDoc) return;
    const controller = new AbortController();
    let url;
    apiClient.get(GlobalConfig.ENDPOINTS.GROUP_PLANNER + '/groups/' + groupId + '/vault/' + previewDoc.id, { responseType: 'blob', signal: controller.signal })
      .then(blob => { if (!controller.signal.aborted) { url = URL.createObjectURL(blob); setPreviewBlobUrl(url); } })
      .catch(error => { if (!controller.signal.aborted) setPreviewError(error.message || 'Preview unavailable'); });
    return () => { controller.abort(); if (url) URL.revokeObjectURL(url); };
  }, [previewDoc, groupId]);

  const handleToggleChecklist = async (itemId) => {
    try {
      await toggleChecklistMut.mutateAsync(itemId);
      queryClient.invalidateQueries({ queryKey: gpKeys.checklist(groupId) });
    } catch {
      showToast('Failed to update checklist', 'error');
    }
  };

  const handleAddChecklistItem = async () => {
    if (!newChecklistText.trim()) return;
    try {
      await groupPlannerApi.addChecklistItem(groupId, newChecklistText.trim());
      setNewChecklistText('');
      setShowChecklistInput(false);
      queryClient.invalidateQueries({ queryKey: gpKeys.checklist(groupId) });
      showToast('Task added');
    } catch {
      showToast('Failed to add task', 'error');
    }
  };

  const handleVaultUpload = async (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    try {
      await uploadVaultMut.mutateAsync(file);
      showToast('File uploaded');
    } catch (err) {
      showToast(err?.message || 'Upload failed', 'error');
    }
    if (vaultInputRef.current) vaultInputRef.current.value = '';
  };

  const handleVaultDelete = async (docId) => {
    try {
      await deleteVaultMut.mutateAsync(docId);
      showToast('File removed');
    } catch {
      showToast('Failed to delete', 'error');
    }
  };

  return (
    <div className="gp-view">
      <h2 className="gp-section-title">Logistics.</h2>
      <div className="gp-logistics-sections">
        {/* Checklist */}
        <section>
          <div className="gp-section-header">
            <span className="gp-section-label">Team Checklist</span>
            <button className="gp-section-action" onClick={() => setShowChecklistInput(true)}>+ Add Task</button>
          </div>
          {showChecklistInput && (
            <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
              <input type="text" className="gp-modal-input" style={{ marginBottom: 0, flex: 1 }} placeholder="Task description..." value={newChecklistText} onChange={(e) => setNewChecklistText(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleAddChecklistItem()} autoFocus />
              <button className="gp-btn-invite" onClick={handleAddChecklistItem}>Add</button>
            </div>
          )}
          <div className="gp-checklist">
            {checklist.length === 0 ? (
              <div className="gp-empty-agenda">No tasks yet.</div>
            ) : (
              checklist.map((item) => (
                <div key={item.id} className={'gp-checklist-item' + (item.completed ? ' done' : '')} onClick={() => handleToggleChecklist(item.id)}>
                  <div className="gp-checklist-checkbox">{item.completed && <span>&#10003;</span>}</div>
                  <span className="gp-checklist-text">{item.item || item.text}</span>
                  {item.author_name && <span style={{ marginLeft: 'auto', fontSize: 11, color: '#a1a1aa' }}>{item.author_name}</span>}
                </div>
              ))
            )}
          </div>
        </section>

        {/* Vault */}
        <section>
          <div className="gp-section-header">
            <span className="gp-section-label">The Vault</span>
          </div>
          <div className="gp-upload-zone" onClick={() => vaultInputRef.current?.click()}>
            <div className="gp-upload-icon">PDF</div>
            <p className="gp-upload-text">{uploadVaultMut.isPending ? 'Uploading...' : 'Click to Securely Upload'}</p>
            <input ref={vaultInputRef} type="file" accept=".pdf,.jpg,.jpeg,.png,.webp" style={{ display: 'none' }} onChange={handleVaultUpload} />
          </div>
          {vault.length > 0 && (
            <div className="gp-vault-list">
              {vault.map((v) => (
                <div key={v.id} className="gp-vault-item">
                  <div className="gp-vault-left">
                    <span className="gp-vault-icon">{v.mime_type && v.mime_type.includes('pdf') ? 'PDF' : 'IMG'}</span>
                    <div>
                      <p className="gp-vault-name">{v.filename}</p>
                      <p className="gp-vault-meta">{v.uploaded_by_name || 'Member'} &middot; {formatFileSize(v.file_size || 0)}</p>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <button className="gp-place-edit-btn" onClick={() => setPreviewDoc(v)} title="Preview file"><Eye size={14} /></button>
                    {currentUser?.uid && (isAdmin || String(v.uploaded_by) === String(currentUser.uid)) && <button className="gp-place-edit-btn" disabled={deleteVaultMut.isPending} onClick={() => handleVaultDelete(v.id)} title="Remove file" style={{ color: '#ef4444' }}><Trash2 size={14} /></button>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      {/* File Preview Modal */}
      {previewDoc && (
        <div className="gp-modal-overlay" onClick={() => setPreviewDoc(null)}>
          <div className="gp-doc-preview" onClick={(e) => e.stopPropagation()}>
            <div className="gp-doc-preview-header">
              <h3 className="gp-doc-preview-title">{previewDoc.filename}</h3>
              <button className="gp-doc-preview-close" onClick={() => setPreviewDoc(null)}><X size={18} /></button>
            </div>
            <div className="gp-doc-preview-body">
              {previewError ? <p role="alert">{previewError}</p> : !previewBlobUrl ? (
                <p className="gp-doc-preview-placeholder">Loading preview...</p>
              ) : previewDoc.mime_type && previewDoc.mime_type.includes('pdf') ? (
                <iframe src={previewBlobUrl} className="gp-doc-preview-iframe" title={previewDoc.filename} />
              ) : (
                <img src={previewBlobUrl} alt={previewDoc.filename} className="gp-doc-preview-img" />
              )}
            </div>
            <div className="gp-doc-preview-meta">
              <span>Uploaded by {previewDoc.uploaded_by_name || 'Member'}</span>
              <span>{formatFileSize(previewDoc.file_size || 0)}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

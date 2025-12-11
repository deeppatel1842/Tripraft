# White Screen Debug Guide

## Issue: White Screen When Creating Expense

### Problem
User "pateldeep" gets a white screen when trying to add an expense. No backend errors logged.

### Root Cause Analysis

**White screen = Frontend JavaScript error BEFORE API call reaches backend**

This means the error is happening in:
1. React component rendering
2. Form validation
3. Data preparation
4. React Query mutation setup

### Debugging Steps

#### 1. Check Browser Console
**Action:** Open browser DevTools (F12) → Console tab

**Look for:**
- Red error messages
- `Uncaught TypeError`
- `Cannot read property of undefined`
- React error boundaries

**Example Errors:**
```
Uncaught TypeError: Cannot read property 'user_id' of undefined
  at TransactionModal.jsx:45
  at handleSubmit
```

#### 2. Check Network Tab
**Action:** DevTools → Network tab → Try to create expense

**Check:**
- Does API request appear? (Should be `POST /api/expense/expenses`)
- If NO request: Error is in frontend
- If YES but fails: Check response status and error message

#### 3. Add Console Logging

**File:** `ExpenseManager.jsx` (Line ~571)

**Already Added:**
```javascript
const handleSaveTransaction = async (transactionData) => {
  console.log('💾 handleSaveTransaction called:', { 
    mode: state.mode, 
    editing: !!state.editingTransactionId,
    data: transactionData 
  });
  // ... rest of code
}
```

**Check Console:**
- Does this log appear when clicking "Save"?
- If NO: Click handler not attached
- If YES: Error is after this point

#### 4. Check React Query Mutation

**File:** `useExpenseQuery.js` (Line 124)

**The mutation:**
```javascript
export function useCreateExpenseMutation() {
  return useMutation({
    mutationFn: (expenseData) => expenseApi.createExpense(expenseData),
    onMutate: async (newExpense) => { /* optimistic update */ },
    onError: (err, newExpense, context) => {
      console.error('❌ Expense creation failed, rolling back:', err);
      // ... rollback logic
    }
  });
}
```

**Error Handling Added:**
```javascript
try {
  const createResponse = await createExpenseMutation.mutateAsync(expensePayload);
  // ... success
} catch (error) {
  console.error('❌ Expense creation FAILED:', error);
  console.error('Error details:', {
    name: error.name,
    message: error.message,
    stack: error.stack,
    response: error.response?.data
  });
  
  showToast(`Failed to create expense: ${errorMessage}`, 'error');
}
```

### Common Causes & Solutions

#### Cause 1: Missing Member Data
**Symptom:** `Cannot read property 'user_id' of undefined`

**Check:**
```javascript
// In TransactionModal.jsx
console.log('Current members:', members);
console.log('Form data:', formData);
console.log('paidBy:', formData.paidBy);
```

**Fix:** Ensure `activeGroupMembers` is populated in ExpenseManager

#### Cause 2: Permission Issue
**Symptom:** API returns 403 but not caught

**Check Backend Logs:**
```bash
# Look for:
POST /api/expense/expenses - 403 Forbidden
🔍 Permission check: user {user_id} not in group {group_id}
```

**Fix:** Already fixed with `is_user_group_member()` function

#### Cause 3: Invalid Split Data
**Symptom:** `splits` array is empty or malformed

**Check:**
```javascript
console.log('Split calculation:', {
  amount: transactionData.amount,
  splitWith: transactionData.splitWith,
  splits: splits
});
```

**Fix:** Ensure at least one person in `splitWith` array

#### Cause 4: React Query Cache Corruption
**Symptom:** White screen only after certain actions

**Fix:** Clear React Query cache
```javascript
// In browser console:
queryClient.clear();
// Or reload page
```

### Test Checklist

Before testing, verify:
- [ ] User is logged in
- [ ] Group is selected (activeGroupId exists)
- [ ] Group has at least 2 members
- [ ] User is a member of the group (`is_user_group_member()` returns true)
- [ ] Form data is complete (description, amount, category, paidBy, splitWith)

### Testing Script

**Run in Browser Console:**
```javascript
// Check current state
console.log('Auth:', window.expenseApi?.currentUser);
console.log('Active group:', /* get from React DevTools */);
console.log('Members:', /* get from React DevTools */);

// Test API directly
const testExpense = {
  group_id: 'db29f36b-1564-43c1-ac50-709f76a87539',
  description: 'Test expense',
  amount: 10,
  currency: 'USD',
  category: 'Food',
  date: new Date().toISOString().split('T')[0],
  paid_by: 'iJol3n5TFrVHdH79hS32WLCI2EK2', // pateldeep
  split_type: 'EQUAL',
  splits: [
    { user_id: 'R0aghH2MVAh1Pf8CH2UQZN3wIjN2', amount: 5 }, // rdcoding
    { user_id: 'iJol3n5TFrVHdH79hS32WLCI2EK2', amount: 5 }  // pateldeep
  ]
};

// Try creating via API
fetch('http://localhost:5000/api/expense/expenses', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${localStorage.getItem('token')}`
  },
  body: JSON.stringify(testExpense)
})
.then(r => r.json())
.then(data => console.log('✅ Success:', data))
.catch(err => console.error('❌ Failed:', err));
```

### Error Logs to Collect

**From User (pateldeep):**
1. Browser console errors (screenshot)
2. Network tab (screenshot showing failed requests)
3. React DevTools state (if available)

**From Backend:**
```bash
# Check Flask logs for:
grep "POST /api/expense/expenses" logs.txt
grep "403\|404\|500" logs.txt
grep "pateldeep\|iJol3n5TFrVHdH79hS32WLCI2EK2" logs.txt
```

### Expected Console Output (Success)

```
💾 handleSaveTransaction called: {
  mode: "group",
  editing: false,
  data: {
    description: "Dinner",
    amount: 50,
    category: "Food",
    paidBy: "iJol3n5TFrVHdH79hS32WLCI2EK2",
    splitWith: ["R0aghH2MVAh1Pf8CH2UQZN3wIjN2", "iJol3n5TFrVHdH79hS32WLCI2EK2"]
  }
}
📤 Creating expense with optimistic balance updates...
🔍 Looking for old expense: {...}
⚡ Optimistic balances set for CREATE!
✅ Expense created in 245ms
✅ Optimistic state cleared after React Query refetch
✅ All data reloaded in 567ms total
```

### Quick Fix Commands

**If Error Persists:**

1. **Clear all caches:**
```javascript
// Browser console
localStorage.clear();
sessionStorage.clear();
location.reload();
```

2. **Restart backend:**
```powershell
# Kill Flask process
Stop-Process -Name python -Force

# Restart
python run.py
```

3. **Check Firestore rules:**
```javascript
// Ensure user has write access to expense_expenses collection
```

### Next Steps

1. **User provides console screenshot**
2. **Check error message**
3. **Identify root cause**
4. **Apply targeted fix**

---

## Likely Causes (Ordered by Probability)

1. **Permission check failing** (403) - Fixed by `is_user_group_member()`
2. **Member data not loaded** - Fixed by Firestore listeners
3. **React Query optimistic update error** - Fixed by try-catch
4. **Form validation error** - Check TransactionModal validation
5. **Network connectivity** - Check browser Network tab

**Most Likely:** Missing error boundary causing white screen on validation failure.

**Quick Test:** Try creating expense as owner (rdcoding1842). If it works, permission issue for pateldeep.

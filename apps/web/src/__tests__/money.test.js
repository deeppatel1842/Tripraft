// Purpose: Regression tests for money, including success and failure behavior.
import { equalSplits, expensePayload, settlementCap, formatMoney } from '../utils/money';
const payer = '01912345-aaaa-7000-8000-000000000001';
const other = '01912345-aaaa-7000-8000-000000000002';
const third = '01912345-aaaa-7000-8000-000000000003';
const data = { amount: 10, description: 'Dinner', category: 'Food', expense_date: '2026-10-03', paidBy: payer, splitWith: [payer, other, third] };
it('allocates cents exactly while keeping UUID participants and deduplicating them', () => {
  const splits = equalSplits(10, [payer, other, third, payer]);
  expect(splits.map(s => s.amount)).toEqual([3.34, 3.33, 3.33]);
  expect(splits.reduce((sum,s) => sum + Math.round(s.amount*100),0)).toBe(1000);
  expect(splits.map(s => s.user_id)).toEqual([payer,other,third]);
});
it.each([0,-1,NaN,Infinity])('rejects an invalid amount %s', amount => expect(() => equalSplits(amount,[payer])).toThrow());
it('omits an unchanged payer from an edit without altering UUIDs', () => {
  const result = expensePayload(data,{groupId:'group',editingExpense:{amount:10, paid_by:payer,split_type:'equal'}});
  expect(result).not.toHaveProperty('paid_by');
  expect(result).not.toHaveProperty('group_id');
  expect(result.splits[0].user_id).toBe(payer);
});
it.each(['exact','percentage','shares'])('preserves saved %s split fields on metadata edits', split_type => {
  const result = expensePayload({...data,description:'Updated'}, {editingExpense:{amount:10,paid_by:payer,split_type}});
  expect(result).toEqual({description:'Updated',category:'Food',expense_date:'2026-10-03'});
  expect(() => expensePayload({...data,amount:12}, {editingExpense:{amount:10,paid_by:payer,split_type}})).toThrow(/preserves custom/);
});
it('supports changing the payer without rebuilding custom shares', () => {
  const result=expensePayload({...data,paidBy:other},{editingExpense:{amount:10,paid_by:payer,split_type:'exact'}});
  expect(result.paid_by).toBe(other);
  expect(result).not.toHaveProperty('splits');
});
it('caps settlement by both payer debt and recipient credit', () => {
  const balances=[{user_id:payer,net_balance:-20},{user_id:other,net_balance:8}];
  expect(settlementCap(balances,payer,other)).toBe(8);
  expect(settlementCap(balances,other,payer)).toBe(0);
  expect(settlementCap(balances,payer,payer)).toBe(0);
});
it('formats non-USD amounts and safely handles invalid currency codes', () => {
  expect(formatMoney(12,'EUR')).toBe('€12.00');
  expect(formatMoney(12,'INVALID')).toBe('12.00 INVALID');
});

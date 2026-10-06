// Purpose: Regression tests for routes, including success and failure behavior.
import React from 'react';import {render,screen,waitFor} from '@testing-library/react';import {MemoryRouter,Routes,Route} from 'react-router-dom';
jest.mock('../context/AuthContext',()=>({useAuth:jest.fn()}));
jest.mock('../pages/InvitationAccept',()=>({__esModule:true,default:()=> <div>Expense invitation</div>}));
jest.mock('../features/trips/jsx/InvitationAcceptPage',()=>({__esModule:true,default:()=> <div>Group invitation</div>}));
jest.mock('../services/expenseApi',()=>({__esModule:true,default:{getInvitationDetails:jest.fn()}}));
jest.mock('../services/groupPlannerApi',()=>({__esModule:true,default:{getInvitationDetails:jest.fn()}}));
import {useAuth} from '../context/AuthContext';import Smart from '../pages/SmartInvitationHandler';import Analytics from '../pages/Analytics';import ExpenseAnalytics from '../pages/ExpenseAnalytics';import expense from '../services/expenseApi';import group from '../services/groupPlannerApi';
it.each([['/invitation/uuid','Expense invitation'],['/invitations/uuid','Group invitation'],['/accept-invitation?id=uuid&type=expense','Expense invitation']])('routes %s to its matching flow without authentication probes',async(url,text)=>{
 render(<MemoryRouter initialEntries={[url]}><Routes><Route path="/invitation/:invitationId" element={<Smart/>}/><Route path="/invitations/:invitationId" element={<Smart/>}/><Route path="/accept-invitation" element={<Smart/>}/></Routes></MemoryRouter>);
 expect(await screen.findByText(text)).toBeInTheDocument();expect(expense.getInvitationDetails).not.toHaveBeenCalled();expect(group.getInvitationDetails).not.toHaveBeenCalled();
});
it.each([Analytics,ExpenseAnalytics])('renders access denial without crashing for a non-admin',Component=>{useAuth.mockReturnValue({currentUser:{uid:'uuid',is_admin:false},loading:false});render(<MemoryRouter><Component/></MemoryRouter>);expect(screen.getByText('Access denied')).toBeInTheDocument();expect(document.querySelector('iframe')).toBeNull();});
it('shows unavailable analytics to admins without calling an absent endpoint',()=>{useAuth.mockReturnValue({currentUser:{is_admin:true},loading:false});render(<MemoryRouter><Analytics/></MemoryRouter>);expect(screen.getByText(/not available in this build/)).toBeInTheDocument();});

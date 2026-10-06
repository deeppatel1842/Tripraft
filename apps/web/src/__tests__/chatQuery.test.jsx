// Purpose: Regression tests for chat Query, including success and failure behavior.
import React from 'react';import {renderHook,act,waitFor} from '@testing-library/react';import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
jest.mock('../services/chatApi',()=>({__esModule:true,default:{sendMessage:jest.fn()}}));jest.mock('../context/AuthContext',()=>({useAuth:()=>({currentUser:{uid:'0190-user-uuid'}})}));
import chat from '../services/chatApi';import {useSendMessage,chatKeys} from '../hooks/useChatQuery';import {mergeMessage,pageMessages} from '../lib/chatCache';
let client,wrapper;beforeEach(()=>{client=new QueryClient({defaultOptions:{queries:{retry:false},mutations:{retry:false}}});wrapper=({children})=><QueryClientProvider client={client}>{children}</QueryClientProvider>;client.setQueryData(chatKeys.messages('group'),{pages:[{data:{messages:[{id:'old',content:'History'}]}}],pageParams:[undefined]});});afterEach(()=>client.clear());
it('removes only a failed optimistic message and keeps concurrent incoming messages',async()=>{
 let reject;chat.sendMessage.mockReturnValue(new Promise((_r,j)=>{reject=j;}));const {result}=renderHook(()=>useSendMessage('group'),{wrapper});
 act(()=>result.current.mutate({content:'Outgoing'}));await waitFor(()=>expect(chat.sendMessage).toHaveBeenCalled());
 const pending=pageMessages(client.getQueryData(chatKeys.messages('group')).pages[0])[0];expect(pending.id).toMatch(/^temp-/);expect(pending.sender_id).toBe('0190-user-uuid');
 client.setQueryData(chatKeys.messages('group'),old=>mergeMessage(old,{id:'incoming',content:'Another member'}));
 await act(async()=>reject(new Error('Offline')));await waitFor(()=>expect(result.current.isError).toBe(true));
 expect(pageMessages(client.getQueryData(chatKeys.messages('group')).pages[0]).map(m=>m.id)).toEqual(['incoming','old']);
});
it('replaces the optimistic send with the server UUID without duplicating a socket echo',async()=>{
 let resolve;chat.sendMessage.mockReturnValue(new Promise(r=>{resolve=r;}));const {result}=renderHook(()=>useSendMessage('group'),{wrapper});act(()=>result.current.mutate({content:'Hello'}));await waitFor(()=>expect(chat.sendMessage).toHaveBeenCalled());
 const message={id:'0190-message-uuid',content:'Hello',sender_id:'0190-user-uuid'};client.setQueryData(chatKeys.messages('group'),old=>mergeMessage(old,message));await act(async()=>resolve({success:true,data:{message}}));await waitFor(()=>expect(result.current.isSuccess).toBe(true));
 expect(pageMessages(client.getQueryData(chatKeys.messages('group')).pages[0]).map(m=>m.id)).toEqual(['0190-message-uuid','old']);
});
it('deduplicates across all pages, including flat and enveloped pages',()=>{const cache={pages:[{messages:[{id:'new'}]},{data:{messages:[{id:'older'}]}}]};expect(mergeMessage(cache,{id:'older'})).toBe(cache);});
it.each(['success','failure'])('updates the original group after a pending send finishes with %s following a group switch',async outcome=>{
 let resolve,reject;chat.sendMessage.mockReturnValue(new Promise((r,j)=>{resolve=r;reject=j;}));
 const other={pages:[{messages:[{id:'other-history',content:'Other group'}]}],pageParams:[undefined]};
 client.setQueryData(chatKeys.messages('other-group'),other);
 const {result,rerender}=renderHook(({id})=>useSendMessage(id),{wrapper,initialProps:{id:'group'}});
 act(()=>result.current.mutate({content:'Original group send'}));await waitFor(()=>expect(chat.sendMessage).toHaveBeenCalled());
 rerender({id:'other-group'});
 const message={id:'server-uuid',group_id:'group',content:'Original group send'};
 await act(async()=>{if(outcome==='success')resolve({data:{message}});else reject(new Error('Offline'));});
 await waitFor(()=>expect(pageMessages(client.getQueryData(chatKeys.messages('group')).pages[0]).some(m=>m._optimistic)).toBe(false));
 expect(pageMessages(client.getQueryData(chatKeys.messages('other-group')).pages[0])).toEqual(other.pages[0].messages);
 expect(pageMessages(client.getQueryData(chatKeys.messages('group')).pages[0]).some(m=>m.id==='server-uuid')).toBe(outcome==='success');
});

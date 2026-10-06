// Purpose: Regression tests for chat Socket, including success and failure behavior.
import React from 'react';import {renderHook,act,waitFor} from '@testing-library/react';import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
jest.mock('../config/globalConfig',()=>({__esModule:true,default:{API_BASE_URL:'http://localhost:5000/api'}}));
jest.mock('../services/sqlAuthService',()=>({__esModule:true,default:{getIdToken:jest.fn().mockResolvedValue(null)}}));
jest.mock('../hooks/useChatQuery',()=>({chatKeys:{messages:id=>['chat','messages',id],unread:id=>['chat','unread',id]}}));
jest.mock('socket.io-client',()=>({io:jest.fn()}));
import {io} from 'socket.io-client';import useChatSocket from '../hooks/useChatSocket';import {pageMessages} from '../lib/chatCache';
let client,wrapper,socket,events;beforeEach(()=>{client=new QueryClient({defaultOptions:{queries:{retry:false}}});wrapper=({children})=><QueryClientProvider client={client}>{children}</QueryClientProvider>;events={};socket={on:jest.fn((name,handler)=>{events[name]=handler;}),emit:jest.fn(),disconnect:jest.fn(),io:{opts:{reconnection:true}}};io.mockReturnValue(socket);});afterEach(()=>client.clear());
it('connects with UUID user and group IDs using cookie credentials',async()=>{
 const {result}=renderHook(()=>useChatSocket('0190-group-uuid','0190-user-uuid'),{wrapper});await waitFor(()=>expect(io).toHaveBeenCalled());expect(io.mock.calls[0]).toEqual(['http://localhost:5000',expect.objectContaining({withCredentials:true})]);act(()=>events.connect());expect(result.current.connected).toBe(true);expect(socket.emit).toHaveBeenCalledWith('join_group',{group_id:'0190-group-uuid'});
});
it('surfaces authentication rejection and stops reconnection attempts',async()=>{const {result}=renderHook(()=>useChatSocket('group','user-uuid'),{wrapper});await waitFor(()=>expect(io).toHaveBeenCalled());act(()=>events.connect_error(new Error('Unauthorized 401')));expect(result.current.connectionError).toBe('Unauthorized 401');expect(socket.io.opts.reconnection).toBe(false);expect(socket.disconnect).toHaveBeenCalled();});
it('keeps messages from the current user sent on another device and deduplicates echoes',async()=>{client.setQueryData(['chat','messages','group'],{pages:[{data:{messages:[]}}],pageParams:[undefined]});renderHook(()=>useChatSocket('group','user-uuid'),{wrapper});await waitFor(()=>expect(io).toHaveBeenCalled());const msg={id:'message-uuid',sender_id:'user-uuid',content:'Other device'};act(()=>{events['chat:message'](msg);events['chat:message'](msg);});expect(pageMessages(client.getQueryData(['chat','messages','group']).pages[0])).toEqual([msg]);});
it('retains a same-text message from another device while a local send is pending',async()=>{
 const pending={id:'temp-local',sender_id:'user-uuid',content:'Hello',_optimistic:true};
 client.setQueryData(['chat','messages','group'],{pages:[{data:{messages:[pending]}}],pageParams:[undefined]});
 renderHook(()=>useChatSocket('group','user-uuid'),{wrapper});await waitFor(()=>expect(io).toHaveBeenCalled());
 const incoming={id:'other-device-uuid',sender_id:'user-uuid',content:'Hello'};
 act(()=>{events['chat:message'](incoming);events['chat:message'](incoming);});
 expect(pageMessages(client.getQueryData(['chat','messages','group']).pages[0])).toEqual([incoming,pending]);
});
it('throttles read receipts and excludes optimistic identifiers',async()=>{const {result}=renderHook(()=>useChatSocket('group','user-uuid'),{wrapper});await waitFor(()=>expect(io).toHaveBeenCalled());act(()=>{result.current.emitRead('message-uuid');result.current.emitRead('message-uuid');result.current.emitRead('temp-uuid');});expect(socket.emit.mock.calls.filter(([name])=>name==='chat:read')).toEqual([['chat:read',{group_id:'group',message_id:'message-uuid'}]]);});

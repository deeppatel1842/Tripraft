// Purpose: Regression tests for auth Service, including success and failure behavior.
jest.mock('../config/globalConfig',()=>({__esModule:true,default:{API_BASE_URL:'http://localhost/api',ENDPOINTS:{AUTH:'/v1/auth'},STORAGE_KEYS:{ACCESS_TOKEN:'accessToken',REFRESH_TOKEN:'refreshToken',CURRENT_USER:'currentUser'}}}));
import auth from '../services/sqlAuthService';
const response=(status,data)=>({ok:status<400,status,json:async()=>data});
beforeEach(()=>{localStorage.clear();auth._clearAuth();auth._isRefreshing=false;auth._refreshPromise=null;global.fetch=jest.fn();document.cookie='csrf_token=csrf; path=/';});
it('refreshes with only cookies when there is no readable access token',async()=>{
 fetch.mockResolvedValue(response(200,{success:true,data:{}}));await expect(auth.refreshAccessToken()).resolves.toMatchObject({success:true});
 expect(fetch.mock.calls[0][1]).toMatchObject({credentials:'include',headers:{'X-CSRF-Token':'csrf'},body:'{}'});
 expect(await auth.getIdToken()).toBeNull();expect(auth.accessToken).toBe('__cookie__');
});
it('shares a single refresh request across concurrent callers',async()=>{
 let resolve;fetch.mockReturnValue(new Promise(r=>{resolve=r;}));const a=auth.refreshAccessToken();const b=auth.refreshAccessToken();
 resolve(response(200,{data:{}}));await Promise.all([a,b]);expect(fetch).toHaveBeenCalledTimes(1);
});
it.each([500,503])('keeps the session after refresh status %s',async status=>{
 auth._saveAuth(null,null,{id:'uuid'});fetch.mockResolvedValue(response(status,{}));await auth.refreshAccessToken();expect(auth.currentUser).toEqual({id:'uuid'});
});
it('keeps the session after transient network failure',async()=>{
 auth._saveAuth(null,null,{id:'uuid'});fetch.mockRejectedValue(new Error('Offline'));await auth.refreshAccessToken();expect(auth.currentUser.id).toBe('uuid');
});
it.each([401,403])('clears a rejected session on refresh status %s',async status=>{
 auth._saveAuth(null,null,{id:'uuid'});fetch.mockResolvedValue(response(status,{}));await auth.refreshAccessToken();expect(auth.currentUser).toBeNull();expect(localStorage.getItem('currentUser')).toBeNull();
});
it('clears authentication even when a rejection contains HTML instead of JSON',async()=>{
 auth._saveAuth(null,null,{id:'uuid'});fetch.mockResolvedValue({ok:false,status:401,json:async()=>{throw new SyntaxError('HTML');}});await auth.refreshAccessToken();expect(auth.currentUser).toBeNull();
});
it('sends CSRF on logout and keeps tokens out of local storage',async()=>{
 auth._saveAuth(null,null,{id:'uuid'});expect(localStorage.getItem('accessToken')).toBeNull();expect(localStorage.getItem('refreshToken')).toBeNull();fetch.mockResolvedValue(response(200,{}));await auth.signOut();expect(fetch.mock.calls[0][1].headers['X-CSRF-Token']).toBe('csrf');
});
it('uses server administrator and verification fields without inventing verification',()=>{
 const user=auth._createUserObject({id:'0190-uuid',email:'test@example.com',is_admin:true},null);expect(user.uid).toBe('0190-uuid');expect(user.is_admin).toBe(true);expect(user.emailVerified).toBe(false);
});
it('normalizes login email before sending it to the backend',async()=>{
 fetch.mockResolvedValue(response(200,{data:{user:{id:'uuid',email:'person@example.com'}}}));
 await expect(auth.signInWithEmail('  PERSON@EXAMPLE.COM  ','password')).resolves.toMatchObject({success:true});
 expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({email:'person@example.com',password:'password'});
});

// Purpose: Regression tests for api Client, including success and failure behavior.
jest.mock('../config/globalConfig',()=>({__esModule:true,default:{API_BASE_URL:'http://localhost/api',API_TIMEOUT:1000,API_MAX_RETRIES:2,RETRY_BACKOFF_BASE_MS:1}}));
jest.mock('../services/sqlAuthService',()=>({__esModule:true,default:{getIdToken:jest.fn(),refreshAccessToken:jest.fn()}}));
jest.mock('../utils/apiLogger',()=>({__esModule:true,default:{logError:jest.fn()}}));
import { APIClient } from '../utils/apiClient';
import auth from '../services/sqlAuthService';
const response=(status,body='',type='application/json')=>({ok:status>=200&&status<300,status,headers:{get:()=>type},text:async()=>body,blob:async()=>new Blob(['preview'])});
let client;
beforeEach(()=>{client=new APIClient();global.fetch=jest.fn();auth.getIdToken.mockResolvedValue(null);auth.refreshAccessToken.mockResolvedValue({success:true});document.cookie='csrf_token=test-csrf; path=/';});
it('accepts a successful empty DELETE and sends cookie credentials and CSRF',async()=>{
 fetch.mockResolvedValue(response(204));
 await expect(client.delete('/v1/groups/uuid')).resolves.toBeNull();
 expect(fetch.mock.calls[0][1]).toMatchObject({method:'DELETE',credentials:'include',headers:{'X-CSRF-Token':'test-csrf'}});
});
it('preserves non-JSON authentication errors and refreshes only once',async()=>{
 fetch.mockResolvedValue(response(401,'<html>Denied</html>','text/html'));
 await expect(client.get('/v1/private')).rejects.toMatchObject({status:401});
 expect(auth.refreshAccessToken).toHaveBeenCalledTimes(1);expect(fetch).toHaveBeenCalledTimes(2);
});
it.each([401,403,500])('preserves HTTP %s when an error body is mislabeled as JSON',async status=>{
 fetch.mockResolvedValue(response(status,'<html>Unavailable</html>','application/json'));
 await expect(client.post('/v1/expenses',{})).rejects.toMatchObject({status});
 expect(fetch).toHaveBeenCalledTimes(status===401 ? 2 : 1);
 expect(auth.refreshAccessToken).toHaveBeenCalledTimes(status===401 ? 1 : 0);
});
it('refreshes cookie auth once and repeats the original request',async()=>{
 fetch.mockResolvedValueOnce(response(401,'{}')).mockResolvedValueOnce(response(200,'{"success":true,"data":{"id":"uuid"}}'));
 await expect(client.post('/v1/groups',{name:'Trip'})).resolves.toMatchObject({data:{id:'uuid'}});
 expect(fetch.mock.calls[1][1].body).toBe('{"name":"Trip"}');
 expect(auth.refreshAccessToken).toHaveBeenCalledTimes(1);
});
it('never retries a money POST after a dropped response',async()=>{
 fetch.mockRejectedValue(new TypeError('Connection lost'));
 await expect(client.post('/v1/expenses',{amount:10})).rejects.toThrow('Connection lost');
 expect(fetch).toHaveBeenCalledTimes(1);
});
it('never retries a money POST after server failure',async()=>{
 fetch.mockResolvedValue(response(500,'{"message":"Unavailable"}'));
 await expect(client.post('/v1/settlements',{})).rejects.toMatchObject({status:500});expect(fetch).toHaveBeenCalledTimes(1);
});
it('retries GET server failures and returns the envelope unchanged',async()=>{
 fetch.mockResolvedValueOnce(response(503,'{}')).mockResolvedValueOnce(response(200,'{"success":true,"data":[]}'));
 await expect(client.get('/v1/places')).resolves.toEqual({success:true,data:[]});expect(fetch).toHaveBeenCalledTimes(2);
});
it('downloads a cookie-authenticated blob',async()=>{fetch.mockResolvedValue(response(200));await expect(client.get('/v1/vault/uuid/download',{responseType:'blob'})).resolves.toBeInstanceOf(Blob);});
it('stops an externally cancelled request without retries',async()=>{
 const controller=new AbortController();controller.abort();
 fetch.mockImplementation((_url,opts)=> opts.signal.aborted ? Promise.reject(new DOMException('Aborted','AbortError')) : Promise.resolve(response(200)));
 await expect(client.get('/v1/places',{signal:controller.signal})).rejects.toThrow('Request aborted');expect(fetch).toHaveBeenCalledTimes(1);
});

// Purpose: Regression tests for service Contracts, including success and failure behavior.
jest.mock('../config/globalConfig',()=>({__esModule:true,default:{ENDPOINTS:{TRIP_PLANNER:'/v1/trip-planner',PLACE_SEARCH:'/v1/places'},TRIP_DEFAULT_DAYS:3,TRIP_DEFAULT_PACING:'M',CITY_SEARCH_LIMIT:10,PLACE_SEARCH_DEFAULT_LIMIT:500,PLACE_SEARCH_DEFAULT_SORT_BY:'rank_score',PLACE_SEARCH_DEFAULT_SORT_ORDER:'desc',AUTOCOMPLETE_MIN_CHARS:2,AUTOCOMPLETE_DEFAULT_LIMIT:10}}));
jest.mock('../utils/apiClient',()=>({__esModule:true,default:{get:jest.fn(),post:jest.fn()}}));
jest.mock('../utils/apiLogger',()=>({__esModule:true,default:{logSuccess:jest.fn(),logWarning:jest.fn(),logError:jest.fn()}}));
import api from '../utils/apiClient';import trip from '../services/tripPlannerService';import places from '../services/placeSearchService';import {placeRating} from '../utils/placeRating';import {validCoordinates} from '../utils/coordinates';
import chat from '../services/chatApi';
it.each([['@SCOUT plan a trip',90000],['@Crew add a poll',90000],['Hello',undefined]])('sets the expected timeout for %s',async(content,timeout)=>{
 await chat.sendMessage('group-uuid',{content});
 expect(api.post).toHaveBeenCalledWith(expect.stringContaining('/groups/group-uuid/messages'),{content},{timeout});
});
it('renders trip data from the actual response envelope and preserves place metadata',async()=>{
 api.post.mockResolvedValue({success:true,data:{title:'Paris',itinerary:[{day:1,stops:[{name:'Museum'}]}],highRankedPlaces:[{id:11,name:'Museum',rank_score:9.8,latitude:0,longitude:2}],city:'Paris'},meta:{count:1}});
 const result=await trip.generateTrip({city:'Paris',days:2,exclude:'ignored'});expect(result.title).toBe('Paris');expect(result.itinerary[0].stops[0].name).toBe('Museum');expect(result.highRankedPlaces[0]).toMatchObject({id:11,rating:4.9,latitude:0});
 expect(api.post).toHaveBeenCalledWith('/v1/trip-planner/generate',{city:'Paris',days:2,pacing:'M'});
});
it('unwraps city searches and lists',async()=>{api.get.mockResolvedValue({success:true,data:{cities:['Paris']}});await expect(trip.searchCities('Pa')).resolves.toEqual(['Paris']);await expect(trip.getCities()).resolves.toEqual(['Paris']);});
it('unwraps real search results and autocomplete without fabricating a fallback',async()=>{api.get.mockResolvedValue({success:true,data:{places:[],total:0}});await expect(places.searchPlaces('Paris')).resolves.toMatchObject({places:[],total:0});api.get.mockResolvedValue({data:{suggestions:['Paris']}});await expect(places.getAutocompleteSuggestions('Pa')).resolves.toEqual(['Paris']);api.get.mockRejectedValue(new Error('Offline'));await expect(places.searchPlaces('Paris')).rejects.toThrow('Offline');});
it.each([[-2,0],[9.8,4.9],[10,5],[100,5],[undefined,0]])('normalizes rank %s into safe rating %s',(rank_score,rating)=>expect(placeRating({rank_score})).toBe(rating));
it.each([[0,0,true],[0,2,true],[2,0,true],[null,2,false],['',2,false],[91,0,false],[0,181,false],['bad',0,false]])('validates map coordinates %s, %s',(latitude,longitude,expected)=>expect(validCoordinates(latitude,longitude)).toBe(expected));

"""
Events Service for Group Planner
Fetches events from Ticketmaster API for travel destinations

Ticketmaster Discovery API: https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# Ticketmaster API Configuration
# Get API key from environment variables
TICKETMASTER_API_KEY = os.environ.get(
    'TICKETMASTER_CONSUMER_API_KEY',
    os.environ.get('TICKETMASTER_API_KEY', '')
)
TICKETMASTER_BASE_URL = 'https://app.ticketmaster.com/discovery/v2'


class EventsService:
    """Service for fetching events from Ticketmaster API"""
    
    @staticmethod
    def get_destination_events(
        destination: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 20
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Get events for a destination from Ticketmaster API
        
        Args:
            destination: City or location name (e.g., "Seattle", "New York")
            start_date: Optional start date (ISO format)
            end_date: Optional end date (ISO format)
            category: Optional category filter (music, sports, arts, family)
            limit: Maximum number of events to return (default 20, max 50)
            
        Returns:
            Tuple of (success, events_list/error)
        """
        try:
            # Check if API key is configured
            if not TICKETMASTER_API_KEY:
                logger.warning("Ticketmaster API key not configured")
                return True, {
                    'events': [],
                    'total': 0,
                    'message': 'Events API not configured. Add TICKETMASTER_API_KEY to enable events.'
                }
            
            # Build API request parameters
            params = {
                'apikey': TICKETMASTER_API_KEY,
                'size': min(limit, 50),  # Ticketmaster max is 200, but we limit to 50
                'sort': 'date,asc'
            }
            
            # Handle destination with country-specific logic
            city, country_code = EventsService._extract_city_and_country(destination)
            params['city'] = city
            
            if country_code:
                params['countryCode'] = country_code
                logger.info(f"Using country code: {country_code} for destination: {destination}")
            else:
                # Default to US if no country specified
                params['countryCode'] = 'US'
            
            # Add date filters if provided
            if start_date:
                try:
                    dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    params['startDateTime'] = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                except:
                    pass
            else:
                # Default to events from today
                params['startDateTime'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
            
            if end_date:
                try:
                    dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    params['endDateTime'] = dt.strftime('%Y-%m-%dT23:59:59Z')
                except:
                    pass
            
            # Add category/segment filter
            if category:
                segment_mapping = {
                    'music': 'KZFzniwnSyZfZ7v7nJ',
                    'sports': 'KZFzniwnSyZfZ7v7nE',
                    'arts': 'KZFzniwnSyZfZ7v7na',
                    'family': 'KZFzniwnSyZfZ7v7n1',
                    'film': 'KZFzniwnSyZfZ7v7nn',
                    'miscellaneous': 'KZFzniwnSyZfZ7v7n1'
                }
                if category.lower() in segment_mapping:
                    params['segmentId'] = segment_mapping[category.lower()]
            
            # Make API request
            logger.info(f"Fetching events for: {destination} (city: {city}, country: {country_code or 'US'})")
            response = requests.get(
                f'{TICKETMASTER_BASE_URL}/events.json',
                params=params,
                timeout=10
            )
            
            if response.status_code == 401:
                logger.error("Ticketmaster API key invalid")
                return True, {
                    'events': [],
                    'total': 0,
                    'message': 'Invalid API key. Please update TICKETMASTER_API_KEY.'
                }
            
            if response.status_code == 429:
                logger.warning("Ticketmaster API rate limit exceeded")
                return True, {
                    'events': [],
                    'total': 0,
                    'message': 'Rate limit exceeded. Try again later.'
                }
            
            response.raise_for_status()
            data = response.json()
            
            # Parse events from response
            events = EventsService._parse_events(data)
            
            # Get pagination info
            page_info = data.get('page', {})
            total_elements = page_info.get('totalElements', len(events))
            
            return True, {
                'events': events,
                'total': total_elements,
                'destination': destination
            }
            
        except requests.exceptions.Timeout:
            logger.error("Ticketmaster API timeout")
            return True, {
                'events': [],
                'total': 0,
                'message': 'Request timed out. Try again.'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Ticketmaster API error: {str(e)}")
            return True, {
                'events': [],
                'total': 0,
                'message': f'API error: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Events service error: {str(e)}")
            return False, {'error': f'Failed to fetch events: {str(e)}'}
    
    @staticmethod
    def _extract_city_and_country(destination: str) -> tuple:
        """Extract city name and country code from destination string"""
        destination_lower = destination.lower()
        
        # Define country mappings
        country_mappings = {
            'japan': 'JP',
            'jp': 'JP', 
            'france': 'FR',
            'fr': 'FR',
            'uk': 'GB',
            'united kingdom': 'GB',
            'gb': 'GB',
            'usa': 'US',
            'united states': 'US',
            'us': 'US',
            'canada': 'CA',
            'ca': 'CA',
            'australia': 'AU',
            'au': 'AU',
            'germany': 'DE',
            'de': 'DE',
            'italy': 'IT',
            'it': 'IT',
            'spain': 'ES',
            'es': 'ES'
        }
        
        # Extract city (first part before comma)
        city = destination.split(',')[0].strip()
        
        # Detect country from full destination string
        country_code = None
        for country, code in country_mappings.items():
            if country in destination_lower:
                country_code = code
                break
                
        # Special city-country mappings
        if 'tokyo' in destination_lower:
            city = 'Tokyo'
            country_code = 'JP'
        elif 'paris' in destination_lower:
            city = 'Paris' 
            country_code = 'FR'
        elif 'london' in destination_lower:
            city = 'London'
            country_code = 'GB'
        elif 'new york' in destination_lower:
            city = 'New York'
            country_code = 'US'
        elif 'los angeles' in destination_lower:
            city = 'Los Angeles'
            country_code = 'US'
            
        return city, country_code
    
    @staticmethod
    def _extract_city(destination: str) -> str:
        """Extract city name from destination string (legacy method)"""
        # Keep for backwards compatibility
        city, _ = EventsService._extract_city_and_country(destination)
        return city
    
    @staticmethod
    def _parse_events(data: Dict) -> List[Dict]:
        """Parse Ticketmaster API response into event list"""
        events = []
        
        # Events are in _embedded.events
        embedded = data.get('_embedded', {})
        raw_events = embedded.get('events', [])
        
        for event in raw_events:
            try:
                # Get venue info
                venues = event.get('_embedded', {}).get('venues', [])
                venue = venues[0] if venues else {}
                venue_name = venue.get('name', '')
                venue_address = venue.get('address', {}).get('line1', '')
                venue_city = venue.get('city', {}).get('name', '')
                venue_location = venue.get('location', {})
                
                # Get date/time
                dates = event.get('dates', {})
                start = dates.get('start', {})
                event_date = start.get('localDate', '')
                event_time = start.get('localTime', '')
                
                # Get images
                images = event.get('images', [])
                image_url = None
                for img in images:
                    if img.get('width', 0) >= 300:
                        image_url = img.get('url')
                        break
                if not image_url and images:
                    image_url = images[0].get('url')
                
                # Get price range
                price_ranges = event.get('priceRanges', [])
                min_price = None
                max_price = None
                if price_ranges:
                    min_price = price_ranges[0].get('min')
                    max_price = price_ranges[0].get('max')
                
                # Get category/segment
                classifications = event.get('classifications', [])
                category = ''
                if classifications:
                    segment = classifications[0].get('segment', {})
                    genre = classifications[0].get('genre', {})
                    category = segment.get('name', genre.get('name', ''))
                
                parsed_event = {
                    'id': f"tm_{event.get('id', '')}",
                    'name': event.get('name', ''),
                    'description': event.get('info', event.get('pleaseNote', '')),
                    'url': event.get('url', ''),
                    'image_url': image_url,
                    'date': event_date,
                    'time': event_time,
                    'venue': venue_name,
                    'address': f"{venue_address}, {venue_city}" if venue_address else venue_city,
                    'latitude': float(venue_location.get('latitude')) if venue_location.get('latitude') else None,
                    'longitude': float(venue_location.get('longitude')) if venue_location.get('longitude') else None,
                    'category': 'event',
                    'event_type': category,
                    'min_price': min_price,
                    'max_price': max_price,
                    'source': 'ticketmaster'
                }
                
                events.append(parsed_event)
                
            except Exception as e:
                logger.warning(f"Failed to parse event: {str(e)}")
                continue
        
        return events


# Singleton instance
events_service = EventsService()

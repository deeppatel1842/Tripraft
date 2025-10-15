import os
import sys
from flask import Flask, jsonify, request, g
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, auth
from functools import wraps
from dotenv import load_dotenv
from config import Config

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Configure CORS with more explicit settings
CORS(app, 
     origins=Config.CORS_ORIGINS,
     supports_credentials=Config.CORS_ALLOW_CREDENTIALS,
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization'],
     expose_headers=['Content-Type'],
     max_age=3600
)

# Initialize Firebase Admin
try:
    service_account_info = {
        "type": os.getenv("FIREBASE_TYPE"),
        "project_id": os.getenv("FIREBASE_PROJECT_ID"),
        "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
        "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),
        "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
        "client_id": os.getenv("FIREBASE_CLIENT_ID"),
        "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
        "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
        "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
        "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL")
    }
    
    cred = credentials.Certificate(service_account_info)
    firebase_admin.initialize_app(cred)
    
except Exception as e:
    print(f"Error initializing Firebase Admin: {e}")


# =============================================================================
# MIDDLEWARE
# =============================================================================

def login_required(f):
    """Authentication middleware decorator."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        id_token = None
        if auth_header and auth_header.startswith('Bearer '):
            id_token = auth_header.split('Bearer ')[1]

        if not id_token:
            return jsonify({'error': 'Authorization token is missing'}), 401

        try:
            decoded_token = auth.verify_id_token(id_token)
            g.user = decoded_token
        except Exception as e:
            return jsonify({'error': 'Invalid or expired token', 'detail': str(e)}), 401
        
        return f(*args, **kwargs)
    return decorated_function


# =============================================================================
# ROUTES
# =============================================================================

@app.route(f'{Config.API_PREFIX}/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'app_name': Config.APP_NAME
    }), 200


@app.route(f'{Config.API_PREFIX}/config', methods=['GET'])
def get_config():
    """Returns public configuration for frontend."""
    return jsonify(Config.get_public_config()), 200

@app.route('/api/auth/verify', methods=['POST'])
def verify_token():
    """Verifies a Firebase ID token and returns user info."""
    try:
        data = request.get_json()
        id_token = data.get('idToken')

        if not id_token:
            return jsonify({'error': 'ID token is required'}), 400

        decoded_token = auth.verify_id_token(id_token)
        
        uid = decoded_token['uid']
        user_info = {
            'uid': uid,
            'email': decoded_token.get('email'),
            'name': decoded_token.get('name'),
            'picture': decoded_token.get('picture'),
            'email_verified': decoded_token.get('email_verified', False)
        }
        
        return jsonify({'success': True, 'user': user_info}), 200

    except Exception as e:
        return jsonify({'error': 'Token verification failed', 'detail': str(e)}), 401


@app.route('/api/profile', methods=['GET'])
@login_required # <-- This is your middleware in action!
def get_profile():
    user_from_token = g.user
    
    return jsonify({
        'message': 'This is a protected route!',
        'user_uid': user_from_token['uid'],
        'user_email': user_from_token.get('email')
    }), 200


# --- Places API ---
@app.route('/api/places/search', methods=['GET'])
def search_places():
    """
    Search for top places/attractions.
    Query params: city (required)
    
    Flow:
    1. Call main_engine.get_places_for_ui() directly
    2. It handles cache hits (from existing hubs) and cache misses (new searches)
    3. Returns processed data with distances calculated relative to queried city
    4. No JSON files needed - data flows directly to frontend
    """
    try:
        import sys
        import os
        
        # Add main_engine to path and import using importlib
        import importlib.util
        
        backend_path = os.path.dirname(__file__)
        main_engine_file = os.path.join(backend_path, 'main_engine', 'main_engine.py')
        
        # Load main_engine module
        spec = importlib.util.spec_from_file_location("main_engine_module", main_engine_file)
        main_engine = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main_engine)
        get_places_for_ui = main_engine.get_places_for_ui
        
        city = request.args.get('city', '').strip()
        if not city:
            return jsonify({'error': 'City parameter is required'}), 400
        
        print(f"\n{'='*60}")
        print(f"PLACES SEARCH REQUEST")
        print(f"{'='*60}")
        print(f"City: {city}")
        print(f"Calling main_engine.get_places_for_ui()...")
        
        # STEP 1: Call main_engine to get places data directly
        all_attractions = get_places_for_ui(city)
        
        if not all_attractions:
            print(f"✗ No attractions found for '{city}'")
            return jsonify({
                'success': False,
                'error': 'No places found',
                'city': city,
                'places': [],
                'count': 0
            }), 404
        
        print(f"✓ Received {len(all_attractions)} places from main_engine")
        
        # STEP 2: Format ALL places for frontend (excluding airports)
        places = []
        for place in all_attractions:
            # Skip airports - we don't want to show them
            place_types = place.get('types', [])
            if 'airport' in place_types or 'international_airport' in place_types:
                continue
            
            # Extract thumbnail URL from cached data (already fetched by main_engine)
            thumbnail_url = place.get('thumbnailUrl', '')
            
            places.append({
                'id': place.get('id', ''),
                'displayName': place.get('displayName', {'text': 'Unknown'}),
                'types': place_types,
                'rating': place.get('rating'),
                'userRatingCount': place.get('userRatingCount'),
                'websiteUri': place.get('websiteUri'),
                'generativeSummary': place.get('generativeSummary', {}),
                'reviewSummary': place.get('reviewSummary', {}),
                'thumbnailUrl': thumbnail_url,
                'location': place.get('location', {}),
                'formattedAddress': place.get('formattedAddress', ''),
                'regularOpeningHours': place.get('regularOpeningHours', {}),
                'priceLevel': place.get('priceLevel', ''),
                'goodForGroups': place.get('goodForGroups', False),
                'goodForChildren': place.get('goodForChildren', False),
                'paymentOptions': place.get('paymentOptions', {}),
                'rank_score': place.get('rank_score', 0),
                'distance_to_query': place.get('distance_to_query', 0)
            })
        
        print(f"✓ Returning {len(places)} places to frontend (airports filtered out)")
        print(f"{'='*60}\n")
        
        return jsonify({
            'success': True,
            'city': city,
            'places': places,
            'count': len(places)
        }), 200
        
    except Exception as e:
        print(f"✗ CRITICAL ERROR in places search: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Failed to fetch places',
            'detail': str(e)
        }), 500


# --- Trip Planner API ---
@app.route('/api/trip/generate', methods=['POST'])
def generate_trip():
    """
    Generate a trip itinerary using advanced_trip.py
    
    Request body:
    {
        "city": "San Diego",
        "num_days": 3,
        "pacing": "M",  // R, M, or P
        "exclude_types": ["museum", "park"],  // optional
        "require_types": ["beach"],  // optional
        "require_places": ["Balboa Park"]  // optional
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        city = data.get('city', '').strip()
        if not city:
            return jsonify({'error': 'City is required'}), 400
        
        num_days = data.get('num_days', 3)
        pacing = data.get('pacing', 'M').upper()
        exclude_types = data.get('exclude_types', [])
        require_types = data.get('require_types', [])
        require_places = data.get('require_places', [])
        
        # Validate pacing
        if pacing not in ['R', 'M', 'P']:
            return jsonify({'error': 'Invalid pacing. Must be R, M, or P'}), 400
        
        # Validate num_days
        if not isinstance(num_days, int) or num_days < 1 or num_days > 14:
            return jsonify({'error': 'Number of days must be between 1 and 14'}), 400
        
        print(f"\n{'='*60}")
        print(f"TRIP PLANNER REQUEST")
        print(f"{'='*60}")
        print(f"City: {city}")
        print(f"Days: {num_days}")
        print(f"Pacing: {pacing}")
        print(f"Exclude: {exclude_types}")
        print(f"Require Types: {require_types}")
        print(f"Require Places: {require_places}")
        
        # Import the trip planner module
        import sys
        import os
        from pathlib import Path
        import importlib.util
        
        # Add the backend directory to Python path
        backend_path = os.path.dirname(__file__)
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        
        # Import trip_planner module directly
        trip_planner_path = os.path.join(backend_path, 'main_engine', 'trip_planner.py')
        spec = importlib.util.spec_from_file_location("trip_planner_module", trip_planner_path)
        trip_planner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(trip_planner)
        
        # Get functions from trip_planner
        TripConfig = trip_planner.Config
        normalize_city_name = trip_planner.normalize_city_name
        geocode_city_locally = trip_planner.geocode_city_locally
        create_final_itinerary = trip_planner.create_final_itinerary
        find_nearest_airport = trip_planner.find_nearest_airport
        find_special_time_places = trip_planner.find_special_time_places
        get_other_top_places = trip_planner.get_other_top_places
        detect_nested_attractions = trip_planner.detect_nested_attractions
        simple_clustering = trip_planner.simple_clustering
        DAY_TRIP_MIN_KM = trip_planner.DAY_TRIP_MIN_KM
        DAY_TRIP_MAX_KM = trip_planner.DAY_TRIP_MAX_KM
        
        # Check if hub data exists for this city
        normalized_name = normalize_city_name(city, for_filename=True)
        hub_file = TripConfig.HUB_ATTRACTIONS_DIR / f"{normalized_name}.json"
        
        if not hub_file.exists():
            # Call main_engine to fetch data
            print(f"No data found for '{city}'. Fetching from main_engine...")
            
            # Import main_engine module directly
            main_engine_path = os.path.join(backend_path, 'main_engine', 'main_engine.py')
            spec2 = importlib.util.spec_from_file_location("main_engine_module", main_engine_path)
            main_engine_mod = importlib.util.module_from_spec(spec2)
            spec2.loader.exec_module(main_engine_mod)
            get_places_for_ui = main_engine_mod.get_places_for_ui
            
            # Fetch places data
            all_places = get_places_for_ui(city)
            
            if not all_places:
                return jsonify({
                    'error': f'Could not fetch data for {city}. Please check the city name and try again.'
                }), 404
            
            # Save to hub file for future use
            import json
            with open(hub_file, 'w', encoding='utf-8') as f:
                json.dump(all_places, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Data fetched and saved for '{city}'")
        else:
            # Load existing hub data
            import json
            with open(hub_file, 'r', encoding='utf-8') as f:
                all_places = json.load(f)
            print(f"✓ Loaded existing data for '{city}'")
        
        # Get city coordinates
        city_coords = geocode_city_locally(city)
        if not city_coords:
            return jsonify({
                'error': f'Could not find coordinates for {city}'
            }), 404
        
        # Perform clustering and nested detection
        cluster_assignments = simple_clustering(all_places, eps_km=3.0, min_samples=2)
        nested_map = detect_nested_attractions(all_places)
        
        # Add cluster info to places
        for place in all_places:
            place['cluster_id'] = cluster_assignments.get(place['id'], -1)
        
        # Generate the itinerary - create both city_focused and with_day_trip versions
        print("Generating city-focused itinerary...")
        import copy
        plan1_itinerary = create_final_itinerary(
            places=copy.deepcopy(all_places),
            num_days=num_days,
            pacing=pacing,
            city_coords=city_coords,
            city_name=city,
            exclude_types=exclude_types,
            require_types=require_types,
            force_city_only=True,  # City-focused plan
            require_names=require_places
        )
        
        if not plan1_itinerary:
            return jsonify({
                'error': 'Could not generate itinerary with the given constraints. Try adjusting your preferences.'
            }), 400
        
        # Generate day trip version if applicable
        far_places_exist = any(
            DAY_TRIP_MIN_KM <= p.get('distance_to_query', 0) <= DAY_TRIP_MAX_KM 
            for p in all_places
        )
        plan2_itinerary = []
        if num_days >= 3 and far_places_exist:
            print("Generating day trip itinerary...")
            plan2_itinerary = create_final_itinerary(
                places=copy.deepcopy(all_places),
                num_days=num_days,
                pacing=pacing,
                city_coords=city_coords,
                city_name=city,
                exclude_types=exclude_types,
                require_types=require_types,
                force_city_only=False,  # Include day trip
                require_names=require_places
            )
        
        # Find nearest airport
        nearest_airport = find_nearest_airport(all_places, city_coords)
        airport_info = None
        if nearest_airport:
            airport_info = {
                'name': nearest_airport.get('displayName', {}).get('text', 'Unknown Airport'),
                'distance_km': nearest_airport.get('distance_to_query', 0)
            }
        
        # Find special time places
        special_places = find_special_time_places(all_places)
        
        # Get other top places not in itinerary
        other_places = get_other_top_places(all_places, plan1_itinerary, nested_map)
        
        # Format the response - send both city_focused and with_day_trip
        response = {
            'success': True,
            'city': city,
            'num_days': num_days,
            'pacing': pacing,
            'itineraries': {
                'city_focused': plan1_itinerary,
                'with_day_trip': plan2_itinerary if plan2_itinerary else []
            },
            'airport': airport_info,
            'special_places': {
                'early_morning': [
                    {
                        'name': p.get('displayName', {}).get('text', 'Unknown'),
                        'rating': p.get('rating', 0),
                        'types': p.get('types', []),
                        'website': p.get('websiteUri')
                    }
                    for p in special_places.get('early_morning', [])
                ],
                'late_night': [
                    {
                        'name': p.get('displayName', {}).get('text', 'Unknown'),
                        'rating': p.get('rating', 0),
                        'types': p.get('types', []),
                        'website': p.get('websiteUri')
                    }
                    for p in special_places.get('late_night', [])
                ]
            },
            'other_top_places': [
                {
                    'name': p.get('displayName', {}).get('text', 'Unknown'),
                    'rating': p.get('rating', 0),
                    'review_count': p.get('userRatingCount', 0),
                    'types': p.get('types', []),
                    'location': p.get('location', {})
                }
                for p in other_places[:5]
            ]
        }
        
        print(f"✓ Generated {len(plan1_itinerary)} days of city-focused itinerary")
        if plan2_itinerary:
            print(f"✓ Generated {len(plan2_itinerary)} days of day-trip itinerary")
        print(f"{'='*60}\n")
        
        return jsonify(response), 200
        
    except Exception as e:
        print(f"✗ CRITICAL ERROR in trip generation: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Failed to generate trip plan',
            'detail': str(e)
        }), 500


# =============================================================================
# RUN APPLICATION
# =============================================================================

if __name__ == '__main__':
    print(f"\n{'='*60}")
    print(f"Starting {Config.APP_NAME}")
    print(f"{'='*60}")
    print(f"Environment: {Config.FLASK_ENV}")
    print(f"Debug Mode: {Config.DEBUG}")
    print(f"Host: {Config.HOST}")
    print(f"Port: {Config.PORT}")
    print(f"{'='*60}\n")
    
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )
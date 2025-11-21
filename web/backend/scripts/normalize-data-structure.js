/**
 * Data Normalization Script
 * Converts inconsistent JSON structures to unified format
 * 
 * Handles:
 * - Argentina: country → states → places
 * - USA/California: country → state → cities → places
 * 
 * Output: Standardized format with regions
 */

const fs = require('fs');
const path = require('path');

// Country code mapping
const COUNTRY_CODES = {
  'Argentina': 'AR',
  'USA': 'US',
  'Thailand': 'TH',
  'France': 'FR',
  'Italy': 'IT',
  'Spain': 'ES',
  'Japan': 'JP',
  'India': 'IN'
  // Add more as needed
};

/**
 * Generate slug from name (for IDs)
 */
function generateSlug(text) {
  return text
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-]/g, '')
    .replace(/--+/g, '-')
    .trim();
}

/**
 * Validate place data
 */
function validatePlace(place, regionName, countryName) {
  const errors = [];
  
  // Required fields
  if (!place.id) errors.push(`Missing id in ${regionName}, ${countryName}`);
  if (!place.name_english) errors.push(`Missing name_english for ${place.id || 'unknown'}`);
  if (!place.coordinates || !place.coordinates.lat || !place.coordinates.lng) {
    errors.push(`Missing coordinates for ${place.id || place.name_english}`);
  }
  
  // Validate coordinate ranges
  if (place.coordinates) {
    const { lat, lng } = place.coordinates;
    if (lat < -90 || lat > 90) errors.push(`Invalid latitude ${lat} for ${place.id}`);
    if (lng < -180 || lng > 180) errors.push(`Invalid longitude ${lng} for ${place.id}`);
  }
  
  // Check tags
  if (!place.tags || !Array.isArray(place.tags) || place.tags.length === 0) {
    errors.push(`Missing or empty tags for ${place.id}`);
  }
  
  return errors;
}

/**
 * Normalize Argentina data
 * Input: country → states → places
 * Output: country → regions → places
 */
function normalizeArgentina(data, outputPath) {
  console.log('📍 Normalizing Argentina data...');
  
  const normalized = {
    country: data.country,
    country_code: COUNTRY_CODES[data.country] || 'AR',
    regions: []
  };
  
  let totalPlaces = 0;
  const allErrors = [];
  
  // Convert states to regions
  for (const state of data.states) {
    const region = {
      region_id: generateSlug(state.english_name || state.name),
      name: state.name,
      name_english: state.english_name || state.name,
      type: 'state',
      coordinates: state.coordinates || extractCoordinatesFromPlaces(state.places),
      nearest_airport: state.nearest_airport,
      places: []
    };
    
    // Process places
    for (const place of state.places) {
      // Validate place
      const errors = validatePlace(place, region.name, normalized.country);
      if (errors.length > 0) {
        allErrors.push(...errors);
      }
      
      // Standardize coordinates format
      if (place.coordinates) {
        place.coordinates = {
          lat: place.coordinates.lat || place.coordinates.latitude,
          lng: place.coordinates.lng || place.coordinates.longitude
        };
        delete place.coordinates.latitude;
        delete place.coordinates.longitude;
      }
      
      region.places.push(place);
      totalPlaces++;
    }
    
    normalized.regions.push(region);
  }
  
  // Add metadata
  normalized.metadata = {
    enhanced_at: new Date().toISOString(),
    total_places: totalPlaces,
    total_regions: normalized.regions.length,
    version: '4.0_standardized',
    data_sources: data.metadata?.data_sources || ['openstreetmap', 'wikipedia', 'wikimedia_commons'],
    enhancement_features: data.metadata?.enhancement_features || [
      'coordinates_from_osm',
      'photos_from_wikipedia_and_commons',
      'dress_codes',
      'addresses',
      'unique_identifiers'
    ]
  };
  
  // Write output
  fs.writeFileSync(outputPath, JSON.stringify(normalized, null, 2));
  console.log(`✅ Argentina normalized: ${totalPlaces} places in ${normalized.regions.length} regions`);
  
  if (allErrors.length > 0) {
    console.warn(`⚠️  Found ${allErrors.length} validation errors (see normalize-errors.log)`);
    fs.writeFileSync(
      path.join(path.dirname(outputPath), 'normalize-errors.log'),
      allErrors.join('\n')
    );
  }
  
  return normalized;
}

/**
 * Normalize USA/California data
 * Input: country → state → cities → places
 * Output: country → regions → places
 */
function normalizeCalifornia(data, outputPath) {
  console.log('📍 Normalizing California data...');
  
  const normalized = {
    country: data.country,
    country_code: COUNTRY_CODES[data.country] || 'US',
    state: data.state,
    regions: []
  };
  
  let totalPlaces = 0;
  const allErrors = [];
  
  // Convert cities to regions
  for (const city of data.cities) {
    const region = {
      region_id: generateSlug(city.city),
      name: city.city,
      name_english: city.city,
      type: 'city',
      coordinates: city.coordinates || extractCoordinatesFromPlaces(city.places),
      nearest_airport: city.nearest_airport,
      places: []
    };
    
    // Process places
    for (const place of city.places) {
      // Validate place
      const errors = validatePlace(place, region.name, `${normalized.country} - ${normalized.state}`);
      if (errors.length > 0) {
        allErrors.push(...errors);
      }
      
      // Standardize coordinates format
      if (place.coordinates) {
        place.coordinates = {
          lat: place.coordinates.lat || place.coordinates.latitude,
          lng: place.coordinates.lng || place.coordinates.longitude
        };
        delete place.coordinates.latitude;
        delete place.coordinates.longitude;
      }
      
      region.places.push(place);
      totalPlaces++;
    }
    
    normalized.regions.push(region);
  }
  
  // Add metadata
  normalized.metadata = {
    enhanced_at: data.metadata?.enhanced_at || new Date().toISOString(),
    total_places: totalPlaces,
    total_regions: normalized.regions.length,
    version: '4.0_standardized',
    data_sources: data.metadata?.data_sources || ['openstreetmap', 'wikipedia', 'wikimedia_commons'],
    enhancement_features: data.metadata?.enhancement_features || [
      'coordinates_from_osm',
      'photos_from_wikipedia_and_commons',
      'dress_codes',
      'addresses',
      'unique_identifiers'
    ]
  };
  
  // Write output
  fs.writeFileSync(outputPath, JSON.stringify(normalized, null, 2));
  console.log(`✅ California normalized: ${totalPlaces} places in ${normalized.regions.length} regions`);
  
  if (allErrors.length > 0) {
    console.warn(`⚠️  Found ${allErrors.length} validation errors (see normalize-errors.log)`);
    fs.writeFileSync(
      path.join(path.dirname(outputPath), 'normalize-errors.log'),
      allErrors.join('\n')
    );
  }
  
  return normalized;
}

/**
 * Extract coordinates from first place (fallback)
 */
function extractCoordinatesFromPlaces(places) {
  if (!places || places.length === 0) return null;
  
  const firstPlace = places.find(p => p.coordinates);
  if (!firstPlace) return null;
  
  return {
    lat: firstPlace.coordinates.lat || firstPlace.coordinates.latitude,
    lng: firstPlace.coordinates.lng || firstPlace.coordinates.longitude
  };
}

/**
 * Main execution
 */
function main() {
  console.log('🚀 Starting data normalization...\n');
  
  const baseDir = path.join(__dirname, '..');
  const outputDir = path.join(baseDir, 'places_database', 'countries');
  
  // Create output directory
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
    console.log('📁 Created output directory:', outputDir);
  }
  
  // 1. Normalize Argentina
  const argentinaPath = path.join(baseDir, 'world_database_2', 'argentina.json');
  if (fs.existsSync(argentinaPath)) {
    const argentinaData = JSON.parse(fs.readFileSync(argentinaPath, 'utf8'));
    normalizeArgentina(argentinaData, path.join(outputDir, 'argentina.json'));
  } else {
    console.error('❌ Argentina file not found:', argentinaPath);
  }
  
  console.log('');
  
  // 2. Normalize California
  const californiaPath = path.join(baseDir, 'world_database', 'USA', 'california.json');
  if (fs.existsSync(californiaPath)) {
    const californiaData = JSON.parse(fs.readFileSync(californiaPath, 'utf8'));
    normalizeCalifornia(californiaData, path.join(outputDir, 'usa-california.json'));
  } else {
    console.error('❌ California file not found:', californiaPath);
  }
  
  console.log('\n✅ Normalization complete!');
  console.log(`📂 Output directory: ${outputDir}`);
  console.log('\nNext steps:');
  console.log('1. Review normalized files');
  console.log('2. Run: node scripts/build-search-index.js');
  console.log('3. Copy to frontend/public/data/');
}

// Run if called directly
if (require.main === module) {
  main();
}

module.exports = {
  normalizeArgentina,
  normalizeCalifornia,
  generateSlug,
  validatePlace
};

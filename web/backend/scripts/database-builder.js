/**
 * Professional Database Builder for TripRaft
 * 
 * Architecture:
 * - Hierarchical: Country → State → City → Places
 * - Flexible: Handles Country→State→Places OR Country→State→City→Places
 * - No Hardcoding: Auto-detects structure
 * - SQLite Backup: Permanent storage
 * - Search Optimized: By city, state, or country
 */

const fs = require('fs');
const path = require('path');

/**
 * Database Configuration
 */
const CONFIG = {
  INPUT_DIRS: [
    'world_database',
    'world_database_2'
  ],
  OUTPUT_DIR: 'places_database',
  STRUCTURE: {
    COUNTRIES: 'countries',      // Root level
    STATES: 'states',           // State level folders
    CITIES: 'cities'            // City level JSON files
  }
};

/**
 * Generate clean slug from text
 */
function generateSlug(text) {
  if (!text) return '';
  return text
    .toString()
    .toLowerCase()
    .trim()
    .replace(/[\s_]+/g, '-')           // Replace spaces/underscores with hyphens
    .replace(/[^\w\-]+/g, '')          // Remove non-word chars except hyphens
    .replace(/\-\-+/g, '-')            // Replace multiple hyphens with single
    .replace(/^-+/, '')                // Trim hyphens from start
    .replace(/-+$/, '');               // Trim hyphens from end
}

/**
 * Auto-detect data structure type
 */
function detectStructure(data) {
  // Type 1: Country → States → Places (Argentina style)
  if (data.states && Array.isArray(data.states)) {
    const firstState = data.states[0];
    if (firstState && firstState.places && Array.isArray(firstState.places)) {
      return {
        type: 'country_state_places',
        hasStates: true,
        hasCities: false,
        stateKey: 'states',
        placeKey: 'places'
      };
    }
  }
  
  // Type 2: Country → State → Cities → Places (USA/California style)
  if (data.state && data.cities && Array.isArray(data.cities)) {
    const firstCity = data.cities[0];
    if (firstCity && firstCity.places && Array.isArray(firstCity.places)) {
      return {
        type: 'country_state_city_places',
        hasStates: true,
        hasCities: true,
        stateKey: 'state',
        cityKey: 'cities',
        placeKey: 'places'
      };
    }
  }
  
  // Type 3: Country → Cities → Places (direct cities)
  if (data.cities && Array.isArray(data.cities)) {
    const firstCity = data.cities[0];
    if (firstCity && firstCity.places && Array.isArray(firstCity.places)) {
      return {
        type: 'country_city_places',
        hasStates: false,
        hasCities: true,
        cityKey: 'cities',
        placeKey: 'places'
      };
    }
  }
  
  return { type: 'unknown' };
}

/**
 * Normalize coordinates to consistent format
 */
function normalizeCoordinates(coords) {
  if (!coords) return null;
  
  return {
    lat: coords.lat || coords.latitude || null,
    lng: coords.lng || coords.longitude || coords.lon || null
  };
}

/**
 * Normalize place data
 */
function normalizePlace(place) {
  return {
    id: place.id || generateSlug(place.name_english || place.name),
    name: place.name_english || place.name || place.name_native,
    name_native: place.name_native || place.name_english || place.name,
    coordinates: normalizeCoordinates(place.coordinates),
    rating: place.rating_tourist_priority || place.rating || 0,
    tags: place.tags || [],
    photos: place.photos || {},
    summary: place.ai_summary || place.description || '',
    opening_hours: place.opening_hours || null,
    duration: place.suggested_duration || place.visit_duration_minutes || null,
    cost: place.cost || 'Unknown',
    website: place.official_website || place.website || null,
    address: place.address || null,
    sunrise_view: place.sunrise_view || false,
    sunset_view: place.sunset_view || false,
    best_time: place.best_time_to_visit || null,
    advance_booking: place.advanced_booking || place.advance_booking || false,
    dress_code: place.dress_code || null,
    place_tip: place.place_tip || null
  };
}

/**
 * Process Type 1: Country → State → Places
 */
function processCountryStatePlaces(data, countryInfo) {
  console.log(`  📊 Structure: Country → State → Places`);
  
  const result = {
    country: countryInfo.name,
    country_code: countryInfo.code,
    type: 'state_level',
    states: []
  };
  
  for (const state of data.states || []) {
    const stateSlug = generateSlug(state.english_name || state.name);
    const stateName = state.english_name || state.name;
    
    console.log(`    📍 State: ${stateName} (${state.places?.length || 0} places)`);
    
    const stateData = {
      state_id: stateSlug,
      name: stateName,
      name_native: state.name,
      coordinates: normalizeCoordinates(state.coordinates),
      airport: state.nearest_airport || null,
      places: (state.places || []).map(normalizePlace),
      metadata: {
        total_places: state.places?.length || 0,
        has_cities: false
      }
    };
    
    // ⭐ Add simplified state info to index (no embedded places)
    result.states.push({
      state_id: stateSlug,
      name: stateName,
      name_native: state.name,
      place_count: stateData.places.length
    });
    
    // Save individual state file with full data
    const stateDir = path.join(
      CONFIG.OUTPUT_DIR,
      CONFIG.STRUCTURE.COUNTRIES,
      countryInfo.slug,
      CONFIG.STRUCTURE.STATES
    );
    
    if (!fs.existsSync(stateDir)) {
      fs.mkdirSync(stateDir, { recursive: true });
    }
    
    const stateFilePath = path.join(stateDir, `${stateSlug}.json`);
    fs.writeFileSync(stateFilePath, JSON.stringify(stateData, null, 2));
  }
  
  return result;
}

/**
 * Process Type 2: Country → State → City → Places
 */
function processCountryStateCityPlaces(data, countryInfo) {
  console.log(`  📊 Structure: Country → State → City → Places`);
  
  const stateName = data.state || 'unknown';
  const stateSlug = generateSlug(stateName);
  
  console.log(`    📍 State: ${stateName}`);
  
  const result = {
    country: countryInfo.name,
    country_code: countryInfo.code,
    type: 'city_level',
    state: {
      state_id: stateSlug,
      name: stateName,
      cities: []
    }
  };
  
  // Create state directory
  const stateDir = path.join(
    CONFIG.OUTPUT_DIR,
    CONFIG.STRUCTURE.COUNTRIES,
    countryInfo.slug,
    CONFIG.STRUCTURE.STATES,
    stateSlug
  );
  
  if (!fs.existsSync(stateDir)) {
    fs.mkdirSync(stateDir, { recursive: true });
  }
  
  // Process each city
  for (const city of data.cities || []) {
    const citySlug = generateSlug(city.city || city.name);
    const cityName = city.city || city.name;
    
    console.log(`      🏙️  City: ${cityName} (${city.places?.length || 0} places)`);
    
    const cityData = {
      city_id: citySlug,
      name: cityName,
      state: stateName,
      country: countryInfo.name,
      coordinates: normalizeCoordinates(city.coordinates),
      airport: city.nearest_airport || null,
      places: (city.places || []).map(normalizePlace),
      metadata: {
        total_places: city.places?.length || 0
      }
    };
    
    result.state.cities.push({
      city_id: citySlug,
      name: cityName,
      place_count: cityData.places.length
    });
    
    // Save individual city file
    const cityFilePath = path.join(stateDir, `${citySlug}.json`);
    fs.writeFileSync(cityFilePath, JSON.stringify(cityData, null, 2));
  }
  
  return result;
}

/**
 * Process Type 3: Country → City → Places (no states)
 */
function processCountryCityPlaces(data, countryInfo) {
  console.log(`  📊 Structure: Country → City → Places`);
  
  const result = {
    country: countryInfo.name,
    country_code: countryInfo.code,
    type: 'city_level',
    cities: []
  };
  
  // Create cities directory
  const citiesDir = path.join(
    CONFIG.OUTPUT_DIR,
    CONFIG.STRUCTURE.COUNTRIES,
    countryInfo.slug,
    CONFIG.STRUCTURE.CITIES
  );
  
  if (!fs.existsSync(citiesDir)) {
    fs.mkdirSync(citiesDir, { recursive: true });
  }
  
  // Process each city
  for (const city of data.cities || []) {
    const citySlug = generateSlug(city.city || city.name);
    const cityName = city.city || city.name;
    
    console.log(`    🏙️  City: ${cityName} (${city.places?.length || 0} places)`);
    
    const cityData = {
      city_id: citySlug,
      name: cityName,
      country: countryInfo.name,
      coordinates: normalizeCoordinates(city.coordinates),
      airport: city.nearest_airport || null,
      places: (city.places || []).map(normalizePlace),
      metadata: {
        total_places: city.places?.length || 0
      }
    };
    
    result.cities.push({
      city_id: citySlug,
      name: cityName,
      place_count: cityData.places.length
    });
    
    // Save individual city file
    const cityFilePath = path.join(citiesDir, `${citySlug}.json`);
    fs.writeFileSync(cityFilePath, JSON.stringify(cityData, null, 2));
  }
  
  return result;
}

/**
 * Extract country info from data or filename
 */
function extractCountryInfo(data, filename) {
  const country = data.country || path.basename(filename, '.json');
  
  // Try to auto-detect country code
  let countryCode = data.country_code;
  
  // Common country codes (expand this as needed)
  const commonCodes = {
    'argentina': 'AR',
    'usa': 'US',
    'united states': 'US',
    'california': 'US',
    'thailand': 'TH',
    'france': 'FR',
    'italy': 'IT',
    'spain': 'ES',
    'japan': 'JP',
    'india': 'IN',
    'brazil': 'BR',
    'mexico': 'MX',
    'canada': 'CA',
    'australia': 'AU',
    'germany': 'DE',
    'uk': 'GB',
    'united kingdom': 'GB',
    'china': 'CN',
    'south korea': 'KR',
    'singapore': 'SG',
    'malaysia': 'MY',
    'indonesia': 'ID',
    'vietnam': 'VN',
    'philippines': 'PH'
  };
  
  if (!countryCode) {
    countryCode = commonCodes[country.toLowerCase()] || country.substring(0, 2).toUpperCase();
  }
  
  return {
    name: country,
    code: countryCode,
    slug: generateSlug(country)
  };
}

/**
 * Process a single country file
 */
function processCountryFile(filePath) {
  const filename = path.basename(filePath);
  console.log(`\n📂 Processing: ${filename}`);
  
  try {
    const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    const structure = detectStructure(data);
    
    if (structure.type === 'unknown') {
      console.error(`  ❌ Unknown structure, skipping`);
      return null;
    }
    
    const countryInfo = extractCountryInfo(data, filename);
    console.log(`  🌍 Country: ${countryInfo.name} (${countryInfo.code})`);
    
    let result;
    
    switch (structure.type) {
      case 'country_state_places':
        result = processCountryStatePlaces(data, countryInfo);
        break;
      
      case 'country_state_city_places':
        result = processCountryStateCityPlaces(data, countryInfo);
        break;
      
      case 'country_city_places':
        result = processCountryCityPlaces(data, countryInfo);
        break;
      
      default:
        console.error(`  ❌ Unsupported structure type: ${structure.type}`);
        return null;
    }
    
    // Save country index file
    const countryDir = path.join(
      CONFIG.OUTPUT_DIR,
      CONFIG.STRUCTURE.COUNTRIES,
      countryInfo.slug
    );
    
    if (!fs.existsSync(countryDir)) {
      fs.mkdirSync(countryDir, { recursive: true });
    }
    
    const indexPath = path.join(countryDir, 'index.json');
    fs.writeFileSync(indexPath, JSON.stringify(result, null, 2));
    
    console.log(`  ✅ Processed successfully`);
    
    return result;
    
  } catch (error) {
    console.error(`  ❌ Error: ${error.message}`);
    return null;
  }
}

/**
 * Scan for all JSON files recursively
 */
function findAllJsonFiles(dir) {
  const files = [];
  
  if (!fs.existsSync(dir)) return files;
  
  const items = fs.readdirSync(dir);
  
  for (const item of items) {
    const fullPath = path.join(dir, item);
    const stat = fs.statSync(fullPath);
    
    if (stat.isDirectory()) {
      files.push(...findAllJsonFiles(fullPath));
    } else if (stat.isFile() && item.endsWith('.json')) {
      files.push(fullPath);
    }
  }
  
  return files;
}

/**
 * Main execution
 */
function main() {
  console.log('🚀 TripRaft Professional Database Builder\n');
  console.log('='.repeat(60));
  
  const baseDir = path.join(__dirname, '..');
  const allResults = [];
  const countryMap = new Map(); // Group results by country
  
  // Create output directory
  const outputDir = path.join(baseDir, CONFIG.OUTPUT_DIR);
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }
  
  // Scan all input directories
  for (const inputDirName of CONFIG.INPUT_DIRS) {
    const inputDir = path.join(baseDir, inputDirName);
    
    if (!fs.existsSync(inputDir)) {
      console.log(`⚠️  Skipping ${inputDirName} (not found)`);
      continue;
    }
    
    console.log(`\n📁 Scanning: ${inputDirName}`);
    const jsonFiles = findAllJsonFiles(inputDir);
    console.log(`   Found ${jsonFiles.length} JSON files`);
    
    for (const filePath of jsonFiles) {
      const result = processCountryFile(filePath);
      if (result) {
        const countryKey = `${result.country_code}_${result.country}`;
        
        if (!countryMap.has(countryKey)) {
          countryMap.set(countryKey, {
            country: result.country,
            country_code: result.country_code,
            type: result.type,
            states: [],
            cities: []
          });
        }
        
        const countryData = countryMap.get(countryKey);
        
        // Merge state data
        if (result.state) {
          countryData.states.push({
            state_id: result.state.state_id,
            name: result.state.name,
            cities: result.state.cities || []
          });
        }
        
        // Merge city data
        if (result.cities) {
          countryData.cities.push(...result.cities);
        }
        
        allResults.push(result);
      }
    }
  }
  
  // Write consolidated index files for each country
  console.log('\n📝 Creating consolidated country indexes...');
  for (const [countryKey, countryData] of countryMap.entries()) {
    const countryDir = path.join(
      CONFIG.OUTPUT_DIR,
      CONFIG.STRUCTURE.COUNTRIES,
      generateSlug(countryData.country)
    );
    
    const indexPath = path.join(countryDir, 'index.json');
    
    // Build final index structure
    const indexData = {
      country: countryData.country,
      country_code: countryData.country_code,
      type: countryData.type
    };
    
    if (countryData.states.length > 0) {
      indexData.states = countryData.states;
    }
    
    if (countryData.cities.length > 0) {
      indexData.cities = countryData.cities;
    }
    
    fs.writeFileSync(indexPath, JSON.stringify(indexData, null, 2));
    console.log(`  ✅ ${countryData.country}: ${countryData.states.length} states, ${countryData.cities.length} cities`);
  }
  
  console.log('\n' + '='.repeat(60));
  console.log(`\n✅ Database build complete!`);
  console.log(`   📊 Processed: ${allResults.length} countries`);
  console.log(`   📂 Output: ${outputDir}`);
  
  console.log('\n📁 Directory Structure:');
  console.log(`   ${CONFIG.OUTPUT_DIR}/`);
  console.log(`   └── countries/`);
  console.log(`       ├── argentina/`);
  console.log(`       │   ├── index.json           (Country overview)`);
  console.log(`       │   └── states/`);
  console.log(`       │       ├── buenos-aires.json`);
  console.log(`       │       └── mendoza.json`);
  console.log(`       └── usa/`);
  console.log(`           ├── index.json           (Country overview)`);
  console.log(`           └── states/`);
  console.log(`               └── california/`);
  console.log(`                   ├── los-angeles.json`);
  console.log(`                   └── san-francisco.json`);
  
  console.log('\n📝 Next Steps:');
  console.log('   1. Run: node scripts/build-search-index.js');
  console.log('   2. Run: node scripts/build-sqlite-backup.js');
  console.log('   3. Test search functionality');
}

// Run if called directly
if (require.main === module) {
  main();
}

module.exports = {
  processCountryFile,
  detectStructure,
  normalizePlace,
  generateSlug
};

/**
 * Data Validation Script
 * Validates normalized place data for quality and completeness
 */

const fs = require('fs');
const path = require('path');

/**
 * Validation rules
 */
const REQUIRED_FIELDS = {
  place: ['id', 'name_english', 'coordinates', 'tags'],
  region: ['region_id', 'name', 'name_english', 'type', 'places'],
  country: ['country', 'country_code', 'regions', 'metadata']
};

const VALID_TAGS = [
  'landmark', 'museum', 'nature', 'park', 'beach', 'mountain', 'lake',
  'art', 'architecture', 'history', 'culture', 'religion', 'shopping',
  'dining', 'nightlife', 'entertainment', 'sports', 'adventure', 'scenic',
  'viewpoint', 'photography', 'family', 'romantic', 'budget', 'luxury',
  'unesco', 'monument', 'square', 'church', 'cathedral', 'temple',
  'festival', 'market', 'food', 'street food', 'cafe', 'restaurant'
];

/**
 * Validate coordinate ranges
 */
function validateCoordinates(coords, placeName) {
  const errors = [];
  
  if (!coords) {
    errors.push(`Missing coordinates for ${placeName}`);
    return errors;
  }
  
  const { lat, lng } = coords;
  
  if (typeof lat !== 'number' || typeof lng !== 'number') {
    errors.push(`Invalid coordinate types for ${placeName}`);
  }
  
  if (lat < -90 || lat > 90) {
    errors.push(`Invalid latitude ${lat} for ${placeName} (must be -90 to 90)`);
  }
  
  if (lng < -180 || lng > 180) {
    errors.push(`Invalid longitude ${lng} for ${placeName} (must be -180 to 180)`);
  }
  
  return errors;
}

/**
 * Validate place data
 */
function validatePlace(place, regionName, countryName) {
  const errors = [];
  const warnings = [];
  
  // Check required fields
  for (const field of REQUIRED_FIELDS.place) {
    if (!place[field]) {
      errors.push(`[${countryName}/${regionName}] Missing required field "${field}" in place ${place.id || place.name_english || 'unknown'}`);
    }
  }
  
  // Validate ID format
  if (place.id && typeof place.id !== 'string') {
    errors.push(`[${countryName}/${regionName}] Invalid ID type for ${place.name_english}`);
  }
  
  // Validate coordinates
  if (place.coordinates) {
    errors.push(...validateCoordinates(place.coordinates, place.name_english));
  }
  
  // Validate tags
  if (place.tags) {
    if (!Array.isArray(place.tags)) {
      errors.push(`[${countryName}/${regionName}] Tags must be an array for ${place.name_english}`);
    } else if (place.tags.length === 0) {
      warnings.push(`[${countryName}/${regionName}] No tags for ${place.name_english}`);
    }
  }
  
  // Validate rating
  if (place.rating_tourist_priority !== undefined) {
    const rating = place.rating_tourist_priority;
    if (typeof rating !== 'number' || rating < 0 || rating > 10) {
      warnings.push(`[${countryName}/${regionName}] Invalid rating ${rating} for ${place.name_english} (should be 0-10)`);
    }
  }
  
  // Check for photos
  if (!place.photos || Object.keys(place.photos).length === 0) {
    warnings.push(`[${countryName}/${regionName}] No photos for ${place.name_english}`);
  }
  
  // Check for summary
  if (!place.ai_summary || place.ai_summary.length < 50) {
    warnings.push(`[${countryName}/${regionName}] Missing or short summary for ${place.name_english}`);
  }
  
  return { errors, warnings };
}

/**
 * Validate region data
 */
function validateRegion(region, countryName) {
  const errors = [];
  const warnings = [];
  
  // Check required fields
  for (const field of REQUIRED_FIELDS.region) {
    if (!region[field]) {
      errors.push(`[${countryName}] Missing required field "${field}" in region ${region.name || 'unknown'}`);
    }
  }
  
  // Validate region_id format
  if (region.region_id && !/^[a-z0-9-]+$/.test(region.region_id)) {
    errors.push(`[${countryName}] Invalid region_id format: ${region.region_id} (should be lowercase with hyphens)`);
  }
  
  // Validate coordinates
  if (region.coordinates) {
    errors.push(...validateCoordinates(region.coordinates, region.name));
  } else {
    warnings.push(`[${countryName}] No coordinates for region ${region.name}`);
  }
  
  // Check places array
  if (!Array.isArray(region.places)) {
    errors.push(`[${countryName}] Places must be an array in region ${region.name}`);
  } else if (region.places.length === 0) {
    warnings.push(`[${countryName}] Region ${region.name} has no places`);
  }
  
  return { errors, warnings };
}

/**
 * Validate country data
 */
function validateCountry(data, filename) {
  const errors = [];
  const warnings = [];
  let placeCount = 0;
  
  // Check required fields
  for (const field of REQUIRED_FIELDS.country) {
    if (!data[field]) {
      errors.push(`[${filename}] Missing required field "${field}"`);
    }
  }
  
  // Validate country code
  if (data.country_code && !/^[A-Z]{2}$/.test(data.country_code)) {
    errors.push(`[${filename}] Invalid country code: ${data.country_code} (should be 2 uppercase letters)`);
  }
  
  // Check regions
  if (!Array.isArray(data.regions)) {
    errors.push(`[${filename}] Regions must be an array`);
  } else {
    // Validate each region
    for (const region of data.regions) {
      const regionValidation = validateRegion(region, data.country);
      errors.push(...regionValidation.errors);
      warnings.push(...regionValidation.warnings);
      
      // Validate places in region
      if (Array.isArray(region.places)) {
        for (const place of region.places) {
          const placeValidation = validatePlace(place, region.name, data.country);
          errors.push(...placeValidation.errors);
          warnings.push(...placeValidation.warnings);
          placeCount++;
        }
      }
    }
  }
  
  // Validate metadata
  if (data.metadata) {
    if (data.metadata.total_places !== placeCount) {
      warnings.push(`[${filename}] Metadata place count mismatch: ${data.metadata.total_places} vs actual ${placeCount}`);
    }
  }
  
  return { errors, warnings, placeCount };
}

/**
 * Check for duplicate place IDs
 */
function checkDuplicateIds(allData) {
  const idMap = new Map();
  const duplicates = [];
  
  for (const { filename, data } of allData) {
    for (const region of data.regions || []) {
      for (const place of region.places || []) {
        if (place.id) {
          if (idMap.has(place.id)) {
            duplicates.push({
              id: place.id,
              locations: [idMap.get(place.id), `${filename}/${region.name}`]
            });
          } else {
            idMap.set(place.id, `${filename}/${region.name}`);
          }
        }
      }
    }
  }
  
  return duplicates;
}

/**
 * Main validation
 */
function main() {
  console.log('✅ Starting data validation...\n');
  
  const inputDir = path.join(__dirname, '..', 'places_database', 'countries');
  
  if (!fs.existsSync(inputDir)) {
    console.error('❌ Input directory not found:', inputDir);
    console.error('👉 Run normalize-data-structure.js first!');
    process.exit(1);
  }
  
  const files = fs.readdirSync(inputDir).filter(f => f.endsWith('.json'));
  console.log(`📂 Found ${files.length} files to validate\n`);
  
  const allData = [];
  const results = {
    totalErrors: 0,
    totalWarnings: 0,
    totalPlaces: 0,
    fileResults: []
  };
  
  // Validate each file
  for (const filename of files) {
    const filePath = path.join(inputDir, filename);
    console.log(`📍 Validating ${filename}...`);
    
    try {
      const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
      allData.push({ filename, data });
      
      const validation = validateCountry(data, filename);
      
      results.totalErrors += validation.errors.length;
      results.totalWarnings += validation.warnings.length;
      results.totalPlaces += validation.placeCount;
      
      results.fileResults.push({
        filename,
        errors: validation.errors.length,
        warnings: validation.warnings.length,
        places: validation.placeCount
      });
      
      if (validation.errors.length > 0) {
        console.log(`   ❌ ${validation.errors.length} errors`);
      }
      if (validation.warnings.length > 0) {
        console.log(`   ⚠️  ${validation.warnings.length} warnings`);
      }
      if (validation.errors.length === 0 && validation.warnings.length === 0) {
        console.log(`   ✅ Valid (${validation.placeCount} places)`);
      }
      
      // Save detailed errors/warnings
      if (validation.errors.length > 0 || validation.warnings.length > 0) {
        const reportPath = path.join(inputDir, `${filename}.validation.txt`);
        const report = [
          `Validation Report for ${filename}`,
          `Generated: ${new Date().toISOString()}`,
          '',
          'ERRORS:',
          ...validation.errors,
          '',
          'WARNINGS:',
          ...validation.warnings
        ].join('\n');
        fs.writeFileSync(reportPath, report);
      }
      
    } catch (error) {
      console.error(`   ❌ Error reading file: ${error.message}`);
      results.totalErrors++;
    }
  }
  
  console.log('');
  
  // Check for duplicate IDs
  console.log('🔍 Checking for duplicate place IDs...');
  const duplicates = checkDuplicateIds(allData);
  if (duplicates.length > 0) {
    console.error(`❌ Found ${duplicates.length} duplicate place IDs:`);
    for (const dup of duplicates.slice(0, 10)) { // Show first 10
      console.error(`   • ${dup.id}: ${dup.locations.join(' and ')}`);
    }
    results.totalErrors += duplicates.length;
  } else {
    console.log('✅ No duplicate IDs found');
  }
  
  console.log('');
  
  // Summary
  console.log('📊 Validation Summary:');
  console.log(`   • Total files: ${files.length}`);
  console.log(`   • Total places: ${results.totalPlaces.toLocaleString()}`);
  console.log(`   • Total errors: ${results.totalErrors}`);
  console.log(`   • Total warnings: ${results.totalWarnings}`);
  console.log('');
  
  if (results.totalErrors > 0) {
    console.error('❌ Validation failed! Please fix errors before proceeding.');
    console.log('📄 Check .validation.txt files for details');
    process.exit(1);
  } else if (results.totalWarnings > 0) {
    console.warn('⚠️  Validation passed with warnings');
    console.log('📄 Check .validation.txt files for details');
  } else {
    console.log('✅ All validations passed!');
  }
  
  console.log('\nNext steps:');
  console.log('1. Fix any errors/warnings (optional)');
  console.log('2. Run: npm run build-index');
}

// Run if called directly
if (require.main === module) {
  main();
}

module.exports = {
  validatePlace,
  validateRegion,
  validateCountry,
  validateCoordinates,
  checkDuplicateIds
};

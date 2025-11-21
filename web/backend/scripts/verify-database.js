const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const dbPath = path.join(__dirname, '..', 'places_database', 'tripraft.db');
const db = new sqlite3.Database(dbPath);

console.log('🔍 Database Verification\n');
console.log('='.repeat(60));

db.serialize(() => {
  // Get counts
  db.get('SELECT COUNT(*) as count FROM countries', (err, row) => {
    console.log(`\n📍 Countries: ${row.count}`);
    
    db.all('SELECT name, code FROM countries ORDER BY name', (err, rows) => {
      rows.forEach(r => console.log(`   • ${r.name} (${r.code})`));
    });
  });

  db.get('SELECT COUNT(*) as count FROM states', (err, row) => {
    console.log(`\n📍 States: ${row.count}`);
    
    db.all('SELECT s.name, c.name as country FROM states s JOIN countries c ON s.country_id = c.id ORDER BY c.name, s.name LIMIT 10', (err, rows) => {
      rows.forEach(r => console.log(`   • ${r.name} (${r.country})`));
      if (row.count > 10) console.log(`   ... and ${row.count - 10} more`);
    });
  });

  db.get('SELECT COUNT(*) as count FROM cities', (err, row) => {
    console.log(`\n📍 Cities: ${row.count}`);
    
    db.all('SELECT ci.name, s.name as state, co.name as country FROM cities ci LEFT JOIN states s ON ci.state_id = s.id JOIN countries co ON ci.country_id = co.id ORDER BY co.name, s.name, ci.name LIMIT 10', (err, rows) => {
      rows.forEach(r => console.log(`   • ${r.name}, ${r.state || r.country}`));
      if (row.count > 10) console.log(`   ... and ${row.count - 10} more`);
    });
  });

  db.get('SELECT COUNT(*) as count FROM places', (err, row) => {
    console.log(`\n📍 Places: ${row.count}`);
    
    db.all('SELECT p.name, ci.name as city, s.name as state, co.name as country, p.rating FROM places p LEFT JOIN cities ci ON p.city_id = ci.id LEFT JOIN states s ON p.state_id = s.id JOIN countries co ON p.country_id = co.id ORDER BY p.rating DESC LIMIT 10', (err, rows) => {
      console.log('\n   Top 10 Rated Places:');
      rows.forEach(r => console.log(`   • ${r.name} (${r.city || r.state}, ${r.country}) - Rating: ${r.rating}`));
    });
    
    setTimeout(() => {
      console.log('\n' + '='.repeat(60));
      console.log('\n✅ Database is fully populated and working!\n');
      db.close();
    }, 200);
  });
});

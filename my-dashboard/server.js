// server.js - Using native SQL Server client
import sql from 'mssql';
import express from 'express';

const app = express();
const PORT = 3001;

// Enable CORS
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', 'http://localhost:5173');
  res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type');
  next();
});

// Try multiple connection configurations
const configs = [
  // Config 1: Using localhost instead of computer name
  {
    server: 'localhost',
  database: 'StudentPerformanceDW',
  options: {
    encrypt: false,
    trustServerCertificate: true
  },
  authentication: {
    type: 'ntlm',
    options: {
      domain: '',
      userName: '', // leave empty for Windows user
      password: ''
      }
    }
  },
  // Config 2: Using IP address
  {
    name: '127.0.0.1',
    config: {
      server: '127.0.0.1\\SQLEXPRESS',
      database: 'StudentPerformanceDW',
      options: {
        trustedConnection: true,
        trustServerCertificate: true,
        encrypt: false,
        connectionTimeout: 30000
      }
    }
  },
  // Config 3: Using computer name without instance
  {
    name: 'Computer name only',
    config: {
      server: 'DESKTOP-UO7MC2L',
      database: 'StudentPerformanceDW',
      options: {
        instanceName: 'SQLEXPRESS',
        trustedConnection: true,
        trustServerCertificate: true,
        encrypt: false,
        connectionTimeout: 30000
      }
    }
  },
  // Config 4: Using .\SQLEXPRESS
  {
    name: '.\\SQLEXPRESS',
    config: {
      server: '.\\SQLEXPRESS',
      database: 'StudentPerformanceDW',
      options: {
        trustedConnection: true,
        trustServerCertificate: true,
        encrypt: false,
        connectionTimeout: 30000
      }
    }
  }
];

let activeConfig = null;

async function testAllConnections() {
  for (const cfg of configs) {
    try {
      console.log(`\n🔄 Trying ${cfg.name}...`);
      const pool = await sql.connect(cfg.config);
      const result = await pool.request().query('SELECT @@VERSION as version, DB_NAME() as db_name');
      console.log(`✅ SUCCESS with ${cfg.name}!`);
      console.log(`   Database: ${result.recordset[0].db_name}`);
      console.log(`   Version: ${result.recordset[0].version.substring(0, 60)}...`);
      await pool.close();
      activeConfig = cfg.config;
      return true;
    } catch (err) {
      console.log(`❌ Failed: ${err.message}`);
    }
  }
  return false;
}

// API endpoint for dimensions (filters)
app.get('/api/dimensions', async (req, res) => {
  if (!activeConfig) {
    return res.status(500).json({ error: 'Database not connected. Check server logs.' });
  }
  
  try {
    await sql.connect(activeConfig);
    
    const years = await sql.query`SELECT year_sk as id, year_name as name FROM DimYear ORDER BY year_sk`;
    const levels = await sql.query`SELECT level_sk as id, level_name as name FROM DimLevel ORDER BY level_sk`;
    const branches = await sql.query`SELECT branch_sk as id, branch_name as name FROM DimBranch ORDER BY branch_sk`;
    const subjects = await sql.query`SELECT content_sk as id, content_name as name FROM DimContent ORDER BY content_sk`;
    
    res.json({
      years: years.recordset,
      levels: levels.recordset,
      branches: branches.recordset,
      subjects: subjects.recordset
    });
    
    await sql.close();
  } catch (err) {
    console.error('Error in /api/dimensions:', err);
    res.status(500).json({ error: err.message });
  }
});

// API endpoint for statistics (KPIs)
app.get('/api/stats', async (req, res) => {
  if (!activeConfig) {
    return res.status(500).json({ error: 'Database not connected' });
  }
  
  const { year, level, branch } = req.query;
  
  let whereClause = 'WHERE 1=1';
  if (year && year !== 'all') whereClause += ` AND s.year_sk = ${year}`;
  if (level && level !== 'all') whereClause += ` AND f.level_sk = ${level}`;
  if (branch && branch !== 'all') whereClause += ` AND f.branch_sk = ${branch}`;
  
  try {
    await sql.connect(activeConfig);
    
    const result = await sql.query(`
      SELECT 
        ISNULL(SUM(f.nb_students), 0) as totalStudents,
        ISNULL(CAST(AVG(f.avg_grade) AS DECIMAL(10,2)), 0) as avgGrade,
        ISNULL(CAST(AVG(f.success_rate) AS DECIMAL(10,2)), 0) as avgSuccessRate,
        ISNULL(COUNT(DISTINCT f.content_sk), 0) as uniqueSubjects
      FROM Fact_StudentPerformance f
      JOIN DimSemester s ON f.semester_sk = s.semester_sk
      ${whereClause}
    `);
    
    res.json(result.recordset[0]);
    await sql.close();
  } catch (err) {
    console.error('Error in /api/stats:', err);
    res.status(500).json({ error: err.message });
  }
});

// API endpoint for pass rate by subject
app.get('/api/by-subject', async (req, res) => {
  if (!activeConfig) {
    return res.status(500).json({ error: 'Database not connected' });
  }
  
  const { year, level, branch } = req.query;
  
  let whereClause = 'WHERE 1=1';
  if (year && year !== 'all') whereClause += ` AND s.year_sk = ${year}`;
  if (level && level !== 'all') whereClause += ` AND f.level_sk = ${level}`;
  if (branch && branch !== 'all') whereClause += ` AND f.branch_sk = ${branch}`;
  
  try {
    await sql.connect(activeConfig);
    
    const result = await sql.query(`
      SELECT 
        c.content_name as subject,
        SUM(f.nb_students) as totalStudents,
        CAST(SUM(f.success_rate * f.nb_students) / NULLIF(SUM(f.nb_students), 0) AS DECIMAL(10,2)) as passRate
      FROM Fact_StudentPerformance f
      JOIN DimContent c ON f.content_sk = c.content_sk
      JOIN DimSemester s ON f.semester_sk = s.semester_sk
      ${whereClause}
      GROUP BY c.content_name
      ORDER BY passRate DESC
    `);
    
    res.json(result.recordset);
    await sql.close();
  } catch (err) {
    console.error('Error in /api/by-subject:', err);
    res.status(500).json({ error: err.message });
  }
});

// API endpoint for pass rate by level
app.get('/api/by-level', async (req, res) => {
  if (!activeConfig) {
    return res.status(500).json({ error: 'Database not connected' });
  }
  
  const { year, branch } = req.query;
  
  let whereClause = 'WHERE 1=1';
  if (year && year !== 'all') whereClause += ` AND s.year_sk = ${year}`;
  if (branch && branch !== 'all') whereClause += ` AND f.branch_sk = ${branch}`;
  
  try {
    await sql.connect(activeConfig);
    
    const result = await sql.query(`
      SELECT 
        l.level_name as level,
        SUM(f.nb_students) as totalStudents,
        CAST(SUM(f.success_rate * f.nb_students) / NULLIF(SUM(f.nb_students), 0) AS DECIMAL(10,2)) as passRate
      FROM Fact_StudentPerformance f
      JOIN DimLevel l ON f.level_sk = l.level_sk
      JOIN DimSemester s ON f.semester_sk = s.semester_sk
      ${whereClause}
      GROUP BY l.level_name, l.level_sk
      ORDER BY l.level_sk
    `);
    
    res.json(result.recordset);
    await sql.close();
  } catch (err) {
    console.error('Error in /api/by-level:', err);
    res.status(500).json({ error: err.message });
  }
});

// API endpoint for pass rate by branch
app.get('/api/by-branch', async (req, res) => {
  if (!activeConfig) {
    return res.status(500).json({ error: 'Database not connected' });
  }
  
  const { year, level } = req.query;
  
  let whereClause = 'WHERE 1=1';
  if (year && year !== 'all') whereClause += ` AND s.year_sk = ${year}`;
  if (level && level !== 'all') whereClause += ` AND f.level_sk = ${level}`;
  
  try {
    await sql.connect(activeConfig);
    
    const result = await sql.query(`
      SELECT 
        b.branch_name as branch,
        SUM(f.nb_students) as totalStudents,
        CAST(SUM(f.success_rate * f.nb_students) / NULLIF(SUM(f.nb_students), 0) AS DECIMAL(10,2)) as passRate
      FROM Fact_StudentPerformance f
      JOIN DimBranch b ON f.branch_sk = b.branch_sk
      JOIN DimSemester s ON f.semester_sk = s.semester_sk
      ${whereClause}
      GROUP BY b.branch_name
    `);
    
    res.json(result.recordset);
    await sql.close();
  } catch (err) {
    console.error('Error in /api/by-branch:', err);
    res.status(500).json({ error: err.message });
  }
});

// API endpoint for grade trend over years
app.get('/api/trend', async (req, res) => {
  if (!activeConfig) {
    return res.status(500).json({ error: 'Database not connected' });
  }
  
  const { level, branch } = req.query;
  
  let whereClause = 'WHERE 1=1';
  if (level && level !== 'all') whereClause += ` AND f.level_sk = ${level}`;
  if (branch && branch !== 'all') whereClause += ` AND f.branch_sk = ${branch}`;
  
  try {
    await sql.connect(activeConfig);
    
    const result = await sql.query(`
      SELECT 
        y.year_name as year,
        CAST(SUM(f.avg_grade * f.nb_students) / NULLIF(SUM(f.nb_students), 0) AS DECIMAL(10,2)) as avgGrade
      FROM Fact_StudentPerformance f
      JOIN DimSemester s ON f.semester_sk = s.semester_sk
      JOIN DimYear y ON s.year_sk = y.year_sk
      ${whereClause}
      GROUP BY y.year_name, y.year_sk
      ORDER BY y.year_sk
    `);
    
    res.json(result.recordset);
    await sql.close();
  } catch (err) {
    console.error('Error in /api/trend:', err);
    res.status(500).json({ error: err.message });
  }
});

// Start server
app.listen(PORT, async () => {
  console.log(`\n🚀 API Server running on http://localhost:${PORT}`);
  console.log(`   Endpoints available:\n`);
  console.log(`   📊 Filters:    GET /api/dimensions`);
  console.log(`   📈 KPIs:       GET /api/stats?year=1&level=2&branch=3`);
  console.log(`   📋 By Subject: GET /api/by-subject?year=1`);
  console.log(`   📊 By Level:   GET /api/by-level?year=1`);
  console.log(`   🏢 By Branch:  GET /api/by-branch?year=1`);
  console.log(`   📉 Trend:      GET /api/trend?level=2`);
  
  console.log('\n🔍 Testing multiple connection configurations...');
  const connected = await testAllConnections();
  
  if (connected) {
    console.log('\n✅ Database connection established! Ready to accept requests.');
  } else {
    console.log('\n❌ No connection configuration worked.');
    console.log('\n💡 Manual fix: Try running SQL Server Configuration Manager and:');
    console.log('   1. Enable TCP/IP protocol');
    console.log('   2. Set TCP Port to 1433 in IPAll section');
    console.log('   3. Restart SQL Server service');
    console.log('   4. Run: npm install tedious');
  }
});
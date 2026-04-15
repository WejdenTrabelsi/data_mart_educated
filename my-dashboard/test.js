import sql from 'mssql';

const config = { server: 'localhost',
  database: 'StudentPerformanceDW',
  user: 'sa',
  password: 'yourpassword',
  options: {
    encrypt: false,
    trustServerCertificate: true}
};

async function test() {
  try {
    await sql.connect(config);
    console.log('✅ Connected!');
  } catch (err) {
    console.log(err);
  }
}

test();
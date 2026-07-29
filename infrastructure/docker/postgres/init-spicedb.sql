# Create SpiceDB datastore DB alongside PorterChain app DB (local compose).
SELECT 'CREATE DATABASE spicedb'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'spicedb')\gexec

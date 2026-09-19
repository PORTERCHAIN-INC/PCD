-- Create SpiceDB datastore DB alongside PorterChain app DB (local compose).
-- Note: docker entrypoint runs *.sql via psql; use -- comments only (not #).
SELECT 'CREATE DATABASE spicedb'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'spicedb')\gexec

-- Run this once as neondb_owner in the Neon SQL Editor.
-- Replace the example password before running it. Never commit the real password.

CREATE ROLE streamlit_reader
  LOGIN
  PASSWORD 'REPLACE_WITH_A_LONG_RANDOM_PASSWORD'
  NOSUPERUSER
  NOCREATEDB
  NOCREATEROLE
  NOINHERIT;

GRANT CONNECT ON DATABASE neondb TO streamlit_reader;
GRANT USAGE ON SCHEMA staging, warehouse TO streamlit_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA staging, warehouse TO streamlit_reader;

-- Preserve read access when the owner creates or replaces tables later.
ALTER DEFAULT PRIVILEGES FOR ROLE neondb_owner IN SCHEMA staging
  GRANT SELECT ON TABLES TO streamlit_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE neondb_owner IN SCHEMA warehouse
  GRANT SELECT ON TABLES TO streamlit_reader;

-- Defense in depth: even an accidentally granted write privilege cannot be used
-- while this role's sessions remain read-only.
ALTER ROLE streamlit_reader SET default_transaction_read_only = on;

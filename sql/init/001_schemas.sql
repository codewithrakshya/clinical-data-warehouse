CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS warehouse;

COMMENT ON SCHEMA staging IS
  'Source-normalized clinical data awaiting validation and transformation.';
COMMENT ON SCHEMA warehouse IS
  'Curated dimensions and facts intended for analytics.';

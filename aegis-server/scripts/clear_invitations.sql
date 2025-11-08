-- Clear all invitation tokens
-- Run this to remove old SHA256-hashed tokens before generating new Argon2-hashed tokens
-- Usage: psql -U aegis_user -d aegis_db -f clear_invitations.sql

DELETE FROM invitations;

SELECT 'All invitations cleared successfully!' AS status;
SELECT COUNT(*) AS remaining_invitations FROM invitations;

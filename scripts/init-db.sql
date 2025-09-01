-- DevCycle Database Initialization Script
-- This script runs when the PostgreSQL container is first created

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Set timezone
SET timezone = 'UTC';

-- Create default roles
INSERT INTO roles (id, name, description, is_active) VALUES
    ('admin', 'Administrator', 'System administrator with full access', true),
    ('user', 'User', 'Standard user with basic access', true),
    ('moderator', 'Moderator', 'Content moderator with limited admin access', true)
ON CONFLICT (id) DO NOTHING;

-- Create default permissions
INSERT INTO permissions (id, name, description, resource, action, is_active) VALUES
    ('read:own', 'Read Own Data', 'Read own user data', 'users', 'read', true),
    ('write:own', 'Write Own Data', 'Update own user data', 'users', 'write', true),
    ('read:public', 'Read Public Data', 'Read public data', 'public', 'read', true),
    ('write:public', 'Write Public Data', 'Write public data', 'public', 'write', true),
    ('read:*', 'Read All Data', 'Read all data in the system', 'system', 'read', true),
    ('write:*', 'Write All Data', 'Write all data in the system', 'system', 'write', true),
    ('admin:*', 'All Admin Operations', 'Perform all administrative operations', 'system', 'admin', true),
    ('moderate:content', 'Moderate Content', 'Moderate user-generated content', 'content', 'moderate', true),
    ('ban:users', 'Ban Users', 'Ban or suspend user accounts', 'users', 'ban', true),
    ('manage:users', 'Manage Users', 'Manage user accounts', 'users', 'manage', true),
    ('manage:roles', 'Manage Roles', 'Manage roles and permissions', 'roles', 'manage', true),
    ('system:config', 'System Configuration', 'Modify system configuration', 'system', 'config', true)
ON CONFLICT (id) DO NOTHING;

-- Assign permissions to roles
INSERT INTO role_permissions (role_id, permission_id) VALUES
    -- Admin role gets all permissions
    ('admin', 'read:own'),
    ('admin', 'write:own'),
    ('admin', 'read:public'),
    ('admin', 'write:public'),
    ('admin', 'read:*'),
    ('admin', 'write:*'),
    ('admin', 'admin:*'),
    ('admin', 'moderate:content'),
    ('admin', 'ban:users'),
    ('admin', 'manage:users'),
    ('admin', 'manage:roles'),
    ('admin', 'system:config'),

    -- User role gets basic permissions
    ('user', 'read:own'),
    ('user', 'write:own'),
    ('user', 'read:public'),

    -- Moderator role gets moderation permissions
    ('moderator', 'read:*'),
    ('moderator', 'write:public'),
    ('moderator', 'moderate:content'),
    ('moderator', 'ban:users')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Create a default admin user (password: admin123)
-- Note: In production, this should be changed immediately
INSERT INTO users (
    id, username, email, hashed_password, first_name, last_name,
    is_active, is_verified, roles, created_at, updated_at
) VALUES (
    uuid_generate_v4(),
    'admin',
    'admin@devcycle.dev',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8QqHh6e', -- admin123
    'System',
    'Administrator',
    true,
    true,
    ARRAY['admin'],
    NOW(),
    NOW()
) ON CONFLICT (username) DO NOTHING;

-- Create a default test user (password: user123)
INSERT INTO users (
    id, username, email, hashed_password, first_name, last_name,
    is_active, is_verified, roles, created_at, updated_at
) VALUES (
    uuid_generate_v4(),
    'user',
    'user@devcycle.dev',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8QqHh6e', -- user123
    'Test',
    'User',
    true,
    true,
    ARRAY['user'],
    NOW(),
    NOW()
) ON CONFLICT (username) DO NOTHING;

-- Database initialization complete
-- System uses structlog for logging instead of database audit logs

-- Grant necessary permissions to the postgres user for development
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

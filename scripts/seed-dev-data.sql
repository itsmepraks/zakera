-- Seed development data for Zakera
-- Creates sample conversations, users, and test data

-- Clean existing data (development only!)
TRUNCATE TABLE conversations CASCADE;
TRUNCATE TABLE users CASCADE;

-- Create test users
INSERT INTO users (id, email, username, hashed_password, role, created_at)
VALUES
    ('user-1', 'admin@zakera.local', 'admin', '$2b$12$...', 'admin', NOW()),
    ('user-2', 'demo@zakera.local', 'demo', '$2b$12$...', 'user', NOW()),
    ('user-3', 'test@zakera.local', 'test', '$2b$12$...', 'user', NOW());

-- Create sample conversations
INSERT INTO conversations (id, user_id, title, created_at, updated_at, status)
VALUES
    ('conv-1', 'user-1', 'Introduction to Quantum Computing', NOW() - INTERVAL '5 days', NOW() - INTERVAL '2 days', 'active'),
    ('conv-2', 'user-1', 'Python Best Practices', NOW() - INTERVAL '3 days', NOW() - INTERVAL '1 day', 'active'),
    ('conv-3', 'user-2', 'Machine Learning Basics', NOW() - INTERVAL '7 days', NOW() - INTERVAL '3 days', 'active'),
    ('conv-4', 'user-2', 'Docker Tutorial', NOW() - INTERVAL '10 days', NOW() - INTERVAL '5 days', 'archived'),
    ('conv-5', 'user-3', 'React Hooks Guide', NOW() - INTERVAL '2 days', NOW() - INTERVAL '1 hour', 'active');

-- Create branches for conversations
INSERT INTO branches (id, conversation_id, name, parent_id, created_at, last_activity)
VALUES
    ('branch-main-1', 'conv-1', 'main', NULL, NOW() - INTERVAL '5 days', NOW() - INTERVAL '2 days'),
    ('branch-exp-1', 'conv-1', 'experiment', 'branch-main-1', NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days'),
    ('branch-main-2', 'conv-2', 'main', NULL, NOW() - INTERVAL '3 days', NOW() - INTERVAL '1 day'),
    ('branch-main-3', 'conv-3', 'main', NULL, NOW() - INTERVAL '7 days', NOW() - INTERVAL '3 days'),
    ('branch-main-4', 'conv-4', 'main', NULL, NOW() - INTERVAL '10 days', NOW() - INTERVAL '5 days'),
    ('branch-main-5', 'conv-5', 'main', NULL, NOW() - INTERVAL '2 days', NOW() - INTERVAL '1 hour');

-- Create sample messages
INSERT INTO messages (id, conversation_id, branch_id, role, content, created_at, model)
VALUES
    ('msg-1', 'conv-1', 'branch-main-1', 'user', 'What is quantum computing?', NOW() - INTERVAL '5 days', NULL),
    ('msg-2', 'conv-1', 'branch-main-1', 'assistant', 'Quantum computing is...', NOW() - INTERVAL '5 days', 'gpt-4'),
    ('msg-3', 'conv-1', 'branch-main-1', 'user', 'Can you explain qubits?', NOW() - INTERVAL '4 days', NULL),
    ('msg-4', 'conv-1', 'branch-main-1', 'assistant', 'Qubits are...', NOW() - INTERVAL '4 days', 'gpt-4'),
    ('msg-5', 'conv-2', 'branch-main-2', 'user', 'What are Python decorators?', NOW() - INTERVAL '3 days', NULL),
    ('msg-6', 'conv-2', 'branch-main-2', 'assistant', 'Decorators are...', NOW() - INTERVAL '3 days', 'gpt-3.5-turbo');

-- Add tags
INSERT INTO conversation_tags (conversation_id, tag)
VALUES
    ('conv-1', 'physics'),
    ('conv-1', 'science'),
    ('conv-2', 'programming'),
    ('conv-2', 'python'),
    ('conv-3', 'ai'),
    ('conv-3', 'ml'),
    ('conv-5', 'frontend'),
    ('conv-5', 'react');

-- Set conversation metadata
UPDATE conversations
SET metadata = jsonb_build_object(
    'model', 'gpt-4',
    'pinned', true,
    'starred', true
)
WHERE id = 'conv-1';

UPDATE conversations
SET metadata = jsonb_build_object(
    'model', 'gpt-3.5-turbo',
    'starred', true
)
WHERE id = 'conv-2';

COMMIT;

SELECT 'Development data seeded successfully!' as status;

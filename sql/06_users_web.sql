USE [StudentPerformanceDW];
GO

-- =============================================
-- USERS + ROLES TABLES (Professor requirement)
-- =============================================

-- 1. Users table
CREATE TABLE dbo.Users (
    user_id INT IDENTITY(1,1) PRIMARY KEY,
    username NVARCHAR(50) NOT NULL UNIQUE,
    email NVARCHAR(100) NOT NULL UNIQUE,
    password_hash NVARCHAR(255) NOT NULL,
    full_name NVARCHAR(100) NOT NULL,
    role NVARCHAR(20) NOT NULL CHECK (role IN ('director', 'parent')),  -- exactly two roles
    student_id INT NULL,                    -- for parents only (link to their kid later)
    created_at DATETIME2 DEFAULT GETDATE(),
    last_login DATETIME2 NULL
);

-- 2. Simple index for fast login
CREATE NONCLUSTERED INDEX IDX_Users_Email ON dbo.Users(email);

-- 3. Insert demo users (you can change passwords later)
INSERT INTO dbo.Users (username, email, password_hash, full_name, role)
VALUES 
    ('director', 'director@lycee.tn', '$2b$12$exampleHashHereReplaceMeWithRealBcrypt', 'M. Ahmed Ben Salem - Directeur', 'director'),
    ('parent1', 'parent1@lycee.tn', '$2b$12$exampleHashHereReplaceMeWithRealBcrypt', 'Mme. Leila Trabelsi - Parent', 'parent'),
    ('parent2', 'parent2@lycee.tn', '$2b$12$exampleHashHereReplaceMeWithRealBcrypt', 'M. Karim Ben Ali - Parent', 'parent');

PRINT '✅ Users table + demo accounts created successfully!';
GO
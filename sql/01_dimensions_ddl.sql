USE StudentPerformanceDW;
GO

CREATE TABLE DimYear (
    year_sk INT IDENTITY(1,1) PRIMARY KEY,
    year_natural_key UNIQUEIDENTIFIER NOT NULL,
    year_name VARCHAR(20) NOT NULL
);

CREATE TABLE DimSemester (
    semester_sk INT IDENTITY(1,1) PRIMARY KEY,
    semester_code VARCHAR(2) NOT NULL,
    year_sk INT NOT NULL,
    FOREIGN KEY (year_sk) REFERENCES DimYear(year_sk)
);

CREATE TABLE DimLevel (
    level_sk INT IDENTITY(1,1) PRIMARY KEY,
    level_natural_key UNIQUEIDENTIFIER NOT NULL,
    level_name VARCHAR(50) NOT NULL
);

CREATE TABLE DimBranch (
    branch_sk INT IDENTITY(1,1) PRIMARY KEY,
    branch_name VARCHAR(30) NOT NULL
);

CREATE TABLE DimContent (
    content_sk INT IDENTITY(1,1) PRIMARY KEY,
    content_natural_key UNIQUEIDENTIFIER NOT NULL,
    content_name VARCHAR(100) NOT NULL
);

PRINT '✅ All dimension tables created successfully';
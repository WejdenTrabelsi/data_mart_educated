USE StudentPerformanceDW;
GO

CREATE TABLE Fact_StudentPerformance (
    content_sk      INT NOT NULL,
    level_sk        INT NOT NULL,
    branch_sk       INT NOT NULL,
    semester_sk     INT NOT NULL,
    avg_grade       DECIMAL(5,2) NOT NULL,
    success_rate    DECIMAL(5,2) NOT NULL,
    nb_students     INT NOT NULL,
    
    PRIMARY KEY (content_sk, level_sk, branch_sk, semester_sk),
    
    FOREIGN KEY (content_sk)  REFERENCES DimContent(content_sk),
    FOREIGN KEY (level_sk)    REFERENCES DimLevel(level_sk),
    FOREIGN KEY (branch_sk)   REFERENCES DimBranch(branch_sk),
    FOREIGN KEY (semester_sk) REFERENCES DimSemester(semester_sk)
);

PRINT '✅ Fact table created successfully';
-- =============================================
-- KPI VIEWS FOR METABASE (Student Performance) - FIXED
-- =============================================

USE [StudentPerformanceDW];
GO

-- 1. Full readable Performance view (best for Metabase)
CREATE OR ALTER VIEW vw_StudentPerformance
AS
SELECT 
    f.avg_grade,
    f.success_rate,
    f.nb_students,
    dy.year_name,
    ds.semester_code,
    dl.level_name,
    db.branch_name,
    dc.content_name,
    -- Extra useful columns for filtering
    dl.level_natural_key,
    dc.content_natural_key
FROM Fact_StudentPerformance f
JOIN DimSemester ds       ON f.semester_sk      = ds.semester_sk
JOIN DimYear dy           ON ds.year_sk         = dy.year_sk          -- ← FIXED: join through semester
JOIN DimLevel dl          ON f.level_sk         = dl.level_sk
JOIN DimBranch db         ON f.branch_sk        = db.branch_sk
JOIN DimContent dc        ON f.content_sk       = dc.content_sk;
GO

-- 2. Summary KPI view (for metric cards)
CREATE OR ALTER VIEW vw_KPI_Performance_Summary
AS
SELECT 
    COUNT(*) AS total_subjects,
    AVG(avg_grade) AS overall_avg_grade,
    AVG(success_rate) AS overall_success_rate,
    SUM(nb_students) AS total_evaluations
FROM vw_StudentPerformance;
GO

PRINT '✅ KPI Views created successfully!';
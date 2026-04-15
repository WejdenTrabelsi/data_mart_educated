SELECT TOP 30 
    c.content_name AS Matière,
    l.level_name AS Niveau,
    b.branch_name AS Branche,
    y.year_name AS [Année Scolaire],
    s.semester_code AS Semestre,
    f.avg_grade AS Moyenne,
    ROUND(f.success_rate, 2) AS [Taux de Réussite (%)],
    f.nb_students AS [Nombre d'Élèves]
FROM Fact_StudentPerformance f
JOIN DimContent c ON f.content_sk = c.content_sk
JOIN DimLevel l ON f.level_sk = l.level_sk
JOIN DimBranch b ON f.branch_sk = b.branch_sk
JOIN DimSemester s ON f.semester_sk = s.semester_sk
JOIN DimYear y ON s.year_sk = y.year_sk
ORDER BY f.success_rate DESC, f.avg_grade DESC;
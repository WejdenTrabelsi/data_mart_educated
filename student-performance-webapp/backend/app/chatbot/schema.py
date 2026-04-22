"""
Static schema description for the SQL agent.
Local LLMs need explicit, high-quality schema context.
"""

WAREHOUSE_SCHEMA = """
You have access to a SQL Server data warehouse with a star schema.

── FACT TABLE ──
Fact_StudentPerformance
  - fact_id          INT PRIMARY KEY
  - semester_sk    INT → DimSemester
  - level_sk        INT → DimLevel
  - branch_sk        INT → DimBranch
  - content_sk       INT → DimContent
  - avg_grade        DECIMAL(4,2)    -- Average grade (0-20 scale)
  - success_rate     DECIMAL(5,2)    -- Percentage (0-100)
  - nb_students      INT             -- Number of students

── DIMENSION TABLES ──
DimYear        : year_sk, year_natural_key, year_name
DimSemester    : semester_sk, semester_code (S1/S2/S3), year_sk → DimYear
DimLevel       : level_sk, level_natural_key, level_name
DimBranch      : branch_sk, branch_name
DimContent     : content_sk, content_natural_key, content_name
── JOIN PATHS ──
Fact → DimSemester  via semester_sk
Fact → DimLevel     via level_sk
Fact → DimBranch    via branch_sk
Fact → DimContent   via content_sk
DimSemester → DimYear via year_sk
── IMPORTANT RULES ──
1. Only write SELECT queries. NEVER INSERT, UPDATE, DELETE, DROP.
2. Use JOINs, not subqueries, when possible.
3. Aggregate with GROUP BY when selecting dimensions + measures.
4. Filter years with DimYear.year_value.
5. Always use table aliases: f for fact, y for year, s for semester, etc.
"""

SQL_EXAMPLES = """
Q: What was the average success rate in 2024?
A: SELECT AVG(f.success_rate) AS avg_success_rate
   FROM Fact_StudentPerformance f
   JOIN DimYear y ON f.year_id = y.year_id
   WHERE y.year_value = 2024;

Q: Compare success rates by branch for Spring 2024.
A: SELECT b.branch_name, AVG(f.success_rate) AS avg_success_rate
   FROM Fact_StudentPerformance f
   JOIN DimBranch b ON f.branch_id = b.branch_id
   JOIN DimSemester s ON f.semester_id = s.semester_id
   JOIN DimYear y ON f.year_id = y.year_id
   WHERE y.year_value = 2024 AND s.semester_name = 'Spring'
   GROUP BY b.branch_name
   ORDER BY avg_success_rate DESC;

Q: How many students are in each level?
A: SELECT l.level_name, SUM(f.nb_students) AS total_students
   FROM Fact_StudentPerformance f
   JOIN DimLevel l ON f.level_id = l.level_id
   GROUP BY l.level_name;
"""
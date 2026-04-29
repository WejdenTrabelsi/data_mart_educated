"""
Static schema description for the SQL agent.
Local LLMs need explicit, high-quality schema context.
"""

WAREHOUSE_SCHEMA = """
You have access to a SQL Server data warehouse.

── MATERIALIZED VIEWS (pre-aggregated, easiest for dashboard questions) ──
mvw_StudentPerformance
  - year_name VARCHAR, semester_code VARCHAR, level_name VARCHAR, branch_name VARCHAR, content_name VARCHAR
  - avg_grade DECIMAL(4,2), success_rate DECIMAL(5,2)
  - One row per dimension combination

mvw_StudentAttendance
  - year_name VARCHAR, semester_code VARCHAR, month_name VARCHAR, day_name VARCHAR, zone_description VARCHAR
  - student_full_name_arab VARCHAR, nb_absence INT, is_school_day BIT, rain_flag BIT, temp_band VARCHAR
  - One row per absence record

── STAR SCHEMA ──
Fact_StudentPerformance
  - fact_id INT PRIMARY KEY
  - semester_sk INT → DimSemester
  - level_sk    INT → DimLevel
  - branch_sk   INT → DimBranch
  - content_sk  INT → DimContent
  - avg_grade    DECIMAL(4,2)    -- 0-20 scale
  - success_rate DECIMAL(5,2)    -- 0-100
  - nb_students  INT

DimYear     : year_sk, year_natural_key, year_name
DimSemester : semester_sk, semester_code (S1/S2/S3), year_sk → DimYear
DimLevel    : level_sk, level_natural_key, level_name
DimBranch   : branch_sk, branch_name
DimContent  : content_sk, content_natural_key, content_name

── JOIN PATHS ──
Fact → DimSemester via semester_sk → DimYear via year_sk
Fact → DimLevel    via level_sk
Fact → DimBranch   via branch_sk
Fact → DimContent  via content_sk

── RULES ──
1. Only SELECT. NEVER INSERT/UPDATE/DELETE/DROP.
2. Prefer mvw_StudentPerformance / mvw_StudentAttendance for simple aggregations.
3. Use JOINs for star schema queries.
4. GROUP BY dimensions when aggregating.
5. Filter years with year_name (e.g., '2024').
6. Always use aliases: f for fact, y for year, s for semester, etc.
"""

SQL_EXAMPLES = """
Q: What was the average success rate in 2024?
A: SELECT AVG(success_rate) AS avg_success_rate
   FROM mvw_StudentPerformance
   WHERE year_name = '2024';

Q: Compare success rates by branch for Spring 2024.
A: SELECT branch_name, AVG(success_rate) AS avg_success_rate
   FROM mvw_StudentPerformance
   WHERE year_name = '2024' AND semester_code = 'S2'
   GROUP BY branch_name
   ORDER BY avg_success_rate DESC;

Q: How many students are in each level?
A: SELECT l.level_name, SUM(f.nb_students) AS total_students
   FROM Fact_StudentPerformance f
   JOIN DimLevel l ON f.level_sk = l.level_sk
   GROUP BY l.level_name;

Q: Which zone has the most absences?
A: SELECT TOP 5 zone_description, COUNT(*) * MAX(nb_absence) AS total_absences
   FROM mvw_StudentAttendance
   GROUP BY zone_description
   ORDER BY total_absences DESC;
"""
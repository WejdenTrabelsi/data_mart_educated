# schema.py
from sqlalchemy import text
from sqlalchemy.engine import Engine

WAREHOUSE_SCHEMA_TEMPLATE = """
You have access to a SQL Server data warehouse.

── MATERIALIZED VIEWS ──
mvw_StudentPerformance
  - year_name VARCHAR, semester_code VARCHAR, level_name VARCHAR, branch_name VARCHAR, content_name VARCHAR
  - avg_grade DECIMAL(4,2), success_rate DECIMAL(5,2)

mvw_StudentAttendance
  - year_name VARCHAR, semester_code VARCHAR, month_name VARCHAR, day_name VARCHAR, zone_description VARCHAR
  - student_full_name_arab VARCHAR, nb_absence INT, is_school_day BIT, rain_flag BIT, temp_band VARCHAR

── ACTUAL VALUES IN DATABASE (use EXACTLY these strings in WHERE clauses) ──
Years (year_name):       {years}
Semesters (semester_code): {semesters}
Levels (level_name):     {levels}
Branches (branch_name):  {branches}

── STAR SCHEMA ──
Fact_StudentPerformance
  - fact_id, semester_sk, level_sk, branch_sk, content_sk
  - avg_grade DECIMAL(4,2), success_rate DECIMAL(5,2), nb_students INT

DimYear, DimSemester, DimLevel, DimBranch, DimContent (join via _sk keys)

── RULES ──
1. Only SELECT. NEVER INSERT/UPDATE/DELETE/DROP.
2. Prefer mvw_StudentPerformance / mvw_StudentAttendance for simple aggregations.
3. Filter year with year_name using EXACT values listed above (e.g. '2023-2024' not '2024').
4. Filter level with level_name using EXACT values listed above.
5. If the user mentions a partial name (e.g. '4ème éco'), match to the closest EXACT value above.
6. GROUP BY dimensions when aggregating.
7. Always alias: f=fact, y=year, s=semester, etc.
"""

def build_schema(engine: Engine) -> str:
    with engine.connect() as conn:
        years     = [r[0] for r in conn.execute(text("SELECT year_name FROM DimYear ORDER BY year_sk")).fetchall()]
        semesters = [r[0] for r in conn.execute(text("SELECT semester_code FROM DimSemester GROUP BY semester_code ORDER BY semester_code")).fetchall()]
        levels    = [r[0] for r in conn.execute(text("SELECT level_name FROM DimLevel ORDER BY level_sk")).fetchall()]
        branches  = [r[0] for r in conn.execute(text("SELECT branch_name FROM DimBranch ORDER BY branch_name")).fetchall()]

    return WAREHOUSE_SCHEMA_TEMPLATE.format(
        years=", ".join(f"'{y}'" for y in years),
        semesters=", ".join(f"'{s}'" for s in semesters),
        levels=", ".join(f"'{l}'" for l in levels),
        branches=", ".join(f"'{b}'" for b in branches),
    )



SQL_EXAMPLES = """
Q: Quel était le taux de réussite moyen en 2023-2024 ?
A: SELECT AVG(success_rate) AS avg_success_rate
   FROM mvw_StudentPerformance
   WHERE year_name = '2023-2024';

Q: Comparez les taux de réussite par branche pour le semestre S2 de 2023-2024.
A: SELECT branch_name, AVG(success_rate) AS avg_success_rate
   FROM mvw_StudentPerformance
   WHERE year_name = '2023-2024' AND semester_code = 'S2'
   GROUP BY branch_name
   ORDER BY avg_success_rate DESC;

Q: Combien d'étudiants y a-t-il dans chaque niveau ?
A: SELECT l.level_name, SUM(f.nb_students) AS total_students
   FROM Fact_StudentPerformance f
   JOIN DimLevel l ON f.level_sk = l.level_sk
   GROUP BY l.level_name;

Q: Quelle zone compte le plus d'absences ?
A: SELECT TOP 5 zone_description, COUNT(*) * MAX(nb_absence) AS total_absences
   FROM mvw_StudentAttendance
   GROUP BY zone_description
   ORDER BY total_absences DESC;
"""
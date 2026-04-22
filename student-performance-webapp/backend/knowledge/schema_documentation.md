# Data Warehouse Schema Documentation

## Star Schema Overview
The warehouse follows a star schema optimized for OLAP queries:
- **1 Fact Table**: Fact_StudentPerformance
- **5 Dimension Tables**: DimYear, DimSemester, DimLevel, DimBranch, DimContent

## Fact_StudentPerformance
This is the central table containing quantitative metrics. Each row represents the aggregated performance for a unique combination of year, semester, level, branch, and content.

## Dimensions
Dimensions provide descriptive context:
- **DimYear**: Academic year (e.g., 2023, 2024)
- **DimSemester**: Academic period (Fall, Spring, S1, S2)
- **DimLevel**: Academic level or grade (Bachelor 1, Master 2, etc.)
- **DimBranch**: Field of study (Computer Science, Mathematics, etc.)
- **DimContent**: Specific course or subject matter

## Incremental Loading
The ETL pipeline supports incremental loads. New data is appended daily, and historical aggregates are recalculated if source corrections are detected.
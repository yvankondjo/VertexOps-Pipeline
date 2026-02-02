with src as (
  select * from {{ source('raw', 'raw_resume_screening') }}
)

select
  safe_cast(years_experience as int64) as years_experience,
  safe_cast(skills_match_score as float64) as skills_match_score,
  lower(trim(education_level)) as education_level,
  safe_cast(project_count as int64) as project_count,
  safe_cast(resume_length as int64) as resume_length,
  safe_cast(github_activity as int64) as github_activity,


  case
    when lower(trim(cast(shortlisted as string))) in ('yes', 'true', '1') then 'yes'
    when lower(trim(cast(shortlisted as string))) in ('no', 'false', '0') then 'no'
    else null
  end as shortlisted_raw
from src
where lower(trim(cast(shortlisted as string))) in ('yes', 'true', '1', 'no', 'false', '0')

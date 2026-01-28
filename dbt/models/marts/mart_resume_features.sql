select
  years_experience,
  skills_match_score,
  education_level,
  project_count,
  resume_length,
  github_activity,
  case
    when shortlisted_raw = 'yes' then 1
    when shortlisted_raw = 'no'  then 0
    else null
  end as is_shortlisted
from {{ ref('stg_resume_screening') }}
where shortlisted_raw in ('yes', 'no')

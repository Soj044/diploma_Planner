//////////////////////////////////////////////////////////////
// PLANNER SERVICE DATABASE (FastAPI + OR-Tools / CP-SAT)
//////////////////////////////////////////////////////////////

Project planner_service {
  database_type: "PostgreSQL"
  Note: '''
  БД сервиса планирования.
  Здесь нет "истинных" сотрудников и задач.
  Здесь хранятся запуски расчета, снапшоты входных данных,
  eligibility, scores, предложения назначений и диагностика.
  '''
}

Enum plan_run_status {
  created
  running
  completed
  failed
  partially_applied
  approved
}

Enum proposal_status {
  proposed
  approved
  rejected
  applied
}

Enum replanning_event_type {
  new_task
  leave_added
  leave_updated
  employee_unavailable
  deadline_changed
  task_cancelled
  manual_replan
}

Table plan_runs {
  id bigserial [pk]
  external_uuid uuid [not null, unique]
  initiated_by_user_id bigint [not null, note: 'Логическая ссылка на core.users.id']
  period_start date [not null]
  period_end date [not null]
  status plan_run_status [not null, default: 'created']
  algorithm_name varchar(100) [not null, default: 'cp_sat']
  algorithm_version varchar(100) [not null]
  objective_summary text
  objective_weights_json jsonb
  time_estimates_json jsonb [not null, default: '{}', note: 'task_id -> source/effective/manual/rules/history estimate metadata']
  created_at timestamptz [not null]
  started_at timestamptz
  finished_at timestamptz

  Note: '''
  Один запуск планирования на конкретный период.
  В MVP persisted artifact slice включает planner-side оценки времени:
  source=manual|history|blended|rules + effective_hours.
  '''
  
  Indexes {
    external_uuid
    status
    (period_start, period_end)
  }
}

Table plan_input_snapshots {
  id bigserial [pk]
  plan_run_id bigint [not null, ref: > plan_runs.id]
  source_hash varchar(255) [not null]
  snapshot_json jsonb [not null]
  created_at timestamptz [not null]

  Note: '''
  Полный срез входных данных,
  на которых строился конкретный план.
  Нужен для воспроизводимости и отладки.
  '''
  
  Indexes {
    plan_run_id
    source_hash
  }
}

Table candidate_eligibility {
  id bigserial [pk]
  plan_run_id bigint [not null, ref: > plan_runs.id]
  external_task_id bigint [not null, note: 'Логическая ссылка на core.tasks.id']
  external_employee_id bigint [not null, note: 'Логическая ссылка на core.employees.id']
  is_eligible boolean [not null]
  hard_constraints_passed boolean [not null]
  rejection_reason_code varchar(100)
  rejection_reason_details text
  created_at timestamptz [not null]

  Note: '''
  Результат этапа "отбор допустимых сотрудников".
  '''
  
  Indexes {
    plan_run_id
    (plan_run_id, external_task_id, external_employee_id) [unique]
    external_task_id
    external_employee_id
  }
}

Table candidate_scores {
  id bigserial [pk]
  plan_run_id bigint [not null, ref: > plan_runs.id]
  external_task_id bigint [not null, note: 'Логическая ссылка на core.tasks.id']
  external_employee_id bigint [not null, note: 'Логическая ссылка на core.employees.id']
  skill_score decimal(8,4) [not null, default: 0]
  availability_score decimal(8,4) [not null, default: 0]
  load_balance_score decimal(8,4) [not null, default: 0]
  historical_score decimal(8,4) [not null, default: 0]
  llm_score decimal(8,4) [not null, default: 0]
  final_score decimal(8,4) [not null, default: 0]
  explanation_text text
  created_at timestamptz [not null]

  Note: '''
  Детальный скоринг пары employee-task.
  llm_score можно использовать как вклад AI-модуля.
  '''
  
  Indexes {
    plan_run_id
    (plan_run_id, external_task_id, external_employee_id) [unique]
    final_score
  }
}

Table assignment_proposals {
  id bigserial [pk]
  plan_run_id bigint [not null, ref: > plan_runs.id]
  external_task_id bigint [not null, note: 'Логическая ссылка на core.tasks.id']
  external_employee_id bigint [not null, note: 'Логическая ссылка на core.employees.id']
  proposal_rank int [not null, default: 1]
  is_selected boolean [not null, default: true]
  planned_hours int [not null]
  start_date date [not null]
  end_date date [not null]
  score decimal(8,4) [not null]
  explanation_text text
  status proposal_status [not null, default: 'proposed']
  reviewed_by_user_id bigint [note: 'Логическая ссылка на core.users.id']
  reviewed_at timestamptz
  created_at timestamptz [not null]

  Note: '''
  Предложения, которые вернул оптимизатор.
  Это еще не финальные назначения в основной БД.
  '''
  
  Indexes {
    plan_run_id
    external_task_id
    external_employee_id
    status
  }
}

Table unassigned_tasks {
  id bigserial [pk]
  plan_run_id bigint [not null, ref: > plan_runs.id]
  external_task_id bigint [not null, note: 'Логическая ссылка на core.tasks.id']
  reason_code varchar(100) [not null]
  reason_details text
  created_at timestamptz [not null]

  Note: '''
  Задачи, которые не удалось назначить.
  '''
  
  Indexes {
    plan_run_id
    external_task_id
  }
}

Table constraint_violations {
  id bigserial [pk]
  plan_run_id bigint [not null, ref: > plan_runs.id]
  violation_type varchar(100) [not null]
  severity varchar(50) [not null, note: 'info | warning | error']
  external_task_id bigint [note: 'Логическая ссылка на core.tasks.id']
  external_employee_id bigint [note: 'Логическая ссылка на core.employees.id']
  details text
  created_at timestamptz [not null]

  Note: '''
  Диагностика нарушений и конфликтов.
  Особенно полезна при отладке и объяснении,
  почему какой-то план не был найден или оказался неполным.
  '''
  
  Indexes {
    plan_run_id
    violation_type
    severity
  }
}

Table replanning_events {
  id bigserial [pk]
  plan_run_id bigint [ref: > plan_runs.id]
  event_type replanning_event_type [not null]
  source_entity_type varchar(100) [not null]
  source_entity_id bigint [not null]
  payload_json jsonb
  created_at timestamptz [not null]

  Note: '''
  События, из-за которых потребовался пересчет плана.
  '''
  
  Indexes {
    plan_run_id
    event_type
    created_at
  }
}

Table solver_statistics {
  id bigserial [pk]
  plan_run_id bigint [not null, unique, ref: > plan_runs.id]
  solver_status varchar(100) [not null]
  objective_value decimal(16,4)
  best_bound decimal(16,4)
  wall_time_ms int
  conflicts int
  branches int
  created_at timestamptz [not null]

  Note: '''
  Технические метрики solver-а.
  Для диплома это очень полезная таблица:
  можно сравнивать качество и время работы алгоритма.
  '''
}

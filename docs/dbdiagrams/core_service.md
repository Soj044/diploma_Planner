//////////////////////////////////////////////////////////////
// CORE SERVICE DATABASE (Django + DRF)
//////////////////////////////////////////////////////////////

Project core_service {
  database_type: "PostgreSQL"
  Note: '''
  Основная бизнес-БД.
  Здесь живут пользователи, сотрудники, навыки, графики, отпуска,
  задачи и финальные назначения.
  '''
}

Enum user_role {
  admin
  manager
  employee
}

Enum employment_type {
  full_time
  part_time
  contract
}

Enum leave_type {
  vacation
  sick_leave
  day_off
  business_trip
}

Enum leave_status {
  requested
  approved
  rejected
  cancelled
}

Enum task_status {
  draft
  planned
  assigned
  in_progress
  done
  cancelled
}

Enum priority_level {
  low
  medium
  high
  critical
}

Enum assignment_status {
  proposed
  approved
  active
  completed
  cancelled
  rejected
}

Enum assignment_source_type {
  system
  manager
  admin
}

Table users {
  id bigserial [pk]
  email varchar(255) [not null, unique]
  password_hash varchar(255) [not null]
  role user_role [not null, default: 'employee']
  is_active boolean [not null, default: true]
  last_login_at timestamptz
  created_at timestamptz [not null]
  updated_at timestamptz [not null]

  Note: '''
  Учетная запись для входа в систему.
  Для диплома одной роли на пользователя достаточно.
  '''
}

Table departments {
  id bigserial [pk]
  name varchar(255) [not null, unique]
  description text
  created_at timestamptz [not null]
  updated_at timestamptz [not null]

  Note: '''
  Подразделения/отделы.
  Нужны для группировки сотрудников и задач.
  '''
}

Table employees {
  id bigserial [pk]
  user_id bigint [not null, unique, ref: > users.id]
  department_id bigint [ref: > departments.id]
  full_name varchar(255) [not null]
  position_name varchar(255) [not null]
  employment_type employment_type [not null, default: 'full_time']
  weekly_capacity_hours int [not null, default: 40]
  timezone varchar(64) [not null, default: 'UTC']
  hire_date date
  is_active boolean [not null, default: true]
  created_at timestamptz [not null]
  updated_at timestamptz [not null]

  Note: '''
  Профиль сотрудника.
  position_name оставлен простым полем, без отдельной таблицы positions.
  '''
}

Table skills {
  id bigserial [pk]
  name varchar(255) [not null, unique]
  description text
  created_at timestamptz [not null]
  updated_at timestamptz [not null]

  Note: '''
  Справочник компетенций/навыков.
  '''
}

Table employee_skills {
  id bigserial [pk]
  employee_id bigint [not null, ref: > employees.id]
  skill_id bigint [not null, ref: > skills.id]
  level int [not null, note: 'Например, шкала 1..5']
  created_at timestamptz [not null]
  updated_at timestamptz [not null]

  Note: '''
  Связь many-to-many между сотрудником и навыком.
  Здесь хранится уровень владения навыком.
  '''
  
  Indexes {
    (employee_id, skill_id) [unique]
    employee_id
    skill_id
  }
}

Table work_schedules {
  id bigserial [pk]
  employee_id bigint [not null, ref: > employees.id]
  name varchar(255) [not null]
  is_default boolean [not null, default: true]
  created_at timestamptz [not null]
  updated_at timestamptz [not null]

  Note: '''
  Шаблон графика сотрудника.
  Нужен, чтобы не хранить доступность по каждой дате отдельно.
  '''
  
  Indexes {
    employee_id
  }
}

Table work_schedule_days {
  id bigserial [pk]
  schedule_id bigint [not null, ref: > work_schedules.id]
  weekday int [not null, note: '0=Monday ... 6=Sunday']
  is_working_day boolean [not null, default: true]
  capacity_hours int [not null, default: 8]
  start_time time
  end_time time

  Note: '''
  Детализация шаблона графика по дням недели.
  '''
  
  Indexes {
    (schedule_id, weekday) [unique]
    schedule_id
  }
}

Table employee_leaves {
  id bigserial [pk]
  employee_id bigint [not null, ref: > employees.id]
  leave_type leave_type [not null]
  status leave_status [not null, default: 'approved']
  start_date date [not null]
  end_date date [not null]
  comment text
  created_at timestamptz [not null]
  updated_at timestamptz [not null]

  Note: '''
  Отпуска, больничные, отгулы и другие периоды отсутствия.
  Это жесткое ограничение для планировщика.
  '''
  
  Indexes {
    employee_id
    (employee_id, start_date, end_date)
  }
}

Table employee_availability_overrides {
  id bigserial [pk]
  employee_id bigint [not null, ref: > employees.id]
  date date [not null]
  available_hours int [not null, note: 'Сколько часов реально доступно в эту дату']
  reason text
  created_by_user_id bigint [ref: > users.id]
  created_at timestamptz [not null]

  Note: '''
  Разовые исключения из стандартного графика.
  Пример: сотрудник обычно доступен 8 часов,
  но в конкретную среду доступен только 3 часа.
  '''
  
  Indexes {
    (employee_id, date) [unique]
    employee_id
  }
}

Table tasks {
  id bigserial [pk]
  department_id bigint [ref: > departments.id]
  title varchar(255) [not null]
  description text
  status task_status [not null, default: 'draft']
  priority priority_level [not null, default: 'medium']
  estimated_hours int [note: 'Опциональная ручная оценка; если null, planner рассчитывает estimate сам']
  actual_hours int [note: 'Заполняется после завершения задачи']
  start_date date
  due_date date [not null]
  created_by_user_id bigint [not null, ref: > users.id]
  created_at timestamptz [not null]
  updated_at timestamptz [not null]

  Note: '''
  Основная сущность задачи.
  estimated_hours — ручная плановая оценка (nullable в MVP v1),
  actual_hours — фактическое время после выполнения (business truth для done).
  Инварианты lifecycle:
  - status=done => actual_hours > 0
  - status!=done => actual_hours is null
  - done считается terminal в v1
  '''
  
  Indexes {
    status
    priority
    due_date
    department_id
  }
}

Table task_requirements {
  id bigserial [pk]
  task_id bigint [not null, ref: > tasks.id]
  skill_id bigint [not null, ref: > skills.id]
  min_level int [not null, default: 1]
  weight decimal(5,2) [not null, default: 1.00]

  Note: '''
  Требуемые навыки для задачи.
  weight нужен, если захочешь учитывать важность навыка при скоринге.
  '''
  
  Indexes {
    (task_id, skill_id) [unique]
    task_id
    skill_id
  }
}

Table assignments {
  id bigserial [pk]
  task_id bigint [not null, ref: > tasks.id]
  employee_id bigint [not null, ref: > employees.id]
  source_plan_run_id uuid [note: 'Логическая ссылка на planner.plan_runs.external_uuid']
  planned_hours int [not null]
  start_date date [not null]
  end_date date [not null]
  status assignment_status [not null, default: 'proposed']
  assigned_by_type assignment_source_type [not null, default: 'system']
  assigned_by_user_id bigint [ref: > users.id]
  approved_by_user_id bigint [ref: > users.id]
  assigned_at timestamptz [not null]
  approved_at timestamptz
  notes text

  Note: '''
  Финальное назначение задачи сотруднику.
  planned_hours, start_date, end_date относятся к КОНКРЕТНОМУ назначению,
  а не ко всей задаче в целом.
  '''
  
  Indexes {
    task_id
    employee_id
    status
    source_plan_run_id
  }
}

Table assignment_change_log {
  id bigserial [pk]
  assignment_id bigint [not null, ref: > assignments.id]
  old_employee_id bigint [ref: > employees.id]
  new_employee_id bigint [ref: > employees.id]
  change_reason text [not null]
  changed_by_user_id bigint [not null, ref: > users.id]
  created_at timestamptz [not null]

  Note: '''
  История переназначений и ручных правок.
  '''
  
  Indexes {
    assignment_id
    created_at
  }
}

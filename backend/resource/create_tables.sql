-- sqlite schema
-- department definition

CREATE TABLE "department" (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `name` TEXT NOT NULL, -- Department name
  `parent_id` INTEGER, -- Parent department ID
  `manager_id` INTEGER, -- Department manager ID
  `create_time` TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Creation time
  `edit_time` TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP -- Update time
);

CREATE UNIQUE INDEX uniq_department_name ON department (name);

-- employee definition

CREATE TABLE `employee` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `employee_no` TEXT NOT NULL, -- Employee number
  `name` TEXT NOT NULL, -- Employee name
  `gender` INTEGER NOT NULL DEFAULT 0, -- 0-unknown 1-male 2-female
  `birth_date` TEXT, -- Birth date
  `phone` TEXT NOT NULL, -- Phone number
  `email` TEXT NOT NULL, -- Email address
  `department_id` INTEGER NOT NULL, -- Department ID
  `position` TEXT NOT NULL, -- Current position
  `entry_date` TEXT NOT NULL, -- Entry date
  `status` INTEGER NOT NULL DEFAULT 2, -- 1-probation 2-active 3-left
  `create_time` TEXT DEFAULT CURRENT_TIMESTAMP, -- Creation time
  `edit_time` TEXT DEFAULT CURRENT_TIMESTAMP -- Update time
);

CREATE UNIQUE INDEX `uniq_employee_no` ON `employee` (`employee_no`);
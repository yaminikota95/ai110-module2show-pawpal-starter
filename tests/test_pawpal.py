from datetime import date, timedelta

import pytest

from pawpal_system import (
    DailyPlan,
    Frequency,
    Owner,
    Pet,
    Priority,
    Scheduler,
    ScheduledTask,
    Task,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_pet(name="Mochi", species="dog", age=3):
    return Pet(name=name, species=species, age=age)


def make_task(title="Task", duration=10, priority=Priority.MEDIUM,
              fixed_time=None, frequency=Frequency.DAILY):
    return Task(title=title, duration_minutes=duration, priority=priority,
                fixed_time=fixed_time, frequency=frequency)


# ---------------------------------------------------------------------------
# Existing tests (kept)
# ---------------------------------------------------------------------------

def test_mark_complete_changes_status():
    task = Task(title="Morning walk", duration_minutes=30, priority=Priority.HIGH)
    assert task.is_completed is False
    task.mark_complete()
    assert task.is_completed is True


def test_add_task_increases_pet_task_count():
    pet = Pet(name="Mochi", species="dog", age=3)
    assert len(pet.get_tasks()) == 0
    pet.add_task(Task(title="Feeding", duration_minutes=5, priority=Priority.HIGH))
    assert len(pet.get_tasks()) == 1


# ---------------------------------------------------------------------------
# Sorting correctness
# ---------------------------------------------------------------------------

def test_scheduled_tasks_are_in_chronological_order():
    """generate_plan must return scheduled tasks sorted by start time."""
    owner = Owner(name="Alex", available_minutes=120)
    pet = make_pet()

    # Add fixed tasks out of chronological order
    pet.add_task(make_task("Late task",  duration=10, fixed_time="09:00"))
    pet.add_task(make_task("Early task", duration=10, fixed_time="07:30"))
    owner.add_pet(pet)

    plan = Scheduler().generate_plan(owner)
    start_times = [s.start_time for s in plan.scheduled]
    assert start_times == sorted(start_times), (
        f"Schedule is not chronological: {start_times}"
    )


def test_sort_tasks_high_priority_before_low():
    """_sort_tasks must place HIGH-priority tasks ahead of LOW-priority ones."""
    scheduler = Scheduler()
    pet = make_pet()
    low  = make_task("Low",  priority=Priority.LOW,  duration=10)
    high = make_task("High", priority=Priority.HIGH, duration=10)

    result = scheduler._sort_tasks([(pet, low), (pet, high)])
    assert result[0][1].priority == Priority.HIGH
    assert result[1][1].priority == Priority.LOW


def test_sort_tasks_same_priority_shorter_first():
    """Among equal-priority tasks, shorter duration comes first."""
    scheduler = Scheduler()
    pet = make_pet()
    long_task  = make_task("Long",  priority=Priority.MEDIUM, duration=30)
    short_task = make_task("Short", priority=Priority.MEDIUM, duration=5)

    result = scheduler._sort_tasks([(pet, long_task), (pet, short_task)])
    assert result[0][1].title == "Short"
    assert result[1][1].title == "Long"


def test_flexible_tasks_scheduled_by_priority():
    """HIGH-priority flexible task must appear before LOW in the final plan."""
    owner = Owner(name="Jordan", available_minutes=120)
    pet = make_pet()
    pet.add_task(make_task("Low task",  priority=Priority.LOW,  duration=15))
    pet.add_task(make_task("High task", priority=Priority.HIGH, duration=15))
    owner.add_pet(pet)

    plan = Scheduler().generate_plan(owner)
    titles = [s.task.title for s in plan.scheduled]
    assert titles.index("High task") < titles.index("Low task")


# ---------------------------------------------------------------------------
# Recurrence logic
# ---------------------------------------------------------------------------

def test_complete_daily_task_creates_successor():
    """Completing a DAILY task must append a new task due tomorrow."""
    pet = make_pet()
    task = make_task("Daily walk", frequency=Frequency.DAILY)
    pet.add_task(task)

    successor = pet.complete_task(task.id)

    assert successor is not None, "Expected a successor task for a DAILY task"
    assert successor.is_completed is False
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    assert successor.due_date == tomorrow


def test_complete_once_task_creates_no_successor():
    """Completing a ONCE task must not create a follow-up task."""
    pet = make_pet()
    task = make_task("One-time vet visit", frequency=Frequency.ONCE)
    pet.add_task(task)

    successor = pet.complete_task(task.id)

    assert successor is None


def test_complete_weekly_task_creates_successor_in_seven_days():
    """Completing a WEEKLY task must schedule the next occurrence 7 days out."""
    pet = make_pet()
    task = make_task("Weekly bath", frequency=Frequency.WEEKLY)
    pet.add_task(task)

    successor = pet.complete_task(task.id)

    expected = (date.today() + timedelta(days=7)).isoformat()
    assert successor is not None
    assert successor.due_date == expected


def test_completed_once_task_excluded_from_schedule():
    """A completed ONCE task must not appear in generate_plan."""
    owner = Owner(name="Sam", available_minutes=60)
    pet = make_pet()
    task = make_task("One-off groom", frequency=Frequency.ONCE)
    pet.add_task(task)
    pet.complete_task(task.id)
    owner.add_pet(pet)

    plan = Scheduler().generate_plan(owner)
    scheduled_ids = {s.task.id for s in plan.scheduled}
    assert task.id not in scheduled_ids


def test_future_due_date_excluded_from_todays_plan():
    """A task with a due_date in the future must not appear in today's schedule."""
    owner = Owner(name="Riley", available_minutes=120)
    pet = make_pet()
    future = (date.today() + timedelta(days=3)).isoformat()
    task = Task(title="Future task", duration_minutes=10,
                priority=Priority.HIGH, due_date=future, frequency=Frequency.DAILY)
    pet.add_task(task)
    owner.add_pet(pet)

    plan = Scheduler().generate_plan(owner)
    scheduled_ids = {s.task.id for s in plan.scheduled}
    assert task.id not in scheduled_ids


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------

def test_overlapping_fixed_tasks_generates_warning():
    """Two fixed tasks at the same time must produce a conflict warning."""
    owner = Owner(name="Casey", available_minutes=120)
    pet = make_pet()
    pet.add_task(make_task("Task A", duration=30, fixed_time="08:00"))
    pet.add_task(make_task("Task B", duration=30, fixed_time="08:15"))  # overlaps A
    owner.add_pet(pet)

    plan = Scheduler().generate_plan(owner)

    assert len(plan.warnings) > 0, "Expected a conflict warning for overlapping tasks"


def test_overlapping_fixed_tasks_second_is_skipped():
    """The conflicting task must appear in skipped, not scheduled."""
    owner = Owner(name="Casey", available_minutes=120)
    pet = make_pet()
    task_a = make_task("Task A", duration=30, fixed_time="08:00")
    task_b = make_task("Task B", duration=30, fixed_time="08:15")
    pet.add_task(task_a)
    pet.add_task(task_b)
    owner.add_pet(pet)

    plan = Scheduler().generate_plan(owner)

    scheduled_titles = {s.task.title for s in plan.scheduled}
    skipped_titles   = {s.task.title for s in plan.skipped}
    assert "Task A" in scheduled_titles
    assert "Task B" in skipped_titles


def test_non_overlapping_fixed_tasks_no_warning():
    """Fixed tasks that do not overlap must produce zero warnings."""
    owner = Owner(name="Morgan", available_minutes=120)
    pet = make_pet()
    pet.add_task(make_task("Morning", duration=30, fixed_time="07:00"))
    pet.add_task(make_task("Evening", duration=30, fixed_time="09:00"))  # gap exists
    owner.add_pet(pet)

    plan = Scheduler().generate_plan(owner)

    assert plan.warnings == []


def test_back_to_back_fixed_tasks_no_conflict():
    """Tasks where one ends exactly when the next begins must not conflict."""
    owner = Owner(name="Drew", available_minutes=120)
    pet = make_pet()
    pet.add_task(make_task("First",  duration=30, fixed_time="08:00"))  # ends 08:30
    pet.add_task(make_task("Second", duration=30, fixed_time="08:30"))  # starts 08:30
    owner.add_pet(pet)

    plan = Scheduler().generate_plan(owner)

    assert plan.warnings == [], f"Unexpected conflict warnings: {plan.warnings}"
    assert len(plan.scheduled) == 2


def test_detect_conflicts_helper_returns_message():
    """_detect_conflicts must return a non-empty list for two overlapping slots."""
    scheduler = Scheduler()
    pet = make_pet()
    task_a = make_task("A", duration=30, fixed_time="08:00")
    task_b = make_task("B", duration=30, fixed_time="08:15")

    slot_a = ScheduledTask(task=task_a, pet=pet, start_time="08:00", end_time="08:30")
    slot_b = ScheduledTask(task=task_b, pet=pet, start_time="08:15", end_time="08:45")

    conflicts = scheduler._detect_conflicts([slot_a, slot_b])
    assert len(conflicts) > 0


def test_detect_conflicts_helper_empty_for_no_overlap():
    """_detect_conflicts must return an empty list when no tasks overlap."""
    scheduler = Scheduler()
    pet = make_pet()
    task_a = make_task("A", duration=30, fixed_time="08:00")
    task_b = make_task("B", duration=30, fixed_time="09:00")

    slot_a = ScheduledTask(task=task_a, pet=pet, start_time="08:00", end_time="08:30")
    slot_b = ScheduledTask(task=task_b, pet=pet, start_time="09:00", end_time="09:30")

    conflicts = scheduler._detect_conflicts([slot_a, slot_b])
    assert conflicts == []


# ---------------------------------------------------------------------------
# Urgency-weighted prioritization
# ---------------------------------------------------------------------------

def test_urgency_score_fresh_task_equals_priority_value():
    """A task with no due_date should score exactly its priority value."""
    task = make_task(priority=Priority.HIGH)  # no due_date
    today = date.today().isoformat()
    assert task.urgency_score(today) == Priority.HIGH.value  # 1.0


def test_urgency_score_decreases_as_overdue_days_increase():
    """urgency_score must fall as days_overdue grows (task becomes more urgent)."""
    task = Task(
        title="Overdue bath",
        duration_minutes=20,
        priority=Priority.LOW,
        due_date=(date.today() - timedelta(days=1)).isoformat(),
        frequency=Frequency.WEEKLY,
    )
    today = date.today().isoformat()
    score_1_day = task.urgency_score(today)

    task2 = Task(
        title="Overdue bath",
        duration_minutes=20,
        priority=Priority.LOW,
        due_date=(date.today() - timedelta(days=5)).isoformat(),
        frequency=Frequency.WEEKLY,
    )
    score_5_days = task2.urgency_score(today)

    assert score_5_days < score_1_day


def test_overdue_medium_task_outranks_fresh_high_task():
    """A MEDIUM task overdue by 3+ days must sort before a fresh HIGH task."""
    scheduler = Scheduler()
    pet = make_pet()
    today = date.today().isoformat()
    overdue_date = (date.today() - timedelta(days=4)).isoformat()

    fresh_high = Task(
        title="Fresh HIGH",
        duration_minutes=10,
        priority=Priority.HIGH,
        frequency=Frequency.DAILY,
    )
    stale_medium = Task(
        title="Stale MEDIUM",
        duration_minutes=10,
        priority=Priority.MEDIUM,
        due_date=overdue_date,
        frequency=Frequency.DAILY,
    )

    result = scheduler._sort_tasks(
        [(pet, fresh_high), (pet, stale_medium)],
        today=today,
    )
    assert result[0][1].title == "Stale MEDIUM", (
        f"Expected overdue MEDIUM first, got {result[0][1].title} "
        f"(scores: HIGH={fresh_high.urgency_score(today):.2f}, "
        f"MEDIUM={stale_medium.urgency_score(today):.2f})"
    )


def test_urgency_score_floor_never_goes_negative():
    """urgency_score must never return a value below 0.1, even for very old tasks."""
    task = Task(
        title="Ancient task",
        duration_minutes=5,
        priority=Priority.HIGH,
        due_date=(date.today() - timedelta(days=100)).isoformat(),
        frequency=Frequency.DAILY,
    )
    score = task.urgency_score(date.today().isoformat())
    assert score >= 0.1


def test_fresh_tasks_urgency_order_matches_priority_order():
    """With no overdue days, urgency score must preserve HIGH > MEDIUM > LOW order."""
    scheduler = Scheduler()
    pet = make_pet()
    today = date.today().isoformat()

    high   = make_task("H", priority=Priority.HIGH,   duration=10)
    medium = make_task("M", priority=Priority.MEDIUM, duration=10)
    low    = make_task("L", priority=Priority.LOW,    duration=10)

    result = scheduler._sort_tasks([(pet, low), (pet, high), (pet, medium)], today=today)
    titles = [t.title for _, t in result]
    assert titles == ["H", "M", "L"]

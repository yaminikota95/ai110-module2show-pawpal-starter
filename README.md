# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Smarter Scheduling

The scheduler goes beyond a simple checklist. Here is a summary of the logic improvements built into `pawpal_system.py`:

**Sorting tasks by time**
Fixed-time tasks are placed first in chronological order. Flexible tasks are then sorted by priority (HIGH → MEDIUM → LOW) and, within the same priority level, shortest-first so smaller tasks don't crowd out longer ones. The final schedule is always returned in wall-clock order regardless of the order tasks were added.

**Filtering by pet and status**
`Owner.filter_tasks(pet_name, completed)` lets you slice the full task list by pet name, completion status, or both at once. Omitting a parameter means "don't filter on that axis", so one method covers all four combinations cleanly.

**Recurring task support**
Every `Task` carries a `frequency` (ONCE, DAILY, or WEEKLY) and a `due_date`. When `Pet.complete_task()` is called, it marks the original done and automatically appends a fresh successor with the next `due_date` calculated using Python's `timedelta` — today + 1 day for DAILY tasks, today + 7 days for WEEKLY ones. ONCE tasks produce no successor. This means the schedule stays accurate across multiple days without any manual reset.

**Conflict detection**
After all tasks are placed, `Scheduler._detect_conflicts()` scans every unique pair of scheduled tasks for overlapping time intervals. It uses `itertools.combinations` for readable pair iteration and exits early once it reaches a task that starts after the current task ends (possible because the list is already sorted). Conflicts are surfaced as plain-language warning strings in `DailyPlan.warnings` — the program never crashes, it just tells you what it found.

---

## Testing PawPal+

### Run the test suite

```bash
python -m pytest tests/test_pawpal.py -v
```

### What the tests cover

The suite contains **17 tests** across three areas:

**Sorting correctness**
Verifies that the final schedule is always in chronological (wall-clock) order, that `_sort_tasks` places HIGH-priority tasks before LOW-priority ones, and that tasks of equal priority are ordered shortest-first so small tasks don't block larger ones.

**Recurrence logic**
Confirms that completing a DAILY task appends a successor due tomorrow, a WEEKLY task appends one due in 7 days, and a ONCE task produces no successor at all. Also checks that a completed ONCE task disappears from the next generated plan, and that a task with a future `due_date` is correctly excluded from today's schedule.

**Conflict detection**
Ensures that two fixed tasks with overlapping time windows produce a warning and that the conflicting task lands in `skipped` rather than `scheduled`. Also verifies the inverse: non-overlapping tasks and back-to-back tasks (end time == start time) generate zero warnings.

### Confidence level

**4 / 5 stars**

The core scheduling behaviors — priority sorting, recurring task lifecycle, and fixed-time conflict detection — are well covered and all 17 tests pass. One star is held back because the test suite does not yet exercise the Streamlit UI layer, multi-pet interactions across owners, or edge cases around the owner's time budget running out mid-schedule. Those paths exist in the code but are untested.

---

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

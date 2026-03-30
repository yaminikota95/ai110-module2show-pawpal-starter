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

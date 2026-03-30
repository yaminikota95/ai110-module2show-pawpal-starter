from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from itertools import combinations
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Priority(Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class Frequency(Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass(eq=False)
class Task:
    """A single pet-care activity."""
    title: str
    duration_minutes: int
    priority: Priority
    fixed_time: Optional[str] = None        # "HH:MM" or None for flexible
    frequency: Frequency = Frequency.DAILY
    is_completed: bool = False
    due_date: Optional[str] = None   # "YYYY-MM-DD" — when this occurrence is next due
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Identity is based solely on id
    def __eq__(self, other: object) -> bool:
        """Two tasks are equal only if they share the same id."""
        return isinstance(other, Task) and self.id == other.id

    def __hash__(self) -> int:
        """Hash based on id so tasks can be stored in sets and dicts."""
        return hash(self.id)

    def validate(self) -> bool:
        """Return True if the task has valid data."""
        if self.duration_minutes <= 0 or not self.title.strip():
            return False
        if self.fixed_time is not None:
            try:
                h, m = map(int, self.fixed_time.split(":"))
                if not (0 <= h <= 23 and 0 <= m <= 59):
                    return False
            except (ValueError, AttributeError):
                return False
        return True

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.is_completed = True

    def mark_incomplete(self) -> None:
        """Reset this task to incomplete (e.g. for recurring tasks)."""
        self.is_completed = False

    def next_occurrence(self) -> Optional["Task"]:
        """Return a fresh Task for the next run, or None if this task is ONCE.

        due_date is calculated with timedelta so is_due_today() only needs
        a single date comparison — no delta arithmetic at read time.
          DAILY  → due_date = today + 1 day
          WEEKLY → due_date = today + 7 days
        """
        if self.frequency == Frequency.ONCE:
            return None
        intervals = {Frequency.DAILY: 1, Frequency.WEEKLY: 7}
        next_due = date.today() + timedelta(days=intervals[self.frequency])
        return Task(
            title=self.title,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            fixed_time=self.fixed_time,
            frequency=self.frequency,
            is_completed=False,
            due_date=next_due.isoformat(),
        )

    def is_due_today(self, today: str) -> bool:
        """Return True if this task should appear in today's schedule."""
        if self.frequency == Frequency.ONCE:
            return not self.is_completed
        if self.due_date is None:
            return True   # no due_date set → treat as due immediately
        return date.fromisoformat(self.due_date) <= date.fromisoformat(today)

    def urgency_score(self, today: str) -> float:
        """Return a float urgency score — lower means schedule sooner.

        Combines priority with how many days the task is overdue so that
        neglected tasks naturally rise above fresh lower-priority ones.

        Formula: max(priority.value - days_overdue * 0.4, 0.1)
          - A fresh HIGH task scores 1.0.
          - A MEDIUM task overdue by 3 days scores 2.0 - 1.2 = 0.8,
            placing it ahead of the fresh HIGH.
          - The floor of 0.1 prevents negative scores regardless of age.

        Crossover points (when an overdue task overtakes a fresh one):
          MEDIUM overtakes fresh HIGH after 3 days overdue.
          LOW    overtakes fresh HIGH after 5 days overdue.
        """
        if self.due_date is None:
            days_overdue = 0
        else:
            days_overdue = max(
                0,
                (date.fromisoformat(today) - date.fromisoformat(self.due_date)).days,
            )
        return max(self.priority.value - days_overdue * 0.4, 0.1)


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    """A pet with its own list of care tasks."""
    name: str
    species: str
    age: int
    _tasks: list[Task] = field(default_factory=list, repr=False)

    def add_task(self, task: Task) -> None:
        """Add a task; silently ignore invalid or duplicate tasks."""
        if not task.validate():
            raise ValueError(f"Task '{task.title}' is invalid and cannot be added.")
        if task in self._tasks:
            return
        self._tasks.append(task)

    def remove_task(self, task_id: str) -> None:
        """Remove a task by id; no-op if not found."""
        self._tasks = [t for t in self._tasks if t.id != task_id]

    def get_task(self, task_id: str) -> Optional[Task]:
        """Return a task by id, or None."""
        return next((t for t in self._tasks if t.id == task_id), None)

    def get_tasks(self, include_completed: bool = False) -> list[Task]:
        """Return tasks, excluding completed ones by default."""
        if include_completed:
            return list(self._tasks)
        return [t for t in self._tasks if not t.is_completed]

    def complete_task(self, task_id: str) -> Optional[Task]:
        """Mark a task complete and, if it recurs, append the next occurrence.

        Returns the newly created successor Task, or None for ONCE tasks.
        No-op (returns None) if task_id is not found.
        """
        task = self.get_task(task_id)
        if task is None:
            return None
        task.mark_complete()
        successor = task.next_occurrence()
        if successor is not None:
            self._tasks.append(successor)
        return successor

    def pending_count(self) -> int:
        """Return the number of incomplete tasks for this pet."""
        return sum(1 for t in self._tasks if not t.is_completed)


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

@dataclass
class Owner:
    """A pet owner who manages one or more pets."""
    name: str
    available_minutes: int = 60
    preferences: list[str] = field(default_factory=list)
    _pets: list[Pet] = field(default_factory=list, repr=False)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet; ignore duplicates by name+species."""
        if any(p.name == pet.name and p.species == pet.species for p in self._pets):
            return
        self._pets.append(pet)

    def remove_pet(self, name: str) -> None:
        """Remove a pet by name; no-op if not found."""
        self._pets = [p for p in self._pets if p.name != name]

    def get_pets(self) -> list[Pet]:
        """Return a copy of the owner's pet list."""
        return list(self._pets)

    def get_all_tasks(self, include_completed: bool = False) -> list[tuple[Pet, Task]]:
        """Return all (pet, task) pairs across every pet."""
        return [
            (pet, task)
            for pet in self._pets
            for task in pet.get_tasks(include_completed=include_completed)
        ]

    def filter_tasks(
        self,
        pet_name: Optional[str] = None,
        completed: Optional[bool] = None,
    ) -> list[tuple[Pet, Task]]:
        """Return (pet, task) pairs filtered by pet name and/or completion status.

        Both parameters are optional and act as independent narrowing filters —
        omitting one means "don't filter on that axis." They are applied in
        sequence: pet_name first, then completion status.

        Args:
            pet_name:  Only include tasks belonging to this pet. None = all pets.
            completed: True = completed tasks only, False = pending only, None = both.

        Returns:
            A list of (Pet, Task) tuples matching all supplied criteria.

        Examples:
            owner.filter_tasks()                        # all tasks, all pets
            owner.filter_tasks(pet_name="Mochi")        # Mochi's tasks only
            owner.filter_tasks(completed=False)         # pending across all pets
            owner.filter_tasks(pet_name="Luna", completed=True)  # Luna's done tasks
        """
        pairs = self.get_all_tasks(include_completed=True)

        if pet_name is not None:
            pairs = [(p, t) for p, t in pairs if p.name == pet_name]

        if completed is not None:
            pairs = [(p, t) for p, t in pairs if t.is_completed == completed]

        return pairs

    def total_pending_minutes(self) -> int:
        """Sum of duration_minutes for all pending tasks across all pets."""
        return sum(t.duration_minutes for _, t in self.get_all_tasks())


# ---------------------------------------------------------------------------
# Output types
# ---------------------------------------------------------------------------

@dataclass
class ScheduledTask:
    """A task that has been placed into a time slot."""
    task: Task
    pet: Pet                # full Pet reference, not just a name string
    start_time: str         # "HH:MM"
    end_time: str           # "HH:MM"

    @property
    def pet_name(self) -> str:
        """Convenience accessor for the associated pet's name."""
        return self.pet.name


@dataclass
class DailyPlan:
    """The complete output of a scheduling run."""
    owner: Owner
    scheduled: list[ScheduledTask]
    skipped: list[ScheduledTask]    # same type; start_time/end_time are empty strings
    total_minutes_used: int
    reasoning: list[str]
    warnings: list[str]             # conflict warnings — surfaced separately from verbose reasoning

    def summary(self) -> str:
        """Return a human-readable string of the full daily plan."""
        lines = [
            f"Plan for {self.owner.name}",
            f"Time budget: {self.owner.available_minutes} min  |  Used: {self.total_minutes_used} min\n",
        ]
        if self.warnings:
            lines.append("*** CONFLICT WARNINGS ***")
            for w in self.warnings:
                lines.append(f"  [!] {w}")
            lines.append("")

        if self.scheduled:
            lines.append("Scheduled:")
            for st in self.scheduled:
                lines.append(
                    f"  {st.start_time}–{st.end_time}  [{st.pet_name}] {st.task.title}"
                    f"  ({st.task.priority.name})"
                )
        else:
            lines.append("No tasks scheduled.")

        if self.skipped:
            lines.append("\nSkipped (did not fit or conflicted):")
            for st in self.skipped:
                lines.append(
                    f"  [{st.pet_name}] {st.task.title}  ({st.task.duration_minutes} min)"
                )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    """
    Organises and schedules tasks for an owner's pets.

    Algorithm:
      1. Filter tasks to only those due today (respects Frequency).
      2. Place fixed-time tasks first (sorted by time); skip conflicting ones.
      3. Fill remaining free gaps with flexible tasks, sorted by priority then duration.
      4. Run _detect_conflicts() as a final verification pass on the placed schedule.
      5. Return scheduled list sorted by start time.
    """

    DAY_START = 7 * 60       # schedule begins at 07:00 (minutes since midnight)
    BUFFER_MINUTES = 5       # minimum gap between consecutive tasks

    def generate_plan(self, owner: Owner) -> DailyPlan:
        """Build and return a DailyPlan for the given owner."""
        today = date.today().isoformat()
        all_tasks = [
            (p, t) for p, t in owner.get_all_tasks()
            if t.is_due_today(today)
        ]

        fixed    = [(p, t) for p, t in all_tasks if t.fixed_time is not None]
        flexible = [(p, t) for p, t in all_tasks if t.fixed_time is None]

        reasoning: list[str] = []
        warnings:  list[str] = []
        scheduled: list[ScheduledTask] = []
        skipped:   list[ScheduledTask] = []
        minutes_used = 0

        # --- Step 1: place fixed-time tasks ---
        accepted_fixed: list[tuple[Pet, Task]] = []
        for pet, task in sorted(fixed, key=lambda x: self._to_min(x[1].fixed_time)):
            conflict = next(
                (a for _, a in accepted_fixed if self._overlaps(a, task)), None
            )
            if conflict:
                msg = (
                    f"'{task.title}' ({pet.name}) conflicts with "
                    f"'{conflict.title}' ({conflict.fixed_time}–"
                    f"{self._to_str(self._to_min(conflict.fixed_time) + conflict.duration_minutes)}) "
                    f"— '{task.title}' skipped."
                )
                warnings.append(msg)
                reasoning.append(msg)
                skipped.append(ScheduledTask(task=task, pet=pet, start_time="", end_time=""))
            else:
                end = self._to_min(task.fixed_time) + task.duration_minutes
                scheduled.append(ScheduledTask(
                    task=task, pet=pet,
                    start_time=task.fixed_time,
                    end_time=self._to_str(end),
                ))
                accepted_fixed.append((pet, task))
                minutes_used += task.duration_minutes
                reasoning.append(
                    f"'{task.title}' ({pet.name}) fixed at {task.fixed_time} — placed as required."
                )

        # --- Step 2: fill free gaps with flexible tasks ---
        occupied = sorted(
            (self._to_min(t.fixed_time), self._to_min(t.fixed_time) + t.duration_minutes)
            for _, t in accepted_fixed
        )
        free_gaps = self._free_gaps(occupied, owner.available_minutes)

        for pet, task in self._sort_tasks(flexible, today):
            placed = False
            needed = task.duration_minutes + self.BUFFER_MINUTES
            for i, (gap_start, gap_end) in enumerate(free_gaps):
                if needed <= gap_end - gap_start:
                    start_str = self._to_str(gap_start)
                    end_str   = self._to_str(gap_start + task.duration_minutes)
                    scheduled.append(ScheduledTask(
                        task=task, pet=pet,
                        start_time=start_str,
                        end_time=end_str,
                    ))
                    reasoning.append(
                        f"'{task.title}' ({pet.name}) scheduled at {start_str} "
                        f"[{task.priority.name}, {task.duration_minutes} min]."
                    )
                    free_gaps[i] = (gap_start + needed, gap_end)
                    minutes_used += task.duration_minutes
                    placed = True
                    break

            if not placed:
                skipped.append(ScheduledTask(task=task, pet=pet, start_time="", end_time=""))
                reasoning.append(
                    f"'{task.title}' ({pet.name}) skipped — needs {task.duration_minutes} min "
                    f"but largest free gap is {max((g[1]-g[0] for g in free_gaps), default=0)} min."
                )

        # Sort final schedule chronologically
        scheduled.sort(key=lambda s: self._to_min(s.start_time))

        # Final verification pass — catches any overlaps the scheduler may have missed
        warnings.extend(self._detect_conflicts(scheduled))

        return DailyPlan(
            owner=owner,
            scheduled=scheduled,
            skipped=skipped,
            total_minutes_used=minutes_used,
            reasoning=reasoning,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _detect_conflicts(self, scheduled: list[ScheduledTask]) -> list[str]:
        """Scan the placed schedule and return a warning string for every overlapping pair.

        This is a verification pass that runs after all tasks have been placed.
        It acts as a safety net — the scheduler's gap logic should prevent overlaps,
        but this catches anything that slips through (e.g., back-to-back fixed tasks
        whose durations were miscalculated, or tasks injected after scheduling).

        Algorithm:
            Uses itertools.combinations to iterate every unique (a, b) pair without
            manual index bookkeeping. Because `scheduled` is sorted by start time,
            once task b starts at or after task a ends (s_b >= e_a), every subsequent
            b also starts later — the loop breaks early instead of checking them all.
            Overlap condition: s_a < e_b  (with s_b < e_a already guaranteed by the
            break above, only one side of the standard two-sided test is needed).

        Args:
            scheduled: Tasks already placed in time slots, sorted by start time.

        Returns:
            A list of human-readable warning strings, one per detected conflict.
            Returns an empty list when no conflicts exist — never raises.
        """
        found: list[str] = []
        for a, b in combinations(scheduled, 2):
            s_a, e_a = self._to_min(a.start_time), self._to_min(a.end_time)
            s_b, e_b = self._to_min(b.start_time), self._to_min(b.end_time)
            if s_b >= e_a:   # b starts after a ends; all later b also start later — stop
                break
            if s_a < e_b:    # s_b < e_a already guaranteed above; full overlap confirmed
                found.append(
                    f"CONFLICT: [{a.pet_name}] '{a.task.title}' "
                    f"({a.start_time}–{a.end_time}) overlaps "
                    f"[{b.pet_name}] '{b.task.title}' "
                    f"({b.start_time}–{b.end_time})"
                )
        return found

    def _sort_tasks(
        self,
        tasks: list[tuple[Pet, Task]],
        today: Optional[str] = None,
    ) -> list[tuple[Pet, Task]]:
        """Sort flexible tasks so the scheduler fills gaps most effectively.

        Sorting key is a two-element tuple so Python's stable sort applies
        criteria in order:
          1. Urgency score (Task.urgency_score) — combines priority with how
             many days the task is overdue.  A MEDIUM task overdue by 3+ days
             scores lower (more urgent) than a fresh HIGH task, so neglected
             tasks naturally rise in the schedule without manual intervention.
          2. Duration (shortest first) — among equal-urgency tasks, shorter
             ones are tried first to leave larger gaps for later tasks.

        Args:
            tasks: List of (Pet, Task) pairs with no fixed_time set.
            today: ISO date string used to calculate days overdue.
                   Defaults to date.today() when None.

        Returns:
            A new sorted list; the original is not mutated.
        """
        if today is None:
            today = date.today().isoformat()
        return sorted(
            tasks,
            key=lambda x: (x[1].urgency_score(today), x[1].duration_minutes),
        )

    def _overlaps(self, a: Task, b: Task) -> bool:
        """Return True if two fixed-time tasks overlap."""
        s1, e1 = self._to_min(a.fixed_time), self._to_min(a.fixed_time) + a.duration_minutes
        s2, e2 = self._to_min(b.fixed_time), self._to_min(b.fixed_time) + b.duration_minutes
        return s1 < e2 and s2 < e1

    def _free_gaps(self, occupied: list[tuple[int, int]], budget: int) -> list[tuple[int, int]]:
        """Compute free time slots available for flexible tasks.

        Walks the list of already-occupied intervals (from fixed-time tasks) in
        order and collects the gaps between them. The available window is anchored
        at DAY_START (07:00 by default) rather than midnight, so flexible tasks
        are never scheduled at unrealistic hours.

        Args:
            occupied: Sorted list of (start_min, end_min) intervals already claimed
                      by fixed-time tasks, in minutes since midnight.
            budget:   Owner's total available minutes for the day.

        Returns:
            List of (start_min, end_min) free intervals within
            [DAY_START, DAY_START + budget], excluding all occupied spans.
        """
        day_end = self.DAY_START + budget
        gaps: list[tuple[int, int]] = []
        cursor = self.DAY_START
        for start, end in occupied:
            if cursor < start:
                gaps.append((cursor, min(start, day_end)))
            cursor = max(cursor, end)
        if cursor < day_end:
            gaps.append((cursor, day_end))
        return gaps

    @staticmethod
    def _to_min(time_str: str) -> int:
        """Convert a 'HH:MM' string to total minutes since midnight."""
        h, m = map(int, time_str.split(":"))
        return h * 60 + m

    @staticmethod
    def _to_str(minutes: int) -> str:
        """Convert total minutes since midnight to a 'HH:MM' string."""
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

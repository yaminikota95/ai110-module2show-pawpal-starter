from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from enum import Enum
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

    def summary(self) -> str:
        """Return a human-readable string of the full daily plan."""
        lines = [
            f"Plan for {self.owner.name}",
            f"Time budget: {self.owner.available_minutes} min  |  Used: {self.total_minutes_used} min\n",
        ]
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
            lines.append("\nSkipped (did not fit):")
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
      1. Collect all valid, incomplete tasks from every pet.
      2. Place fixed-time tasks first (sorted by time); skip later ones that conflict.
      3. Fill remaining free gaps with flexible tasks, sorted by priority then duration.
    """

    def generate_plan(self, owner: Owner) -> DailyPlan:
        """Build and return a DailyPlan for the given owner."""
        all_tasks = owner.get_all_tasks()

        fixed    = [(p, t) for p, t in all_tasks if t.fixed_time is not None]
        flexible = [(p, t) for p, t in all_tasks if t.fixed_time is None]

        reasoning: list[str] = []
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
                skipped.append(ScheduledTask(task=task, pet=pet, start_time="", end_time=""))
                reasoning.append(
                    f"'{task.title}' ({pet.name}) skipped — conflicts with "
                    f"'{conflict.title}' at {conflict.fixed_time}."
                )
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
        budget = owner.available_minutes - minutes_used

        for pet, task in self._sort_tasks(flexible):
            placed = False
            for i, (gap_start, gap_end) in enumerate(free_gaps):
                if task.duration_minutes <= gap_end - gap_start:
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
                    free_gaps[i] = (gap_start + task.duration_minutes, gap_end)
                    minutes_used += task.duration_minutes
                    budget -= task.duration_minutes
                    placed = True
                    break

            if not placed:
                skipped.append(ScheduledTask(task=task, pet=pet, start_time="", end_time=""))
                reasoning.append(
                    f"'{task.title}' ({pet.name}) skipped — needs {task.duration_minutes} min "
                    f"but only {budget} min remaining."
                )

        return DailyPlan(
            owner=owner,
            scheduled=scheduled,
            skipped=skipped,
            total_minutes_used=minutes_used,
            reasoning=reasoning,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _sort_tasks(self, tasks: list[tuple[Pet, Task]]) -> list[tuple[Pet, Task]]:
        """Sort by priority (HIGH first), then shortest duration first."""
        return sorted(tasks, key=lambda x: (x[1].priority.value, x[1].duration_minutes))

    def _overlaps(self, a: Task, b: Task) -> bool:
        """Return True if two fixed-time tasks overlap."""
        s1, e1 = self._to_min(a.fixed_time), self._to_min(a.fixed_time) + a.duration_minutes
        s2, e2 = self._to_min(b.fixed_time), self._to_min(b.fixed_time) + b.duration_minutes
        return s1 < e2 and s2 < e1

    def _free_gaps(self, occupied: list[tuple[int, int]], budget: int) -> list[tuple[int, int]]:
        """Return free time intervals within [0, budget] not covered by occupied."""
        gaps: list[tuple[int, int]] = []
        cursor = 0
        for start, end in occupied:
            if cursor < start:
                gaps.append((cursor, start))
            cursor = max(cursor, end)
        if cursor < budget:
            gaps.append((cursor, budget))
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

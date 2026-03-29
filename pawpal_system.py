from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Priority(Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3


@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: Priority
    fixed_time: Optional[str] = None  # "HH:MM" or None for flexible
    is_completed: bool = False
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def validate(self) -> bool:
        return self.duration_minutes > 0 and bool(self.title.strip())


@dataclass
class Pet:
    name: str
    species: str
    age: int
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> None:
        self.tasks = [t for t in self.tasks if t.id != task_id]

    def get_tasks(self) -> list[Task]:
        return list(self.tasks)


@dataclass
class Owner:
    name: str
    available_minutes: int = 60
    preferences: list[str] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        self.pets.append(pet)

    def get_pets(self) -> list[Pet]:
        return list(self.pets)


@dataclass
class ScheduledTask:
    task: Task
    pet_name: str
    start_time: str
    end_time: str


@dataclass
class DailyPlan:
    scheduled: list[ScheduledTask]
    skipped: list[tuple[str, Task]]  # (pet_name, task)
    total_minutes_used: int
    reasoning: list[str]

    def summary(self) -> str:
        lines = [f"Total time used: {self.total_minutes_used} min\n"]
        lines.append("Scheduled:")
        for st in self.scheduled:
            lines.append(f"  {st.start_time}–{st.end_time}  [{st.pet_name}] {st.task.title}")
        if self.skipped:
            lines.append("\nSkipped (did not fit):")
            for pet_name, task in self.skipped:
                lines.append(f"  [{pet_name}] {task.title} ({task.duration_minutes} min)")
        return "\n".join(lines)


class Scheduler:
    def __init__(self, owner: Owner):
        self.owner = owner

    def generate_plan(self) -> DailyPlan:
        all_tasks: list[tuple[str, Task]] = [
            (pet.name, task)
            for pet in self.owner.get_pets()
            for task in pet.get_tasks()
            if not task.is_completed and task.validate()
        ]

        fixed = [(n, t) for n, t in all_tasks if t.fixed_time is not None]
        flexible = [(n, t) for n, t in all_tasks if t.fixed_time is None]

        conflicts = self._detect_conflicts(fixed)
        reasoning: list[str] = []
        if conflicts:
            reasoning.extend(conflicts)

        sorted_flexible = self._sort_tasks(flexible)

        scheduled: list[ScheduledTask] = []
        skipped: list[tuple[str, Task]] = []
        minutes_used = 0

        # Place fixed-time tasks first
        for pet_name, task in fixed:
            start_min = self._time_to_minutes(task.fixed_time)
            end_min = start_min + task.duration_minutes
            scheduled.append(ScheduledTask(
                task=task,
                pet_name=pet_name,
                start_time=task.fixed_time,
                end_time=self._minutes_to_time(end_min),
            ))
            minutes_used += task.duration_minutes
            reasoning.append(
                f"'{task.title}' ({pet_name}) fixed at {task.fixed_time} — placed as required."
            )

        # Greedily fill remaining budget with flexible tasks
        budget = self.owner.available_minutes - minutes_used
        cursor = minutes_used  # simple sequential placement after fixed tasks

        for pet_name, task in sorted_flexible:
            if task.duration_minutes <= budget:
                start_time = self._minutes_to_time(cursor)
                end_time = self._minutes_to_time(cursor + task.duration_minutes)
                scheduled.append(ScheduledTask(
                    task=task,
                    pet_name=pet_name,
                    start_time=start_time,
                    end_time=end_time,
                ))
                reasoning.append(
                    f"'{task.title}' ({pet_name}) scheduled at {start_time} "
                    f"[{task.priority.name} priority, {task.duration_minutes} min]."
                )
                cursor += task.duration_minutes
                budget -= task.duration_minutes
                minutes_used += task.duration_minutes
            else:
                skipped.append((pet_name, task))
                reasoning.append(
                    f"'{task.title}' ({pet_name}) skipped — needs {task.duration_minutes} min "
                    f"but only {budget} min remaining."
                )

        return DailyPlan(
            scheduled=scheduled,
            skipped=skipped,
            total_minutes_used=minutes_used,
            reasoning=reasoning,
        )

    def _sort_tasks(self, tasks: list[tuple[str, Task]]) -> list[tuple[str, Task]]:
        return sorted(tasks, key=lambda x: (x[1].priority.value, x[1].duration_minutes))

    def _detect_conflicts(self, fixed: list[tuple[str, Task]]) -> list[str]:
        conflicts = []
        for i, (n1, t1) in enumerate(fixed):
            s1 = self._time_to_minutes(t1.fixed_time)
            e1 = s1 + t1.duration_minutes
            for n2, t2 in fixed[i + 1:]:
                s2 = self._time_to_minutes(t2.fixed_time)
                e2 = s2 + t2.duration_minutes
                if s1 < e2 and s2 < e1:
                    conflicts.append(
                        f"Conflict: '{t1.title}' ({n1}) and '{t2.title}' ({n2}) overlap."
                    )
        return conflicts

    @staticmethod
    def _time_to_minutes(time_str: str) -> int:
        h, m = map(int, time_str.split(":"))
        return h * 60 + m

    @staticmethod
    def _minutes_to_time(minutes: int) -> str:
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

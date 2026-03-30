from pawpal_system import Owner, Pet, Task, Priority, Frequency, Scheduler

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
owner = Owner(name="Jordan", available_minutes=120)

mochi = Pet(name="Mochi", species="dog", age=3)
luna  = Pet(name="Luna",  species="cat", age=5)

# --- Tasks added INTENTIONALLY OUT OF ORDER ---
# (late fixed time first, then low-priority, then early fixed time, etc.)

mochi.add_task(Task(
    title="Evening walk",
    duration_minutes=25,
    priority=Priority.MEDIUM,
    fixed_time="17:30",
    frequency=Frequency.DAILY,
))
mochi.add_task(Task(
    title="Fetch / playtime",
    duration_minutes=20,
    priority=Priority.LOW,
    frequency=Frequency.DAILY,
))
mochi.add_task(Task(
    title="Flea medication",
    duration_minutes=5,
    priority=Priority.HIGH,
    fixed_time="09:00",
    frequency=Frequency.WEEKLY,
))
mochi.add_task(Task(
    title="Morning walk",
    duration_minutes=30,
    priority=Priority.HIGH,
    fixed_time="08:00",
    frequency=Frequency.DAILY,
))
mochi.add_task(Task(
    title="Teeth brushing",
    duration_minutes=5,
    priority=Priority.MEDIUM,
    frequency=Frequency.DAILY,
))

luna.add_task(Task(
    title="Vet appointment",
    duration_minutes=60,
    priority=Priority.HIGH,
    fixed_time="14:00",
    frequency=Frequency.ONCE,
))
luna.add_task(Task(
    title="Brush fur",
    duration_minutes=10,
    priority=Priority.LOW,
    frequency=Frequency.DAILY,
))
luna.add_task(Task(
    title="Clean litter box",
    duration_minutes=5,
    priority=Priority.HIGH,
    frequency=Frequency.DAILY,
))
luna.add_task(Task(
    title="Morning feeding",
    duration_minutes=5,
    priority=Priority.HIGH,
    fixed_time="07:30",
    frequency=Frequency.DAILY,
))
# Intentional conflict: Luna's insulin shot overlaps Mochi's morning walk (both at 08:00)
luna.add_task(Task(
    title="Insulin shot",
    duration_minutes=10,
    priority=Priority.HIGH,
    fixed_time="08:00",
    frequency=Frequency.DAILY,
))

owner.add_pet(mochi)
owner.add_pet(luna)

# Mark tasks complete via the new complete_task() to trigger recurrence
fetch_id = mochi.get_tasks()[1].id    # Fetch / playtime  (DAILY  → successor spawned)
flea_id  = mochi.get_tasks()[2].id    # Flea medication   (WEEKLY → successor spawned, locked 7 days)
vet_id   = luna.get_tasks()[0].id     # Vet appointment   (ONCE   → no successor)

mochi.complete_task(fetch_id)
mochi.complete_task(flea_id)
luna.complete_task(vet_id)

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def print_section(title: str) -> None:
    print(f"\n{'=' * 50}")
    print(f"  {title}")
    print('=' * 50)

def print_pairs(pairs):
    if not pairs:
        print("  (none)")
        return
    for pet, task in pairs:
        status = "[x]" if task.is_completed else "[ ]"
        time   = task.fixed_time or "flexible"
        print(f"  {status} [{pet.name:5}] {task.priority.name:6} | {time:8} | {task.title}")

# ---------------------------------------------------------------------------
# 0. Recurrence demo
# ---------------------------------------------------------------------------
print_section("RECURRENCE — after completing 3 tasks")
print("  Completed:  Fetch/playtime (DAILY), Flea medication (WEEKLY), Vet appt (ONCE)")
print()
print("  Mochi full task list (include completed):")
for t in mochi.get_tasks(include_completed=True):
    status = "[x]" if t.is_completed else "[ ]"
    print(f"    {status} {t.frequency.value:6} | {t.title} (due_date={t.due_date})")
print()
print("  Luna full task list (include completed):")
for t in luna.get_tasks(include_completed=True):
    status = "[x]" if t.is_completed else "[ ]"
    print(f"    {status} {t.frequency.value:6} | {t.title} (due_date={t.due_date})")

# ---------------------------------------------------------------------------
# 1. Raw insertion order (before any sorting)
# ---------------------------------------------------------------------------
print_section("RAW INSERTION ORDER — all tasks, no sort")
print_pairs(owner.filter_tasks())

# ---------------------------------------------------------------------------
# 2. Sorted by time: fixed-time first (chronological), flexible after
# ---------------------------------------------------------------------------
print_section("SORTED BY TIME (fixed=chronological, flexible=priority)")
all_tasks = owner.filter_tasks()
sorted_tasks = sorted(
    all_tasks,
    key=lambda x: (x[1].fixed_time or "99:99", x[1].priority.value)
)
print_pairs(sorted_tasks)

# ---------------------------------------------------------------------------
# 3. Filter: Mochi's tasks only
# ---------------------------------------------------------------------------
print_section("FILTER — Mochi only")
print_pairs(owner.filter_tasks(pet_name="Mochi"))

# ---------------------------------------------------------------------------
# 4. Filter: Luna's tasks only
# ---------------------------------------------------------------------------
print_section("FILTER — Luna only")
print_pairs(owner.filter_tasks(pet_name="Luna"))

# ---------------------------------------------------------------------------
# 5. Filter: pending tasks only (across all pets)
# ---------------------------------------------------------------------------
print_section("FILTER — Pending only (all pets)")
print_pairs(owner.filter_tasks(completed=False))

# ---------------------------------------------------------------------------
# 6. Filter: completed tasks only
# ---------------------------------------------------------------------------
print_section("FILTER — Completed only")
print_pairs(owner.filter_tasks(completed=True))

# ---------------------------------------------------------------------------
# 7. Filter: Mochi + pending only (combined filters)
# ---------------------------------------------------------------------------
print_section("FILTER — Mochi + Pending only")
print_pairs(owner.filter_tasks(pet_name="Mochi", completed=False))

# ---------------------------------------------------------------------------
# 8. Generated schedule (uses all sorting + conflict detection internally)
# ---------------------------------------------------------------------------
print_section("TODAY'S SCHEDULE")
plan = Scheduler().generate_plan(owner)
print(plan.summary())

if plan.warnings:
    print("\n--- Conflict Warnings ---")
    for w in plan.warnings:
        print(f"  [!] {w}")
else:
    print("\n  No conflicts detected.")

print("\n--- Reasoning ---")
for line in plan.reasoning:
    print(f"  • {line}")

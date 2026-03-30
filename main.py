from pawpal_system import Owner, Pet, Task, Priority, Frequency, Scheduler

# --- Setup ---
owner = Owner(name="Jordan", available_minutes=90)

mochi = Pet(name="Mochi", species="dog", age=3)
luna  = Pet(name="Luna",  species="cat", age=5)

# --- Tasks for Mochi ---
mochi.add_task(Task(
    title="Morning walk",
    duration_minutes=30,
    priority=Priority.HIGH,
    fixed_time="08:00",
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
    title="Fetch / playtime",
    duration_minutes=20,
    priority=Priority.MEDIUM,
    frequency=Frequency.DAILY,
))

# --- Tasks for Luna ---
luna.add_task(Task(
    title="Brush fur",
    duration_minutes=10,
    priority=Priority.MEDIUM,
    frequency=Frequency.DAILY,
))
luna.add_task(Task(
    title="Clean litter box",
    duration_minutes=5,
    priority=Priority.HIGH,
    frequency=Frequency.DAILY,
))

owner.add_pet(mochi)
owner.add_pet(luna)

# --- Generate plan ---
plan = Scheduler().generate_plan(owner)

# --- Print schedule ---
print("=" * 45)
print("         TODAY'S SCHEDULE")
print("=" * 45)
print(plan.summary())
print()
print("--- Reasoning ---")
for line in plan.reasoning:
    print(f"  • {line}")
print("=" * 45)

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from colorama import Fore, Style, init as colorama_init
from tabulate import tabulate

from pawpal_system import Owner, Pet, Task, Priority, Frequency, Scheduler

colorama_init(autoreset=True)   # Windows-safe ANSI colors; resets after each print

# ---------------------------------------------------------------------------
# Display constants
# ---------------------------------------------------------------------------

PRIORITY_COLOR = {
    Priority.HIGH:   Fore.RED,
    Priority.MEDIUM: Fore.YELLOW,
    Priority.LOW:    Fore.GREEN,
}
PRIORITY_ICON = {
    Priority.HIGH:   "🔴",
    Priority.MEDIUM: "🟡",
    Priority.LOW:    "🟢",
}
FREQ_ICON = {
    Frequency.DAILY:  "🔄",
    Frequency.WEEKLY: "📅",
    Frequency.ONCE:   "1️⃣ ",
}

TASK_KEYWORDS = {
    "walk":        "🦮",
    "run":         "🏃",
    "feed":        "🍽️ ",
    "food":        "🍽️ ",
    "meal":        "🍽️ ",
    "medication":  "💊",
    "medicine":    "💊",
    "meds":        "💊",
    "insulin":     "💊",
    "flea":        "💊",
    "vet":         "🏥",
    "appointment": "🏥",
    "brush":       "🪥",
    "teeth":       "🪥",
    "groom":       "✂️ ",
    "bath":        "🛁",
    "litter":      "🧹",
    "clean":       "🧹",
    "play":        "🎾",
    "fetch":       "🎾",
    "toy":         "🎾",
    "nap":         "😴",
    "sleep":       "😴",
    "training":    "🎓",
    "shot":        "💉",
    "vaccine":     "💉",
}


def task_emoji(title: str) -> str:
    """Return the best-matching emoji for a task title, or 📋 as fallback."""
    lower = title.lower()
    for keyword, icon in TASK_KEYWORDS.items():
        if keyword in lower:
            return icon
    return "📋"


def priority_cell(p: Priority) -> str:
    return f"{PRIORITY_COLOR[p]}{PRIORITY_ICON[p]} {p.name}{Style.RESET_ALL}"


def status_cell(is_completed: bool) -> str:
    if is_completed:
        return f"{Fore.WHITE}{Style.DIM}✅ Done{Style.RESET_ALL}"
    return f"{Fore.CYAN}⏳ Pending{Style.RESET_ALL}"


def freq_cell(f: Frequency) -> str:
    return f"{FREQ_ICON[f]} {f.value}"


# ---------------------------------------------------------------------------
# Section header
# ---------------------------------------------------------------------------

def section(title: str) -> None:
    width = 62
    bar   = "─" * width
    print()
    print(f"{Fore.CYAN}{Style.BRIGHT}┌{bar}┐")
    print(f"│  {title:<{width - 2}}│")
    print(f"└{bar}┘{Style.RESET_ALL}")


def banner() -> None:
    width = 62
    bar   = "=" * width
    print(f"\n{Fore.MAGENTA}{Style.BRIGHT}")
    print(f"  {bar}")
    print(f"  {'PawPal+  🐾  Pet Care Scheduler':^{width}}")
    print(f"  {'Priority  •  Recurrence  •  Conflict Detection':^{width}}")
    print(f"  {bar}")
    print(Style.RESET_ALL)


# ---------------------------------------------------------------------------
# Table helpers
# ---------------------------------------------------------------------------

def task_rows(pairs, include_due: bool = False) -> list[list]:
    rows = []
    for pet, task in pairs:
        row = [
            f"{task_emoji(task.title)} {task.title}",
            f"{Fore.BLUE}{Style.BRIGHT}{pet.name}{Style.RESET_ALL}",
            priority_cell(task.priority),
            task.fixed_time or f"{Fore.WHITE}{Style.DIM}flexible{Style.RESET_ALL}",
            freq_cell(task.frequency),
            status_cell(task.is_completed),
        ]
        if include_due:
            row.append(task.due_date or "—")
        rows.append(row)
    return rows


def print_task_table(pairs, title: str = "", include_due: bool = False) -> None:
    if not pairs:
        print(f"  {Fore.WHITE}{Style.DIM}(none){Style.RESET_ALL}")
        return
    headers = ["Task", "Pet", "Priority", "Time", "Freq", "Status"]
    if include_due:
        headers.append("Due date")
    print(tabulate(
        task_rows(pairs, include_due=include_due),
        headers=headers,
        tablefmt="rounded_outline",
    ))


# ---------------------------------------------------------------------------
# Setup — identical scenario to original main.py
# ---------------------------------------------------------------------------

owner = Owner(name="Jordan", available_minutes=120)

mochi = Pet(name="Mochi", species="dog", age=3)
luna  = Pet(name="Luna",  species="cat", age=5)

mochi.add_task(Task("Evening walk",    25, Priority.MEDIUM, fixed_time="17:30", frequency=Frequency.DAILY))
mochi.add_task(Task("Fetch / playtime", 20, Priority.LOW,                       frequency=Frequency.DAILY))
mochi.add_task(Task("Flea medication",  5, Priority.HIGH,   fixed_time="09:00", frequency=Frequency.WEEKLY))
mochi.add_task(Task("Morning walk",    30, Priority.HIGH,   fixed_time="08:00", frequency=Frequency.DAILY))
mochi.add_task(Task("Teeth brushing",   5, Priority.MEDIUM,                    frequency=Frequency.DAILY))

luna.add_task(Task("Vet appointment",  60, Priority.HIGH,   fixed_time="14:00", frequency=Frequency.ONCE))
luna.add_task(Task("Brush fur",        10, Priority.LOW,                        frequency=Frequency.DAILY))
luna.add_task(Task("Clean litter box",  5, Priority.HIGH,                       frequency=Frequency.DAILY))
luna.add_task(Task("Morning feeding",   5, Priority.HIGH,   fixed_time="07:30", frequency=Frequency.DAILY))
# Intentional conflict: Luna's insulin shot overlaps Mochi's morning walk (both 08:00)
luna.add_task(Task("Insulin shot",     10, Priority.HIGH,   fixed_time="08:00", frequency=Frequency.DAILY))

owner.add_pet(mochi)
owner.add_pet(luna)

# Complete three tasks to trigger recurrence demo
fetch_id = mochi.get_tasks()[1].id   # Fetch / playtime  → DAILY successor
flea_id  = mochi.get_tasks()[2].id   # Flea medication   → WEEKLY successor
vet_id   = luna.get_tasks()[0].id    # Vet appointment   → ONCE, no successor

mochi.complete_task(fetch_id)
mochi.complete_task(flea_id)
luna.complete_task(vet_id)

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

banner()

# ── 0. Recurrence demo ──────────────────────────────────────────────────────
section("RECURRENCE  —  after completing 3 tasks")
print(f"  Completed: {Fore.YELLOW}Fetch/playtime{Style.RESET_ALL} (DAILY), "
      f"{Fore.YELLOW}Flea medication{Style.RESET_ALL} (WEEKLY), "
      f"{Fore.YELLOW}Vet appointment{Style.RESET_ALL} (ONCE)\n")

for pet_obj in [mochi, luna]:
    print(f"  {Fore.BLUE}{Style.BRIGHT}── {pet_obj.name} ──{Style.RESET_ALL}")
    rows = [
        [
            f"{task_emoji(t.title)} {t.title}",
            freq_cell(t.frequency),
            status_cell(t.is_completed),
            t.due_date or "—",
        ]
        for t in pet_obj.get_tasks(include_completed=True)
    ]
    print(tabulate(rows,
                   headers=["Task", "Freq", "Status", "Due date"],
                   tablefmt="rounded_outline"))
    print()

# ── 1. Raw insertion order ───────────────────────────────────────────────────
section("RAW INSERTION ORDER  —  all tasks, no sort")
print_task_table(owner.filter_tasks())

# ── 2. Sorted by time ────────────────────────────────────────────────────────
section("SORTED BY TIME  (fixed=chronological, flexible=priority)")
all_tasks = owner.filter_tasks()
sorted_tasks = sorted(all_tasks, key=lambda x: (x[1].fixed_time or "99:99", x[1].priority.value))
print_task_table(sorted_tasks)

# ── 3–7. Filters ─────────────────────────────────────────────────────────────
section("FILTER  —  Mochi only")
print_task_table(owner.filter_tasks(pet_name="Mochi"))

section("FILTER  —  Luna only")
print_task_table(owner.filter_tasks(pet_name="Luna"))

section("FILTER  —  Pending only (all pets)")
print_task_table(owner.filter_tasks(completed=False))

section("FILTER  —  Completed only")
print_task_table(owner.filter_tasks(completed=True))

section("FILTER  —  Mochi + Pending only")
print_task_table(owner.filter_tasks(pet_name="Mochi", completed=False))

# ── 8. Today's schedule ───────────────────────────────────────────────────────
section("TODAY'S SCHEDULE")
plan = Scheduler().generate_plan(owner)

# Budget bar
pct   = min(plan.total_minutes_used / owner.available_minutes, 1.0)
filled = int(pct * 30)
bar   = f"{Fore.GREEN}{'█' * filled}{Fore.WHITE}{'░' * (30 - filled)}{Style.RESET_ALL}"
print(f"\n  Time budget  {bar}  "
      f"{Fore.CYAN}{plan.total_minutes_used}{Style.RESET_ALL} / "
      f"{owner.available_minutes} min\n")

# Conflict warnings
if plan.warnings:
    print(f"  {Fore.RED}{Style.BRIGHT}⚠️  CONFLICT WARNINGS{Style.RESET_ALL}")
    for w in plan.warnings:
        print(f"  {Fore.RED}  ✗  {w}{Style.RESET_ALL}")
    print()

# Scheduled tasks
if plan.scheduled:
    sched_rows = [
        [
            f"{Fore.CYAN}{s.start_time}–{s.end_time}{Style.RESET_ALL}",
            f"{task_emoji(s.task.title)} {s.task.title}",
            f"{Fore.BLUE}{Style.BRIGHT}{s.pet_name}{Style.RESET_ALL}",
            priority_cell(s.task.priority),
            f"{s.task.duration_minutes} min",
        ]
        for s in plan.scheduled
    ]
    print(tabulate(sched_rows,
                   headers=["Time slot", "Task", "Pet", "Priority", "Duration"],
                   tablefmt="rounded_outline"))

# Skipped tasks
if plan.skipped:
    print(f"\n  {Fore.YELLOW}{Style.BRIGHT}Skipped  ({len(plan.skipped)} task(s) did not fit or conflicted){Style.RESET_ALL}")
    skip_rows = [
        [
            f"{task_emoji(s.task.title)} {s.task.title}",
            f"{Fore.BLUE}{Style.BRIGHT}{s.pet_name}{Style.RESET_ALL}",
            priority_cell(s.task.priority),
            f"{s.task.duration_minutes} min",
            f"{Fore.RED}conflict{Style.RESET_ALL}"
            if any(s.task.title in w for w in plan.warnings)
            else f"{Fore.YELLOW}no gap{Style.RESET_ALL}",
        ]
        for s in plan.skipped
    ]
    print(tabulate(skip_rows,
                   headers=["Task", "Pet", "Priority", "Duration", "Reason"],
                   tablefmt="rounded_outline"))

# Outcome summary
print()
if plan.warnings:
    print(f"  {Fore.RED}● {len(plan.warnings)} conflict(s) detected — see warnings above.{Style.RESET_ALL}")
else:
    print(f"  {Fore.GREEN}✔  Schedule built cleanly — no conflicts detected.{Style.RESET_ALL}")

# Reasoning log
section("SCHEDULER REASONING LOG")
for line in plan.reasoning:
    marker = f"{Fore.RED}✗{Style.RESET_ALL}" if "conflict" in line.lower() or "skipped" in line.lower() \
        else f"{Fore.GREEN}✔{Style.RESET_ALL}"
    print(f"  {marker}  {line}")

print()

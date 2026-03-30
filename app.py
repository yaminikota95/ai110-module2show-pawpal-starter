import streamlit as st
from pawpal_system import Owner, Pet, Task, Priority, Frequency, Scheduler, DailyPlan

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# ---------------------------------------------------------------------------
# Session state — initialize once per browser session
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan", available_minutes=60)

if "pet" not in st.session_state:
    default_pet = Pet(name="Mochi", species="dog", age=3)
    st.session_state.owner.add_pet(default_pet)
    st.session_state.pet = default_pet

# ---------------------------------------------------------------------------
# Owner + Pet setup
# ---------------------------------------------------------------------------
st.subheader("Owner & Pet")

col1, col2 = st.columns(2)
with col1:
    owner_name = st.text_input("Owner name", value=st.session_state.owner.name)
    available_minutes = st.number_input(
        "Available minutes today", min_value=10, max_value=480,
        value=st.session_state.owner.available_minutes,
    )
with col2:
    pet_name = st.text_input("Pet name", value=st.session_state.pet.name)
    species  = st.selectbox(
        "Species", ["dog", "cat", "other"],
        index=["dog", "cat", "other"].index(st.session_state.pet.species),
    )

if st.button("Save owner & pet"):
    st.session_state.owner.name              = owner_name
    st.session_state.owner.available_minutes = available_minutes
    st.session_state.pet.name                = pet_name
    st.session_state.pet.species             = species
    st.success(f"Saved: {owner_name} with {pet_name} ({species}), {available_minutes} min budget.")

st.divider()

# ---------------------------------------------------------------------------
# Add a task
# ---------------------------------------------------------------------------
st.subheader("Tasks")

col1, col2, col3, col4 = st.columns(4)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
with col3:
    priority_label = st.selectbox("Priority", ["HIGH", "MEDIUM", "LOW"])
with col4:
    fixed_time = st.text_input("Fixed time (HH:MM)", placeholder="optional")

if st.button("Add task"):
    task = Task(
        title=task_title,
        duration_minutes=int(duration),
        priority=Priority[priority_label],
        fixed_time=fixed_time.strip() or None,
    )
    if not task.validate():
        st.error("Invalid task — check the title, duration, or time format (HH:MM).")
    else:
        st.session_state.pet.add_task(task)
        st.success(f"Added '{task_title}' to {st.session_state.pet.name}.")

# --- Filter controls ---
owner = st.session_state.owner
pet_names = ["All"] + [p.name for p in owner.get_pets()]
col_f1, col_f2 = st.columns(2)
with col_f1:
    filter_pet = st.selectbox("Filter by pet", pet_names)
with col_f2:
    filter_status = st.radio("Filter by status", ["Pending", "All", "Completed"], horizontal=True)

status_map = {"Pending": False, "Completed": True, "All": None}

filtered = owner.filter_tasks(
    pet_name=None if filter_pet == "All" else filter_pet,
    completed=status_map[filter_status],
)

# Use Scheduler._sort_tasks for flexible tasks; fixed-time tasks sorted chronologically
_scheduler = Scheduler()
fixed_pairs    = [(p, t) for p, t in filtered if t.fixed_time is not None]
flexible_pairs = [(p, t) for p, t in filtered if t.fixed_time is None]

fixed_pairs.sort(key=lambda x: x[1].fixed_time)
flexible_pairs = _scheduler._sort_tasks(flexible_pairs)

sorted_filtered = fixed_pairs + flexible_pairs

if sorted_filtered:
    priority_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
    st.dataframe(
        [
            {
                "Pet": p.name,
                "Task": t.title,
                "Priority": f"{priority_icon.get(t.priority.name, '')} {t.priority.name}",
                "Duration (min)": t.duration_minutes,
                "Time": t.fixed_time or "flexible",
                "Frequency": t.frequency.value,
                "Status": "✅ Done" if t.is_completed else "⏳ Pending",
            }
            for p, t in sorted_filtered
        ],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No tasks match the current filters.")

st.divider()

# ---------------------------------------------------------------------------
# Generate schedule
# ---------------------------------------------------------------------------
st.subheader("Today's Schedule")

if st.button("Generate schedule"):
    owner = st.session_state.owner
    if not owner.get_all_tasks():
        st.warning("Add at least one task before generating a schedule.")
    else:
        plan: DailyPlan = Scheduler().generate_plan(owner)

        # --- Conflict warnings — shown first so they're impossible to miss ---
        if plan.warnings:
            for w in plan.warnings:
                st.warning(f"⚠️ Conflict detected: {w}")

        # --- Summary metrics ---
        budget = owner.available_minutes
        used   = plan.total_minutes_used
        remaining = budget - used

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Scheduled", len(plan.scheduled))
        m2.metric("Skipped",   len(plan.skipped))
        m3.metric("Min used",  used)
        m4.metric("Min left",  remaining)

        st.progress(min(used / budget, 1.0), text=f"{used} / {budget} min used")

        if plan.warnings:
            st.error(
                f"{len(plan.warnings)} conflict(s) found — see warnings above. "
                "Conflicting tasks were moved to the skipped list."
            )
        else:
            st.success(
                f"Schedule built cleanly — {len(plan.scheduled)} task(s) placed, "
                "no conflicts detected."
            )

        # --- Scheduled tasks table ---
        if plan.scheduled:
            st.markdown("**Scheduled tasks** (chronological order)")
            priority_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
            st.dataframe(
                [
                    {
                        "Start": s.start_time,
                        "End":   s.end_time,
                        "Pet":   s.pet_name,
                        "Task":  s.task.title,
                        "Priority": (
                            f"{priority_icon.get(s.task.priority.name, '')} "
                            f"{s.task.priority.name}"
                        ),
                        "Duration (min)": s.task.duration_minutes,
                    }
                    for s in plan.scheduled   # already sorted by Scheduler
                ],
                use_container_width=True,
                hide_index=True,
            )

        # --- Skipped tasks table ---
        if plan.skipped:
            st.markdown("**Skipped tasks** (did not fit or conflicted)")
            st.dataframe(
                [
                    {
                        "Pet":  s.pet_name,
                        "Task": s.task.title,
                        "Duration (min)": s.task.duration_minutes,
                        "Reason": (
                            "conflict" if any(s.task.title in w for w in plan.warnings)
                            else "no time remaining"
                        ),
                    }
                    for s in plan.skipped
                ],
                use_container_width=True,
                hide_index=True,
            )

        # --- Reasoning log ---
        with st.expander("Scheduler reasoning log"):
            for line in plan.reasoning:
                st.write(f"- {line}")

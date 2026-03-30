# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

I designed six classes. `Owner` holds the user's name and how many minutes they have available in a day, and it owns a list of pets. `Pet` stores a pet's name, species, and age, and is responsible for managing its own list of tasks. `Task` is the core data unit — it holds a title, duration in minutes, priority level, an optional fixed start time for things like medication, and a completion flag. `Priority` is a simple enum (HIGH, MEDIUM, LOW) kept separate so sorting stays clean. `Scheduler` is the brain of the system: it takes an `Owner`, collects all tasks across all pets, sorts them by priority, and greedily fits them into the available time budget while detecting conflicts between fixed-time tasks. Finally, `DailyPlan` is the output object — it holds the list of scheduled tasks, the tasks that didn't fit, total minutes used, and a human-readable reasoning list that explains each scheduling decision.

The key responsibility split was: `Owner`, `Pet`, and `Task` are pure data with no scheduling logic, `Scheduler` owns all the scheduling logic, and `DailyPlan` owns all the output and display logic. This keeps the scheduler fully testable without touching the UI.

**b. Design changes**


None


---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers three constraints: available time, task priority, and fixed-time anchoring. Available time is the hard outer limit — the owner sets a daily minute budget and no task can be placed beyond it. Fixed-time anchoring is the next hard constraint: tasks like medication have to happen at a specific hour, so those slots are reserved before anything else is placed. Priority is the soft constraint that governs everything flexible — HIGH tasks are always attempted before MEDIUM or LOW, and within the same priority level shorter tasks go first to avoid large tasks consuming gaps that several smaller ones could share.

I decided these three mattered most by asking what would actually break the schedule if ignored. Ignoring available time means overbooking the day — an immediate practical failure. Ignoring fixed times means a medication task could get bumped to an arbitrary slot — a correctness failure. Ignoring priority just makes the order arbitrary, which is less harmful but defeats the purpose of the app. Everything else — owner preferences, pet species, age — could refine decisions but isn't load-bearing for a correct schedule, so it was left out of the core algorithm.

**b. Tradeoffs**


One tradeoff the scheduler makes is that it uses a greedy "first fit" strategy when placing flexible tasks into free time gaps. This means it takes the first gap that's large enough and fills it immediately, rather than looking ahead to find the best possible slot. For example, if a 20-minute task could fit in either a 25-minute gap at 7 AM or a 60-minute gap at noon, the scheduler always picks the 7 AM slot — even if a later 25-minute task could have used that small gap more efficiently, leaving the larger gap available for something bigger.

The reason this tradeoff is reasonable for a pet care app is that daily pet tasks don't really require optimal packing. A dog doesn't care whether their walk happens at 7:05 or 7:30 — what matters is that it happens, that high-priority tasks go first, and that the schedule is predictable and easy to read. A more "optimal" algorithm like dynamic programming or backtracking would find better solutions but would also be much harder to explain, debug, and extend. The greedy approach produces a schedule that's good enough in practice and fails gracefully: when something doesn't fit, it tells you exactly why in plain language instead of silently rearranging everything in ways that are hard to follow.

---

## 3. AI Collaboration

**a. How you used AI**

The most effective features were the ones tied to concrete algorithms rather than vague goals. Asking the AI to implement `_sort_tasks()` with a specific two-key comparator (priority value, then duration) produced clean, testable code immediately. Similarly, prompting it to write `_detect_conflicts()` using `itertools.combinations` with an early-break condition gave me something I could reason about and unit-test directly. The recurring task feature — `next_occurrence()` returning a fresh `Task` with a `timedelta`-calculated `due_date` — also came out well because the requirement was precise: one method, pure output, no side effects.

Prompts that were most useful shared a pattern: they described the input, the expected output, and the constraint (e.g. "return None for ONCE tasks, don't mutate the original"). Vague prompts like "make scheduling smarter" were not useful and produced suggestions I had to discard.

**b. Judgment and verification**

Early in the build, the AI suggested adding a `Schedule` class that sat between `Scheduler` and `DailyPlan` — essentially a mutable intermediate object that tasks would be added to during planning before being frozen into a `DailyPlan`. I rejected it. The extra class added state without adding capability: `Scheduler.generate_plan()` already builds everything in local variables and returns an immutable `DailyPlan` in one pass. Introducing a mutable intermediate would have made the flow harder to test and harder to follow. I verified my instinct by tracing through `generate_plan()` and confirming that no caller ever needed to inspect mid-build state — the output object was always the right boundary.

The general check I applied: if a suggested abstraction only exists to serve one method in one class, it probably shouldn't exist.

---

## 4. Testing and Verification

**a. What you tested**

I tested three behaviors: sorting correctness, recurring task lifecycle, and conflict detection. Sorting tests verified that `_sort_tasks()` places HIGH before LOW, resolves ties by shortest duration, and that `generate_plan()` always returns the final schedule in wall-clock order. Recurrence tests confirmed that completing a DAILY task appends a successor with `due_date = today + 1`, a WEEKLY task appends one at `today + 7`, a ONCE task produces no successor, and that future `due_date` values correctly exclude a task from today's plan. Conflict tests checked that overlapping fixed-time tasks generate a warning, that the conflicting task lands in `skipped`, and that back-to-back tasks (end time == start time) are correctly treated as non-overlapping.

These were the most important behaviors to test because they are the ones that fail silently if broken. A sorting bug doesn't crash the app — it just produces a misleading schedule. A recurrence bug means tasks quietly disappear or duplicate across days. A conflict bug means two tasks get placed in the same time slot with no warning. All three would be hard to catch by manual testing but easy to miss in production.

**b. Confidence**

I'm confident the core scheduling logic is correct — all 17 tests pass and the tested paths cover the main failure modes. My confidence drops for multi-pet scenarios and budget-boundary edge cases: those code paths exist and work in manual testing but have no automated coverage. The Streamlit UI is entirely untested at the unit level, so any regression there would only surface by running the app. If I had more time I'd add tests for an owner with two pets whose tasks conflict with each other, a task whose duration exactly equals the remaining budget, and the case where `available_minutes` is smaller than every task in the list.

---

## 5. Reflection

**a. What went well**

The separation between `pawpal_system.py` and `app.py` worked better than expected. Because `Scheduler` is stateless and `DailyPlan` is an immutable output object, I could write and run all 17 tests without ever importing Streamlit. That boundary made debugging fast — if a test failed, the problem was guaranteed to be in the logic, not the UI. The two-pass conflict detection also came out cleaner than planned: the placement pass catches conflicts as they happen, and `_detect_conflicts()` acts as a silent safety net after the fact. Having both passes meant I could test each independently.

**b. What you would improve**

The UI only supports one pet per session. The data model already handles multiple pets correctly — `Owner` holds a list, `filter_tasks` works across all of them — but the form in `app.py` only creates and edits a single pet. I'd add a pet selector so owners with more than one animal can manage all of them without rewriting the backend. I'd also add persistence: right now everything resets on page refresh, which makes the recurring task feature nearly useless in practice since the successor tasks disappear the moment you close the tab. A simple JSON file or SQLite store would make the recurrence logic worth using.

**c. Key takeaway — AI strategy and being lead architect**

Separating the work into phases — design first, then logic, then UI, then tests — made AI collaboration significantly more manageable. Each session had a single clear scope, which meant the AI's suggestions stayed relevant and I wasn't juggling half-built pieces across concerns. When the design session was done, the data model was locked; the logic session couldn't accidentally reshape it because I wasn't asking design questions anymore.

The most important thing I learned is that the AI is a very fast, very confident executor — but it has no stake in the architecture. It will implement whatever you describe, including designs that create more complexity than they solve. Staying in the lead-architect role meant treating every suggestion as a pull request: read it, understand it, and only merge it if it fits the system you're building. The moments where I pushed back — rejecting the intermediate `Schedule` class, insisting on pure functions for the scheduler helpers — kept the codebase smaller and more testable than it would have been if I had accepted everything. Speed is only useful if what gets built is what you actually wanted.

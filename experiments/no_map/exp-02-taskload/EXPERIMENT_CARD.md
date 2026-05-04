# EXPERIMENT 02: TASK LOAD STRESS TEST

## EXPERIMENT METADATA
- **Experiment ID**: EXP-02-TASKLOAD
- **Date Created**: 2026-02-04
- **Objective**: Validate task queue management and system saturation behavior

## OBJECTIVES
- **Primary**: Test if task generation, queuing, and assignment systems work correctly under varying load conditions
- **Secondary**: Identify system capacity limits and observe agent utilization patterns

## VARIABLE PARAMETER
- **Parameter**: `tasks.arrival_rate` (tasks spawned per hour)
- **Scenario A**: 3 tasks/hour (low load, under-saturated)
- **Scenario B**: 8 tasks/hour (medium load)
- **Scenario C**: 15 tasks/hour (high load, over-saturated)

## FIXED PARAMETERS
- `simulation.duration`: 1000 steps
- `simulation.seed`: 42
- `humans`: 3 total (human_1: 2, human_2: 1)
- `robots`: 3 total (robot_1: 2, robot_2: 1)
- `battery.recharge_trigger`: 30
- `battery.recharge_rate`: 0.167
- `battery.drain_rate`: 0.2
- `battery.min_accept_task`: 35
- All service and world parameters unchanged

## EXPECTED OUTCOMES

### Scenario A (arrival_rate=3, low load)
- **Queue Size**: Near 0 (tasks assigned immediately)
- **Agent Utilization**: LOW (agents frequently idle)
- **System Wealth Growth**: SLOW (limited opportunities)
- **Task Completion**: ALL tasks completed with minimal delay
- **Rationale**: Supply exceeds demand - agents have excess capacity

### Scenario B (arrival_rate=8, medium load)
- **Queue Size**: FLUCTUATES but manageable (0-10 range)
- **Agent Utilization**: HIGH (agents stay busy)
- **System Wealth Growth**: OPTIMAL (good balance)
- **Task Completion**: EFFICIENT processing
- **Rationale**: Balanced load - system operating near capacity

### Scenario C (arrival_rate=15, high load)
- **Queue Size**: GROWS OVER TIME (accumulation pattern)
- **Agent Utilization**: MAXIMUM (always busy)
- **System Wealth Growth**: HIGH initially but queue builds
- **Task Completion**: HIGH rate but can't keep up with arrival
- **Rationale**: Demand exceeds supply - system saturation

### Key Comparison
- Queue size should increase dramatically from A → C
- System wealth growth rate highest in B (optimal efficiency)
- Task completion rate should plateau in C (capacity limit reached)
- Agent idle time should decrease from A → C

## KEY GRAPHS - EXPECTED OUTCOMES

| Graph | Scenario A (rate=3) | Scenario B (rate=8) | Scenario C (rate=15) |
|-------|---------------------|----------------------|-----------------------|
| **Queue Size Over Time** | Near 0, flat | Fluctuates 0–10 | Grows over time (accumulation) |
| **Agent Status Distribution** | High % idle, low % exec | Balanced idle/exec | Low % idle, high % exec |
| **Wealth Growth Rate** | Low, slow growth | Optimal, steady growth | High initially then levels as queue builds |
| **Task Status** (avg time per state) | Low time unassigned, normal in progress | Moderate unassigned, normal in progress | High time unassigned, normal in progress |

**Rationale**: Low load (A) = tasks assigned quickly → short queue time. High load (C) = backlog → long time in queue. In-progress time depends on work_time, not load. Completed is terminal (0 steps in state).

## VALIDATION CRITERIA
✓ Queue remains near 0 in Scenario A  
✓ Queue shows growth trend in Scenario C  
✓ Agent utilization increases from A → C  
✓ System can handle medium load efficiently  
✓ Clear saturation pattern visible in high load  

## ACTUAL RESULTS

### Scenario A (arrival_rate=3)
- Final Gini: _[to be filled]_
- Final System Wealth: _[to be filled]_
- Total Tasks Completed: _[to be filled]_
- Avg Queue Size: _[to be filled]_
- Max Queue Size: _[to be filled]_
- Avg Critical Battery Rate: _[to be filled]_
- % Time Agents Idle: _[to be filled]_
- Status: ⬜ Pass / ⬜ Fail

### Scenario B (arrival_rate=8)
- Final Gini: _[to be filled]_
- Final System Wealth: _[to be filled]_
- Total Tasks Completed: _[to be filled]_
- Avg Queue Size: _[to be filled]_
- Max Queue Size: _[to be filled]_
- Avg Critical Battery Rate: _[to be filled]_
- % Time Agents Idle: _[to be filled]_
- Status: ⬜ Pass / ⬜ Fail

### Scenario C (arrival_rate=15)
- Final Gini: _[to be filled]_
- Final System Wealth: _[to be filled]_
- Total Tasks Completed: _[to be filled]_
- Avg Queue Size: _[to be filled]_
- Max Queue Size: _[to be filled]_
- Avg Critical Battery Rate: _[to be filled]_
- % Time Agents Idle: _[to be filled]_
- Status: ⬜ Pass / ⬜ Fail

## CONCLUSION
_[To be filled after running experiments]_

### Did results match expectations?
- [ ] Queue size increases from A → C as expected
- [ ] Agent utilization shows clear progression
- [ ] System saturates at high load
- [ ] Task generation follows Poisson distribution correctly

### Issues Found
_[Document any unexpected behavior or bugs discovered]_

### Recommendations
_[Optimal task arrival rate for this agent configuration]_

## KEY GRAPHS FOR ANALYSIS (4 MOST IMPORTANT)

### Primary Graphs
1. **`queue_size_over_time.png`** ⭐⭐⭐  
   - Unassigned tasks waiting in queue.  
   - Expected: near 0 in A, moderate in B, growing in C.

2. **`agent_status_distribution.png`** ⭐⭐⭐  
   - % of agents idle / busy / exec over time.  
   - Expected: more idle in A, balanced in B, mostly exec in C.

3. **`wealth_growth_rate.png`** ⭐⭐  
   - System wealth growth per step (smoothed).  
   - Expected: low in A, optimal in B, high then plateau in C.

4. **`task_status.png`** ⭐⭐⭐ (new)  
   - Average time (steps) each task spends in: unassigned, in progress, completed (0).  
   - Expected: short unassigned in A, long unassigned in C; in-progress similar across scenarios.  
   - Requires `task_data.csv` (generated when running simulation).

### How to generate task_status.png only (after re-running simulation)
```bash
python scripts/plot_task_status.py experiments/exp-02-taskload
```
Or for one scenario: `python scripts/plot_task_status.py experiments/exp-02-taskload/scenario-a`

### Additional Graphs (auto-generated)
- `gini_over_time.png`, `system_wealth_over_time.png`, `tasks_completed_over_time.png`
- `critical_battery_over_time.png`, `robot_vs_human_wealth.png`, `avg_battery_over_time.png`
- `wealth_trajectories.png`, `wealth_distribution.png`, `wealth_boxplot.png`
- `task_completion_rate.png`

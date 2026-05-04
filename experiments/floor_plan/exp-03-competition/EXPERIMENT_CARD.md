# EXPERIMENT 03: AGENT COMPETITION DYNAMICS

## EXPERIMENT METADATA
- **Experiment ID**: EXP-03-COMPETITION
- **Date Created**: 2026-02-04
- **Objective**: Validate economic competition between humans and robots under different population ratios

## OBJECTIVES
- **Primary**: Test if agent type differences (battery constraints, service offerings, completion rates) create realistic competitive dynamics
- **Secondary**: Observe how population ratios affect wealth distribution and task allocation patterns

## VARIABLE PARAMETER
- **Parameter**: Robot-to-human population ratio
- **Scenario A**: 6 humans, 2 robots (human-dominated, 3:1 ratio)
- **Scenario B**: 4 humans, 4 robots (balanced, 1:1 ratio)
- **Scenario C**: 2 humans, 6 robots (robot-dominated, 1:3 ratio)

## FIXED PARAMETERS
- `simulation.duration`: 1000 steps
- `simulation.seed`: 42
- `tasks.arrival_rate`: 10 tasks/hour (sufficient for all agents)
- `battery.recharge_trigger`: 30
- `battery.recharge_rate`: 0.167
- `battery.drain_rate`: 0.2
- `battery.min_accept_task`: 35
- `assignment_policy`: random
- All service and world parameters unchanged

## EXPECTED OUTCOMES

### Scenario A (6 humans, 2 robots - human-dominated)
- **Human Wealth**: HIGH (more opportunities for humans)
- **Robot Wealth**: LOWER (fewer robots, but constrained by battery)
- **Gini Coefficient**: LOW (homogeneous humans dominate)
- **Critical Battery Rate**: LOW (only 2 robots)
- **Task Distribution**: 75% to humans, 25% to robots
- **Rationale**: Humans dominate economy, minimal battery constraints

### Scenario B (4 humans, 4 robots - balanced)
- **Human Wealth**: MODERATE-HIGH
- **Robot Wealth**: MODERATE
- **Gini Coefficient**: MODERATE (mixed population)
- **Critical Battery Rate**: MODERATE
- **Task Distribution**: ~50-50 split (accounting for robot downtime)
- **Rationale**: Equal competition but robots handicapped by battery

### Scenario C (2 humans, 6 robots - robot-dominated)
- **Human Wealth**: HIGHER per capita (no battery constraint)
- **Robot Wealth**: VARIABLE (battery creates inequality)
- **Gini Coefficient**: HIGH (robots vary by battery state)
- **Critical Battery Rate**: HIGH (more robots competing for charging)
- **Task Distribution**: Humans capture more tasks per agent
- **Rationale**: Robot competition intense, battery becomes major bottleneck

### Key Comparison
- Per-capita human wealth should be highest in C (scarce humans)
- Gini should increase from A → C (robot battery variability)
- Battery charging tasks increase from A → C (more robots)
- Robots in C may have unequal outcomes based on charging access

## VALIDATION CRITERIA
✓ Humans maintain wealth advantage across all scenarios  
✓ Gini increases from A → C due to robot heterogeneity  
✓ Critical battery rate correlates with robot population  
✓ Task allocation reflects both population and constraints  
✓ Robot wealth variance increases with robot population  

## ACTUAL RESULTS

### Scenario A (6H, 2R - human-dominated)
- Final Gini: _[to be filled]_
- Final System Wealth: _[to be filled]_
- Total Tasks Completed: _[to be filled]_
- Avg Queue Size: _[to be filled]_
- Avg Critical Battery Rate: _[to be filled]_
- Robot Final Wealth (mean): _[to be filled]_
- Human Final Wealth (mean): _[to be filled]_
- Robot Wealth Std Dev: _[to be filled]_
- Human Wealth Std Dev: _[to be filled]_
- Status: ⬜ Pass / ⬜ Fail

### Scenario B (4H, 4R - balanced)
- Final Gini: _[to be filled]_
- Final System Wealth: _[to be filled]_
- Total Tasks Completed: _[to be filled]_
- Avg Queue Size: _[to be filled]_
- Avg Critical Battery Rate: _[to be filled]_
- Robot Final Wealth (mean): _[to be filled]_
- Human Final Wealth (mean): _[to be filled]_
- Robot Wealth Std Dev: _[to be filled]_
- Human Wealth Std Dev: _[to be filled]_
- Status: ⬜ Pass / ⬜ Fail

### Scenario C (2H, 6R - robot-dominated)
- Final Gini: _[to be filled]_
- Final System Wealth: _[to be filled]_
- Total Tasks Completed: _[to be filled]_
- Avg Queue Size: _[to be filled]_
- Avg Critical Battery Rate: _[to be filled]_
- Robot Final Wealth (mean): _[to be filled]_
- Human Final Wealth (mean): _[to be filled]_
- Robot Wealth Std Dev: _[to be filled]_
- Human Wealth Std Dev: _[to be filled]_
- Status: ⬜ Pass / ⬜ Fail

## CONCLUSION
_[To be filled after running experiments]_

### Did results match expectations?
- [ ] Humans show consistent wealth advantage
- [ ] Gini increases with robot proportion
- [ ] Battery constraints create visible disadvantages
- [ ] Task allocation reflects competitive dynamics

### Issues Found
_[Document any unexpected behavior or bugs discovered]_

### Recommendations
_[Insights about optimal agent ratios or policy adjustments]_

## GRAPHS GENERATED
- `gini_over_time.png` - Wealth inequality evolution (KEY METRIC)
- `system_wealth_over_time.png` - Total system wealth
- `tasks_completed_over_time.png` - Cumulative task completion
- `queue_size_over_time.png` - Task queue dynamics
- `critical_battery_over_time.png` - Critical battery rate
- `robot_vs_human_wealth.png` - Final wealth comparison (KEY METRIC)
- `avg_battery_over_time.png` - Average battery levels
- `agent_status_distribution.png` - Agent state distribution
- `wealth_trajectories.png` - Individual agent wealth paths (KEY METRIC)
- `wealth_distribution.png` - Final wealth histogram (KEY METRIC)
- `wealth_boxplot.png` - Wealth distribution comparison (KEY METRIC)
- `task_completion_rate.png` - Task completion rate
- `wealth_growth_rate.png` - System wealth growth

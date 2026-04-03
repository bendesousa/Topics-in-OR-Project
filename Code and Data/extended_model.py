from chill_model import chill_model
from ga import run_ga
import gurobipy as gb
import pandas as pd

#Running base model for initial guess
model, x, y, q, Rules, T, D, data = chill_model()


if model.SolCount > 0:
    base_obj = model.ObjVal
    base_gap = model.MIPGap

    base_solution = [
        (i, m, t, d)
        for (i, m, t, d), var in x.items()
        if var.X > 0.5
    ]
    base_df = pd.DataFrame(base_solution, columns=["Module", "Event", "Time", "Day"])
    base_df.sort_values(["Day", "Time"]).to_csv("base_timetable.csv", index=False)

    base_rulebreaks = [
        (r, k, var.X)
        for (r, k), var in q.items()
        if var.X > 0.5
    ]
    base_rulebreaks.extend(("Clash", k, var.X) for k, var in y.items() if var.X > 0.5)
    base_rules_df = pd.DataFrame(base_rulebreaks, columns=["Rule", "CourseID", "Num_Violations"])
    base_rules_df.sort_values(["CourseID", "Num_Violations"]).to_csv("base_rulebreakers.csv", index=False)

    print(f"Base MIP objective: {base_obj:.2f}, gap: {base_gap:.2%}")

I = data["I"]
M = data["M"]
demand = data["demand"]

rows = []
for (i, m), req in demand.items():
    rows.append({"Module Name": i, "Event Type": m, "Weekly Requirement": req})

event_df = pd.DataFrame(rows)

#Running GA Alg1
# print("Running GA Alg1...")
feasible_population, events = run_ga(
    event_df, T, D,
    mode="alg1",
    pop_size=20,
    generations=50
)

# #Running GA Alg2
# print("Running GA Alg2...")
best_alg2_solution, _ = run_ga(
    event_df, T, D,
    mode="alg2",
    pop_size=20,
    generations=50,
    initial_population=feasible_population
)

#Rerunning base model with GA solution as initial guess
print("Rerunning base model with GA solution as initial guess...")
# Assign GA solution into x as initial values

for idx, (t, d) in enumerate(best_alg2_solution):
    i, m = events[idx]
    if (i, m, t, d) in x:
        x[i, m, t, d].Start = 1.0

model.Params.MIPGap = 0.05
model.Params.TimeLimit = 35473

try:
    model.optimize()
except KeyboardInterrupt:
    pass


# Results
if model.SolCount > 0:
    solution = [
        (i, m, t, d)
        for (i, m, t, d), var in x.items()
        if var.X > 0.5
    ]

    sol_df = pd.DataFrame(solution, columns=["Module", "Event", "Time", "Day"])
    sol_df = sol_df.sort_values(["Day", "Time"])
    sol_df.to_csv("extended_timetable.csv", index=False)
    # this is the rule violations
    rulebreaks = [
            (r, k, var.X)
            for (r, k), var in q.items()
            if var.X > 0.5
        ]
    # including clashes
    rulebreaks.extend(
        ("Clash", k, var.X) 
        for k, var in y.items()
        if var.X > 0.5
        )
    rules_df = pd.DataFrame(rulebreaks, columns =["Rule", "CourseID", "Num_Violations"])
    rules_df = rules_df.sort_values(["CourseID", "Num_Violations"])
    # write to csv
    rules_df.to_csv("ext_rulebreakers.csv", index=False)

    print(f"Base MIP:      obj={base_obj:.2f}, gap={base_gap:.2%}")
    print(f"GA-seeded MIP: obj={model.ObjVal:.2f}, gap={model.MIPGap:.2%}")

else:
    print("No solution found, status:", model.status)


from chill_model import chill_model
from ga import run_ga
import gurobipy as gb
import pandas as pd

#Running base model for initial guess
model, x, y, q, Rules, T, D, data = chill_model()

I = data["I"]
M = data["M"]
demand = data["demand"]

rows = []
for (i, m), req in demand.items():
    rows.append({"Module Name": i, "Event Type": m, "Weekly Requirement": req})

event_df = pd.DataFrame(rows)

#Running GA Alg1
# print("Running GA Alg1...")
# feasible_population, events = run_ga(
#     event_df,
#     T,
#     D,
#     mode="alg1"
# )

# #Running GA Alg2
# print("Running GA Alg2...")
# best_alg2_solution, _ = run_ga(
#     event_df,
#     T,
#     D,
#     mode="alg2",
#     initial_population=feasible_population
# )

feasible_population, events = run_ga(
    event_df, T, D,
    mode="alg1",
    pop_size=10,
    generations=20
)

best_alg2_solution, _ = run_ga(
    event_df, T, D,
    mode="alg2",
    pop_size=10,
    generations=20,
    initial_population=feasible_population
)

#Rerunning base model with GA solution as initial guess
print("Rerunning base model with GA solution as initial guess...")
# Assign GA solution into x as initial values
# for idx, (t, d) in enumerate(best_alg2_solution):
#     i, m = events[idx]

#     for key, var in x.items():
#         if key == (i, m, t, d):
#             var.Start = 1.0
#         else:
#             # optional: initialise others to 0
#             pass

for idx, (t, d) in enumerate(best_alg2_solution):
    i, m = events[idx]
    if (i, m, t, d) in x:
        x[i, m, t, d].Start = 1.0

model.optimize()

#Results
# if model.status == gb.GRB.OPTIMAL:

#     solution = [
#         (i, m, t, d)
#         for (i, m, t, d), var in x.items()
#         if var.X > 0.5
#     ]

#     sol_df = pd.DataFrame(solution, columns=["Module", "Event", "Time", "Day"])
#     sol_df = sol_df.sort_values(["Day", "Time"])

#     sol_df.to_csv("extended_timetable.csv", index=False)

# else:
#     print("Model status:", model.status)

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

else:
    print("No solution found, status:", model.status)
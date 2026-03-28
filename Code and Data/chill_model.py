import os


def chill_model():
    import gurobipy as gb
    import pickle

    import os
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    with open(os.path.join(BASE_DIR, "model_inputs.pkl"), "rb") as f:
        data = pickle.load(f)
    
    K = data["K"]
    I = data["I"]
    M = data["M"]
    A = data["A"]
    B = data["B"]
    A_m = data["A_m"]
    B_m = data["B_m"]
    demand = data["demand"]
    enrolled = data["enrolled"]
    C = data["C"]
    R_c = data["R_c"]
    
    T = ["09:00","10:00","11:00","12:00","13:00","14:00","15:00","16:00","17:00"]
    D = ["Monday", "Tuesday", "Wednesday My Dudes", "Out of Touch Thursday", "It's Friday Thennnnn"]
    Rules = ["Lunch", "After 17h", "Friday Afternoon", "6hrs per day"]
    #Weighting
    W = 10
    
    #Initialising the model
    model = gb.Model('timetable')
    
    #Decision Variable(s)
    #Whether course i event m is in slot or not
    x = model.addVars([(i, m, t, d) for i in I for m in M for t in T for d in D], vtype=gb.GRB.BINARY, name='x')
    #Overlap
    y = model.addVars(K, vtype=gb.GRB.INTEGER, lb=0, ub = gb.GRB.INFINITY, name='y')
    #Lunch break
    b = model.addVars(D, K, lb=0, name='b')
    # questions violations
    q = model.addVars(Rules, K, vtype = gb.GRB.INTEGER, lb = 0, ub = gb.GRB.INFINITY, name="violations")
    # daily limit violations
    l = model.addVars(D, K, vtype = gb.GRB.INTEGER, lb = 0, ub = gb.GRB.INFINITY, name="daily_limit_violated")
    
    #Constraints
    #No overlapping compulsory courses
    model.addConstrs(gb.quicksum(x[i,"Lecture",t,d] for i in A[k]) <= 1 for k in K for t in T for d in D)
    
    #Required hours per week for each event
    model.addConstrs(gb.quicksum(x[i,m,t,d] for t in T for d in D)
                                == demand[i,m] for m in M for i in I if (i,m) in demand)
    
    #Optional courses cannot clash with compulsory ones
    # =============================================================================
    # model.addConstrs(gb.quicksum(100 * x[i,"Lecture",t,d] + x[j,"Lecture",t,d]
    #                              for i in A[k] for j in B[k]) <= 100
    #                  for k in K for t in T for d in D)
    # =============================================================================
                    
    #Overlap constraint
    model.addConstrs(gb.quicksum(x[i,m,t,d] for i in A[k] | B[k] for m in M) <= y[k] for k in K for t in T for d in D)
    
    #No teaching after 5pm
    model.addConstrs(gb.quicksum(x[i,m,"17:00",d] for m in M for i in (A_m.get((k,m), set()) |B_m.get((k,m), set())) for d in D) <= q["After 17h", k] for k in K)
    
    #No teaching on Friday after 2pm
    model.addConstrs(gb.quicksum(x[i,m,t,"It's Friday Thennnnn"] for m in M for i in (A_m.get((k,m), set()) |B_m.get((k,m), set())) for t in ["14:00", "15:00", "16:00", "17:00"]) <= q["Friday Afternoon", k] for k in K)
    
    #Core teaching being delivered without clashes
    # =============================================================================
    # model.addConstrs(gb.quicksum(
    #         x[i,"Lecture",t,d] for i in (A_m.get((k,"Lecture"), set()) | B_m.get((k,"Lecture"), set()))
    #     ) <= 1
    #     for k in K for t in T for d in D)
    # =============================================================================
                
    #Lunchbreak constraint
    model.addConstrs(gb.quicksum(x[i,m,"12:00",d] + x[i,m,"13:00",d] for i in A[k] | B[k]) - 1
                                <= b[d,k] for k in K for m in M if (k,m) in A[k] | B[k] for d in D)
    
    model.addConstrs(gb.quicksum(b[d,k] for d in D) <= q["Lunch", k] for k in K)
    
    # We have a room big enough for all x
    model.addConstrs(
        gb.quicksum(x[i, m, t, d] for m in M for i in I if (i,m) in enrolled and enrolled[i, m] <= c) 
        <= gb.quicksum(R_c[c_prime] for c_prime in C if c_prime <= c) 
        for c in C for t in T for d in D
        
    )
    # Average room_c utilization <= .75
    #model.addConstrs(
    #    gb.quicksum(x[i, m, t, d] for t in T for d in D for m in M for i in I if (i,m) in enrolled and enrolled[i, m] <= c)
    #    <= .75 * (45 * gb.quicksum(R_c[c_prime] for c_prime in C if c_prime <= c))
    #    for c in C
    #)
    # Average room_c utilization >= .5
    #model.addConstrs(
    #    gb.quicksum(x[i, m, t, d] for t in T for d in D for k in K for m in M for i in A_m[k, m] | B_m[k, m] if enrolled[i, m] <= c)
    #    >= .5 * (45 * gb.quicksum(R_c[c_prime] for c_prime in C if c_prime <= c))
    #    for c in C
    #)
    #Optional Constraints
    #Ensure multi-slot events fill consecutive slots
    # for k in K:
    #     for m in M:
    #         for i in A_m[k,m] | B_m[k,m]:
    #             l = demand[i, m]
    #             if l >= 2:
    #                 for d in D:
    #                     #avoiding overlap across days
    #                     for t in range(1+l, len(T)+1-l):
    #                         model.addConstr(l * x[i,m,T[t],d] <=
    #                                         gb.quicksum(x[i,m, T[t-r],d] + x[i,m,T[t+r],d] 
    #                                                     for r in range(1, l+1)))
    
    #Limit on daily teaching
    model.addConstrs(gb.quicksum(x[i,m,t,d] for m in M for i in (A_m.get((k,m), set()) |B_m.get((k,m), set())) for t in T) <= 6 + l[d, k] for d in D for k in K)
    model.addConstrs(gb.quicksum(l[d, k] for d in D) <= q["6hrs per day", k] for k in K)
    
    #Objective Function
    model.setObjective(gb.quicksum(W * y[k] + gb.quicksum(q[r, k] for r in Rules) for k in K)
                       ,gb.GRB.MINIMIZE)
    
    # current time limit is 10 minutes, can change obvi, similar models take a day on better hardware
    model.Params.TimeLimit = 600
    
    model.optimize()
    
    return model, x, y, q, Rules, T, D, data

# if __name__ == "__main__":
    
#     model, x, y, q, Rules, T, D, data = chill_model()
    
#     import gurobi as gb
#     import pandas as pd
    
#     if model.status == gb.GRB.INFEASIBLE:
#         model.computeIIS()
#         model.write("model.ilp")
#         print("\nModel Infeasible: Check model.ilp for cause")
    
#     # if there is a solution get it
#     elif model.SolCount:
#         # this is the timetable
#         solution = [
#             (i, m, t, d)
#             for (i, m, t, d), var in x.items()
#             if var.X > 0.5
#         ]
        
#         sol_df = pd.DataFrame(solution, columns=["Module", "Event", "Time", "Day"])
#         sol_df = sol_df.sort_values(["Day", "Time"])
#         # write to csv
#         # sol_df.to_csv("uni_timetable.csv", index = False)
        
#         # this is the rule violations
#         rulebreaks = [
#                 (r, k, var.X)
#                 for (r, k), var in q.items()
#                 if var.X > 0.5
#             ]
#         # including clashes
#         rulebreaks.append(("Clash", k, var.X)
#                           for k, var in y.items()
#                           if var.X > 0.5)
#         rules_df = pd.DataFrame(rulebreaks, columns =["Rule", "CourseID", "Num_Violations"])
#         rules_df = rules_df.sort_values(["CourseID", "Num_Violations"])
#         # write to csv
        # rules_df.to_csv("uni_rulebreakers.csv", index=False)
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 23 11:27:05 2026

@author: nolanbearw
"""
import gurobipy as gb
import pandas as pd
import pickle

with open("model_inputs.pkl", "rb") as f:
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

#Weighting
W = 1

#Initialising the model
model = gb.Model('timetable')

#Decision Variable(s)
#Whether course i event m is in slot or not
x = model.addVars([(i, m, t, d) for i in I for m in M for t in T for d in D], vtype=gb.GRB.BINARY, name='x')
#Overlap
y = model.addVars(K, vtype=gb.GRB.INTEGER, lb=0, name='y')
#Lunch break
b = model.addVars(D, K, lb=0, name='b')

#Constraints
#No overlapping compulsory courses

model.addConstrs(gb.quicksum(x[i,m,t,d] for i in A[k]) <= 1 for k in K for m in M for t in T for d in D)

#Required hours per week for each event
model.addConstrs(gb.quicksum(x[i,m,t,d] for t in T for d in D)
                            == demand[i,m] for m in M for i in I if (i,m) in demand)

#Optional courses cannot clash with compulsory ones 
model.addConstrs(gb.quicksum(x[i,m,t,d] + x[j,m,t,d] for m in M) <= 1 for k in K for t in T for d in D for i in A[k] for j in B[k])
                
#Overlap constraint
model.addConstrs(gb.quicksum(x[i,m,t,d] for i in B[k]) <= y[k] for k in K for m in M for t in T for d in D)

#No teaching after 5pm
model.addConstrs(x[i,m,"17:00",d] == 0 for i in I for m in M for d in D)

#No teaching on Friday after 2pm
model.addConstrs(x[i,m,t,"It's Friday Thennnnn"] == 0 for m in M for t in ["14:00", "15:00", "16:00", "17:00"] for i in I)

#Core teaching being delivered without clashes
model.addConstrs(gb.quicksum(
        x[i,"Lecture",t,d] for i in (A_m.get((k,"Lecture"), set()) |B_m.get((k,"Lecture"), set()))
    ) <= 1
    for k in K for t in T for d in D)
            
#Lunchbreak constraint
model.addConstrs(gb.quicksum(x[i,m,"12:00",d] + x[i,m,"13:00",d] for i in A[k] | B[k]) - 1
                            <= b[d,k] for k in K for m in M if (k,m) in A[k] | B[k] for d in D)

# We have a room big enough for all x
model.addConstrs(
    gb.quicksum(x[i, m, t, d] for m in M for i in I if (i,m) in enrolled and enrolled[i, m] <= c) 
    <= gb.quicksum(R_c[c_prime] for c_prime in C if c_prime <= c) 
    for c in C for t in T for d in D
    
)
# Average room_c utilization <= .75
model.addConstrs(
    gb.quicksum(x[i, m, t, d] for t in T for d in D for m in M for i in I if (i,m) in enrolled and enrolled[i, m] <= c)
    <= .75 * (45 * gb.quicksum(R_c[c_prime] for c_prime in C if c_prime <= c))
    for c in C
)
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
model.addConstrs(gb.quicksum(x[i,m,t,d] for i in (A_m.get((k,m), set()) |B_m.get((k,m), set())) for t in T for m in M) <= 6 for k in K for m in M for d in D)

#Objectivve Function
model.setObjective(gb.quicksum(y[k] for k in K)
                   + W * gb.quicksum(b[d,k] for d in D for k in K)
                   ,gb.GRB.MINIMIZE)

model.Params.TimeLimit = 60

model.optimize()

if model.status == gb.GRB.INFEASIBLE:
    model.computeIIS()
    model.write("model.ilp")
    
elif model.status == gb.GRB.OPTIMAL:
    solution = [
        (i, m, t, d)
        for (i, m, t, d), var in x.items()
        if var.X > 0.5
    ]
    
    sol_df = pd.DataFrame(solution, columns=["Module", "Event", "Time", "Day"])
    sol_df = sol_df.sort_values(["Day", "Time"])
    
    sol_df.to_csv("uni_timetable.csv", index = False)
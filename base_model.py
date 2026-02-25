import numpy as np
import gurobipy as gb

#Sets 
#Programmes/ Years
K = []
#Courses/Events
I = []
#Capacities
C = []
#Time slots
T = list(range(1,10))
#Days
D = list(range(1,6))
#Event types 
M = []
#Compulsory courses
A = {k: set([]) for k in K}
#Optional courses
B = {k: set([]) for k in K}
#Compulsory course events
A_m = {(k,m): set([]) for k in K for m in M}
#Optional course events
B_m = {(k,m): set([]) for k in K for m in M}

#Parameters
#Weekly time requirement for each event     
demand = {(i,m): () for i in I for m in M}
#Weighting
W = 1
#Event duration
duration = {i: () for i in I}
#Room counts w/ capacity
R_c = {c: 0 for c in C}
# sizes of i m
enrolled = {(i, m): 0 for i in I for m in M}
# eligible c's for i, m
comp = {(i, m): {c for c in C if enrolled(i, m) <= c} for i in I for m in M}

#Initialising the model
model = gb.Model('timetable')

#Decision Variable(s)
#Whether course i event m is in slot or not with capacity c
x = model.addVars([(i, m, t, d, c) for i in I for m in M for t in T for d in D for c in comp[i, m]], vtype=gb.GRB.BINARY, name='x')
#Overlap
y = model.addVars(K, vtype=gb.GRB.INTEGER, lb=0, name='y')
#Lunch break
b = model.addVars(D, K, lb=0, name='b')

#Constraints
#No overlapping compulsory courses
for k in K:
    for t in T:
        for d in D:
            model.addConstr(gb.quicksum(x[i,t,d] for i in A[k]) <= 1)

#Required hours per week for each event
for k in K:
    for m in M:
        for i in A_m[k,m] | B_m[k,m]:
            model.addConstr(gb.quicksum(x[i,t,d] for t in T for d in D)
                            == demand[i,m])

#Optional courses cannot clash with compulsory ones 
for k in K:
    for t in T:
        for d in D:
            for i in A[k]:
                for j in B[k]:
                    model.addConstr(x[i,t,d] + x[j,t,d] <= 1)
                
#Overlap constraint
for k in K:
    for t in T:
        for d in D:
            model.addConstr(gb.quicksum(x[i,t,d] for i in B[k]) <= y[k])

#No teaching after 5pm
for i in I:
    for d in  D:
        model.addConstr(x[i,9,d] == 0)

#No teaching on Friday after 2pm
for i in I:
    for t in [4,5,6,7,8,9]:
        model.addConstr(x[i,t,5] == 0)

#Core teaching being delivered without clashes
#assume m=1 is lectures
for k in K:
    for t in T:
        for d in D:
            model.addConstr(gb.quicksum(x[i,t,d] for i in A_m[k,1] | B_m[k,1])
                            <= 1)
            
#Lunchbreak constraint
for k in K:
    for d in D:
        model.addConstr(gb.quicksum(x[i,4,d] + x[i,5,d] for i in A[k] | B[K]) - 1
                        <= b[d,k])

# We have a room big enough for all x
# model.addConstrs(gb.quicksum(x[i, m, t, d, c] for i in I for m in M for c in comp[i,m]) <= R_c[c] for c in C for t in T for d in D )
# Average room utilization <= .75
# model.addConstrs(quicksum(x[i, m, t, d, c] for i in I for m in M for t in T for d in D for c in comp[i,m])/(R_c[c] * 45) <= .75 for c in C)

#Optional Constraints
#Ensure multi-slot events fill consecutive slots
# for i in I:
#     l = duration[i]
#     if l >= 2:
#         for d in D:
#             #avoiding overlap across days
#             for t in range(1+l, len(T)+1-l):
#                 model.addConstr(l * x[i,t,d] <=
#                                 gb.quicksum(x[i,t-r,d] + x[i,t+r,d] 
#                                             for r in range(1, l+1)))

# #Limit on daily teaching
# for k in K:
#     for d in D:
#         model.addConstr(gb.quicksum(x[i,t,d] for i in A[k] | B[k] for t in T) <= 6)

#Objectivve Function
model.setObjective(gb.quicksum(y[k] for k in K)
                   + W * gb.quicksum(b[d,k] for d in D for k in K),
                   gb.GRB.MINIMIZE)

model.optimize()
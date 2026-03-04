import numpy as np
import pandas as pd
import gurobipy as gb

vet = pd.read_excel("Cleaned Vet School Data.xlsx")
room = pd.read_excel("Rooms and Room Types.xlsx", sheet_name="Room")
room = room[room["Campus"] == "Easter Bush"]
vet = vet.drop_duplicates(subset=["Event Name", "Duration (minutes)"])
vet = vet[vet["Semester"] == "Semester 1"]
vet["Year"] = (vet["Event Name"].str.strip().str.split().str[0])
#Sets 
#Programmes/ Years
K = vet["Year"].unique()
#Courses/Events
I = vet["Event Name"].unique()
#Capacities
C = room["Capacity"].unique()
#Time slots
T = list(range(1,10))
#Days
D = list(range(1,6))
#Event types 
M = vet["Event Type"].unique()
#Compulsory courses
A = {k: set(
        vet.loc[
            (vet["Year"] == k) & (vet["WholeClass"] == True),
            "Event Name"
        ]
    ) for k in K} # where vet["whole class"] = True
#Optional courses
B = {k: set(
        vet.loc[
            (vet["Year"] == k) & (vet["WholeClass"] == False),
            "Event Name"
        ]
    ) for k in K} # where vet["whole class"] = False
#Compulsory course events
A_m = {(k,m): set(
        vet.loc[
            (vet["Year"] == k) &
            (vet["Event Type"] == m) &
            (vet["WholeClass"] == True),
            "Event Name"
        ]
    ) for k in K for m in M}
#Optional course events
B_m = {(k,m): set(
        vet.loc[
            (vet["Year"] == k) &
            (vet["Event Type"] == m) &
            (vet["WholeClass"] == False),
            "Event Name"
        ]
    ) for k in K for m in M}

#Parameters
#Weekly time requirement for each event     
demand = {(row["Event Name"], row["Event Type"]): row["Duration (minutes)"]
    for _, row in vet.iterrows()} # duration
#Weighting
W = 1
#Event duration
duration = (vet.groupby("Event Name")["Duration (minutes)"]
       .sum()
       .to_dict()) # sum durations where week[i_0] = week[i_1]
#Room counts w/ capacity
R_c = room.groupby("Capacity").size().to_dict()
# sizes of i m
enrolled = {
    (row["Event Name"], row["Event Type"]): row["Event Size"]
    for _, row in vet.iterrows()
}
#Initialising the model
model = gb.Model('timetable')

#Decision Variable(s)
#Whether course i event m is in slot or not with capacity c
x = model.addVars([(i, t, d) for i in I for t in T for d in D], vtype=gb.GRB.BINARY, name='x')
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
#assume m=0 is lectures
for k in K:
    for t in T:
        for d in D:
            model.addConstr(gb.quicksum(x[i,t,d] for i in A_m[k,"Lecture"] | B_m[k,"Lecture"])
                            <= 1)
            
#Lunchbreak constraint
for k in K:
    for d in D:
        model.addConstr(gb.quicksum(x[i,4,d] + x[i,5,d] for i in A[k] | B[k]) - 1
                        <= b[d,k])

# We have a room big enough for all x
model.addConstrs(
    gb.quicksum(enrolled[i, m] * x[i, t, d] for k in K for m in M for i in A_m[k, m] | B_m[k, m] if enrolled[i, m] <= c) 
    <= gb.quicksum(c_prime * R_c[c_prime] for c_prime in C if c_prime <= c) 
    for c in C for t in T for d in D
    
)
# Average room_c utilization <= .75
model.addConstrs(
    gb.quicksum(enrolled[i, m] * x[i, t, d] for t in T for d in D for k in K for m in M for i in A_m[k, m] | B_m[k, m] if enrolled[i, m] <= c)
    <= .75 * (45 * gb.quicksum(c_prime * R_c[c_prime] for c_prime in C if c_prime <= c))
    for c in C
)
# Average room_c utilization >= .5
model.addConstrs(
    gb.quicksum(enrolled[i, m] * x[i, t, d] for t in T for d in D for k in K for m in M for i in A_m[k, m] | B_m[k, m] if enrolled[i, m] <= c)
    >= .5 * (45 * gb.quicksum(c_prime * R_c[c_prime] for c_prime in C if c_prime <= c))
    for c in C
)
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
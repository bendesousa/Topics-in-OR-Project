def base_model():

    import numpy as np
    import pandas as pd
    import gurobipy as gb
    import math

    vet = pd.read_csv("Processed_Vet_School_Data.csv")
    room = pd.read_excel("Rooms and Room Types.xlsx", sheet_name="Room")
    room = room[room["Campus"] == "Easter Bush"]
    vet = (
        vet
        .loc[vet["Semester"] == "Semester 1"]
        .loc[vet["Event Type"].isin(["Lecture", "Practical", "Tutorial", "Workshop"])]
        .copy()
    )

    programs_and_reqs = pd.read_excel("Programme-Course.xlsx")
    programs_and_reqs = programs_and_reqs.rename(columns={"ModuleId": "Module Code"})

    set_df = vet.merge(programs_and_reqs, on="Module Code", how="inner")

    vet["Weeks"] = vet["Weeks"].astype(str).str.split(",")
    vet = vet.explode("Weeks")
    vet["Weeks"] = vet["Weeks"].astype(int)

    event_df = (
        vet.groupby(["Module Name", "Event Type", "Weeks"])["Duration (minutes)"]
        .sum()                                  # sum within each week
        .groupby(["Module Name", "Event Type"])
        .max()                                  # take max week
        .reset_index()
    )

    #Sets 
    #Programmes/ Years
    K = set_df["CourseId"].unique()
    #Courses/Events
    I = set_df["Module Name"].unique()
    #Capacities
    C = room["Capacity"].unique()
    #Time slots
    T = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"]
    #Days
    D = ["Monday", "Tuesday", "Wednesday My Dudes", "Out of Touch Thursday", "It's Friday Thennnnn"]
    #Event types 
    M = set_df["Event Type"].unique()
    #Compulsory courses
    A = {k: set(
            set_df.loc[
                (set_df["CourseId"] == k) & (set_df["Compulsory"] == True),
                "Module Name"
            ]
        )
        for k in K}
    #Optional courses
    B = {k: set(
            set_df.loc[
                (set_df["CourseId"] == k) & (set_df["Compulsory"] == False),
                "Module Name"
            ]
        )
        for k in K}
    #Optional courses
    #Compulsory course events (all of the events in vet associated with courses in A)
    A_m = {(k, m): set(
            set_df.loc[
                (set_df["CourseId"] == k) & (set_df["Compulsory"] == True) & (set_df["Event Type"] == m),
                "Module Name"
            ]
        )
        for k in K for m in M}
    #Optional courses
    #Optional course events (all of the events in vet associated with courses in B)
    B_m = {(k, m): set(
            set_df.loc[
                (set_df["CourseId"] == k) & (set_df["Compulsory"] == False) & (set_df["Event Type"] == m),
                "Module Name"
            ]
        )
        for k in K for m in M}

    #Parameters
    #Weekly time requirement for each event     
    demand = {(row["Module Name"], row["Event Type"]): math.ceil(row["Duration (minutes)"] / 60)
        for _, row in event_df.iterrows()} 
    #Weighting
    W = 1
    #Event duration
    #duration = (vet.groupby("Event Name")["Duration (minutes)"]
    #      .sum()
    #     .to_dict()) # sum durations where week[i_0] = week[i_1]
    #Room counts w/ capacity
    R_c = room.groupby("Capacity").size().to_dict()
    # sizes of i m
    enrolled = {
        (row["Module Name"], row["Event Type"]): row["Event Size"]
        for _, row in vet.iterrows()
    }
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
    for k in K:
        for m in M:
            for t in T:
                for d in D:
                    model.addConstr(gb.quicksum(x[i,m,t,d] for i in A[k]) <= 1)

    #Required hours per week for each event
    for k in K:
        for m in M:
            for i in A_m[k,m] | B_m[k,m]:
                model.addConstr(gb.quicksum(x[i,m,t,d] for t in T for d in D)
                                == demand[i,m])

    #Optional courses cannot clash with compulsory ones 
    for k in K:
        for t in T:
            for d in D:
                for m in M:
                    for i in A[k]:
                        for j in B[k]:
                            model.addConstr(x[i,m,t,d] + x[j,t,d] <= 1)
                    
    #Overlap constraint
    for k in K:
        for m in M:
            for t in T:
                for d in D:
                    model.addConstr(gb.quicksum(x[i,m,t,d] for i in B[k]) <= y[k])

    #No teaching after 5pm
    for i in I:
        for m in M:
            for d in D:
                model.addConstr(x[i,m,"17:00",d] == 0)

    #No teaching on Friday after 2pm
    #for i in I:
    #    for t in [4,5,6,7,8,9]:
    #        model.addConstr(x[i,t,5] == 0)

    #Core teaching being delivered without clashes
    #assume m=0 is lectures
    for k in K:
        for t in T:
            for d in D:
                model.addConstr(gb.quicksum(x[i,"Lecture",t,d] for i in A_m[k,"Lecture"] | B_m[k,"Lecture"])
                                <= 1)
                
    #Lunchbreak constraint
    for k in K:
        for m in M:
            for d in D:
                model.addConstr(gb.quicksum(x[i,m,"12:00",d] + x[i,m,"13:00",d] for i in A[k] | B[k]) - 1
                                <= b[d,k])

    # We have a room big enough for all x
    model.addConstrs(
        gb.quicksum(x[i, m, t, d] for k in K for m in M for i in A_m[k, m] | B_m[k, m] if enrolled[i, m] <= c) 
        <= gb.quicksum(R_c[c_prime] for c_prime in C if c_prime <= c) 
        for c in C for t in T for d in D
        
    )
    # Average room_c utilization <= .75
    #model.addConstrs(
    #    gb.quicksum(enrolled[i, m] * x[i, t, d] for t in T for d in D for k in K for m in M for i in A_m[k, m] | B_m[k, m] if enrolled[i, m] <= c)
    #    <= .75 * (45 * gb.quicksum(c_prime * R_c[c_prime] for c_prime in C if c_prime <= c))
    #    for c in C
    #)
    # Average room_c utilization >= .5
    #model.addConstrs(
    #    gb.quicksum(enrolled[i, m] * x[i, t, d] for t in T for d in D for k in K for m in M for i in A_m[k, m] | B_m[k, m] if enrolled[i, m] <= c)
    #    >= .5 * (45 * gb.quicksum(c_prime * R_c[c_prime] for c_prime in C if c_prime <= c))
    #    for c in C
    #)
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
                    + W * gb.quicksum(b[d,k] for d in D for k in K)
                    #+ W * gb.quicksum(x[i,9,d] for i in I for d in D)
                    ,gb.GRB.MINIMIZE)

    model.optimize()

    return model, x, event_df, T, D, demand

if __name__ == "__main__":

    model, x, event_df, T, D, demand = base_model()

    import pandas as pd
    import gurobipy as gb
    
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
        
        sol_df.to_csv("vet_timetable.csv", index = False)

    else:
            print("Model solved with status:", model.status)
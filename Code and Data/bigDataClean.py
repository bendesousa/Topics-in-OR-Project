#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 24 12:17:23 2026

@author: nolanbearw
"""
import pandas as pd
import numpy as np
import pickle

vet = pd.read_excel("2024-5 Event Module Room.xlsx", sheet_name = "2024-5 Event Module Room")

vet = (
    vet
    .loc[vet["Semester"] == "Semester 1"]
    .loc[vet["Event Type"].isin(["Lecture", "Practical", "Tutorial", "Workshop"])]
    .copy()
)


vet["Weeks"] = vet["Weeks"].astype(str).str.split(",")
vet = vet.explode("Weeks")
vet["Weeks"] = vet["Weeks"].astype(int)

vet = (
    vet.groupby(["Timeslot", "Module Code", "Event Type", "Weeks"], as_index=False)
       .agg({
           "Duration (minutes)": "max",
           "Event Size": "sum",
           # take the first non-null value for all the "don't care" cols
           **{col: "first" for col in vet.columns 
              if col not in ["Timeslot", "Module Code", "Event Type",
                             "Duration (minutes)", "Event Size"]}
       })
)

programs_and_reqs = pd.read_excel("Programme-Course.xlsx")
programs_and_reqs = programs_and_reqs.rename(columns={"ModuleId": "Module Code"})

set_df = vet.merge(programs_and_reqs, on="Module Code", how="inner")


event_df = (
    vet.groupby(["Module Name", "Event Type", "Weeks"])["Duration (minutes)"]
      .sum()                                  # sum within each week
      .groupby(["Module Name", "Event Type"])
      .max()                                  # take max week
      .reset_index()
)

event_df["Duration (minutes)"] = np.ceil(event_df["Duration (minutes)"] / 60).astype(int)
event_df = event_df.rename(columns={"Duration (minutes)": "Duration (hours)"})

room = pd.read_excel("Rooms and Room Types.xlsx", sheet_name="Room")

# -------------------------
# 1. Precompute small sets
# -------------------------
K = set_df["CourseId"].unique()
I = set_df["Module Name"].unique()
M = set_df["Event Type"].unique()
C = room["Capacity"].unique()
# capacities -> counts
R_c = room["Capacity"].value_counts().to_dict()

# -------------------------
# 2. Pre-index set_df by course
# -------------------------
by_course = set_df.groupby("CourseId")

# -------------------------
# 3. Build A and B FAST
# -------------------------
A = {
    k: set(grp.loc[grp["Compulsory"], "Module Name"])
    for k, grp in by_course
}

B = {
    k: set(grp.loc[~grp["Compulsory"], "Module Name"])
    for k, grp in by_course
}

# -------------------------
# 4. Build A_m and B_m FAST
# -------------------------
# Group once by (CourseId, Event Type)
ct_groups = set_df.groupby(["CourseId", "Event Type"])

A_m = {
    (k, m): set(grp.loc[grp["Compulsory"], "Module Name"])
    for (k, m), grp in ct_groups
}

B_m = {
    (k, m): set(grp.loc[~grp["Compulsory"], "Module Name"])
    for (k, m), grp in ct_groups
}

# -------------------------
# 5. demand (fast using itertuples)
# -------------------------
demand = {
    (row["Module Name"], row["Event Type"]): row["Duration (hours)"]
    for _, row in event_df.iterrows()
}

# -------------------------
# 6. enrolled from set_df
# -------------------------
enrolled = {
    (row["Module Name"], row["Event Type"]): row["Event Size"]
    for _, row in set_df.iterrows()
}

# these tutorials are cohorted -> too much demand, so uncohort them some
demand["Global Challenges for Business", "Tutorial"] = 7
enrolled["Global Challenges for Business", "Tutorial"] = 74

demand["PGDE Secondary Curriculum and Pedagogy", "Tutorial"] = 8
enrolled["PGDE Secondary Curriculum and Pedagogy", "Tutorial"] = 200

demand["Year 5 - Process of Care 2", "Tutorial"] = 9
enrolled["Year 5 - Process of Care 2", "Tutorial"] = 110

demand["Clinical Psychology 1", "Tutorial"] = 40
enrolled["Clinical Psychology 1", "Tutorial"] = 55

demand["Clinical Psychology 2", "Tutorial"] = 40
enrolled["Clinical Psychology 2", "Tutorial"] = 55

# fuck the futures institute
for m in M:
    for i in I:
        if "(fusion online)" in i.lower(): 
            demand[(i,m)] = 0
            enrolled[i,m] = 0
        elif "(fusion on-site)" in i.lower():
            demand[(i,m)] = 0
            enrolled[i,m] = 0

# these are the same program doing a new course each week
demand["CBT with Complex Presentations", "Lecture"] = 0
demand["CBT with Children and Young People in Practice", "Lecture"] = 0
demand["CBT Placement 1", "Lecture"] = 0

# this had mislabeled practical as lecture
demand["Conception to Parturition", "Lecture"] -= 3
demand["Conception to Parturition", "Tutorial"] += 1

# these had mislabeled discussion as lecture
demand["Gametes and Gonads", "Lecture"] -= 3
demand["Development and Disease", "Lecture"] -= 3
demand["Reproductive Cancers", "Lecture"] -=1

values = [v for v in enrolled.values() if v not in (0, None) and not (isinstance(v, float) and np.isnan(v))]
avg_enrolled = sum(values) / len(values)

for i in I:
    for m in M:
        if (i,m) in enrolled and enrolled[i,m] == 0:
            enrolled[i,m] = avg_enrolled

for k in K:
    if len(A[k]) > 6:
        print(k)

precomp = {
    "K": K,
    "I": I,
    "M": M,
    "A": A,
    "B": B,
    "A_m": A_m,
    "B_m": B_m,
    "demand": demand,
    "enrolled": enrolled,
    "C": C,
    "R_c": R_c
}

with open("model_inputs.pkl", "wb") as f:
    pickle.dump(precomp, f)
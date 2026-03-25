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
for i in I:
    for m in M:
        if (i,m) in demand and demand[i,m] >= 20:
            print(f"{i}:\t{m}")
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
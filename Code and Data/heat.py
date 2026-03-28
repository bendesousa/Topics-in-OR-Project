#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 27 22:27:54 2026

@author: nolanbearw
"""

import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt

tt = pd.read_csv("uni_timetable.csv")
tt = tt[["Time", "Day"]]

# 1. Count occurrences of each (Time, Day)
counts = tt.groupby(["Time", "Day"]).size().reset_index(name="Count")

# 2. Pivot so rows=Time, columns=Day, values=Count
heatmap_data = counts.pivot(index="Time", columns="Day", values="Count").fillna(0)

# 3. Sort rows/columns so it looks nice
heatmap_data = heatmap_data.sort_index().reindex(columns=["Monday","Tuesday","Wednesday My Dudes", "Out of Touch Thursday", "It's Friday Thennnnn"])

# 4. Plot
sns.heatmap(heatmap_data, annot=True, fmt=".0f", cmap="viridis")
plt.savefig("tt_heatmap.png")
plt.show()


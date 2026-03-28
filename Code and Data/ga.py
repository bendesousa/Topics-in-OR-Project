import random
import numpy as np

#Data Preparation Functions
def prepare_events_and_demand(event_df):
    """
    Converts event_df into:
    - events: list of (Module Name, Event Type)
    - demand: dict mapping (Module Name, Event Type) -> required count
    """

    # Ensure deterministic ordering
    event_df = event_df.sort_values(["Module Name", "Event Type"])

    # Unique events
    events = list(
        event_df[["Module Name", "Event Type"]]
        .drop_duplicates()
        .itertuples(index=False, name=None)
    )

    # Demand mapping
    demand = {}
    for _, row in event_df.iterrows():
        key = (row["Module Name"], row["Event Type"])
        demand[key] = int(row["Weekly Requirement"])

    return events, demand

#Function to initialize the population for the genetic algorithm
def initialize_population(pop_size, events, T, D):
    population = []

    for _ in range(pop_size):
        individual = []
        for _ in events:
            t = random.choice(T)
            d = random.choice(D)
            individual.append((t, d))
        population.append(individual)

    return population

#Alg1 - Fitness function to evaluate the quality of a timetable
def evaluate_alg1(individual, events, demand):

    assignment = {}
    for idx, (t, d) in enumerate(individual):
        i, m = events[idx]
        assignment[(i, m)] = (t, d)

    violations = 0

    # Demand constraint
    for (i, m), req in demand.items():
        assigned = sum(
            1 for (ii, mm) in assignment.keys()
            if ii == i and mm == m
        )
        violations += abs(assigned - req)

    # Clash constraint
    slot_map = {}
    for (i, m), (t, d) in assignment.items():
        slot_map.setdefault((t, d), []).append((i, m))

    for _, assigned_events in slot_map.items():
        if len(assigned_events) > 1:
            violations += len(assigned_events) - 1

    return violations

#Alg2 - Fitness function to evaluate the quality of a timetable with soft constraints
def evaluate_alg2(individual, events):

    # Count number of clashes (soft objective)
    slot_map = {}

    for idx, (t, d) in enumerate(individual):
        i, m = events[idx]
        slot_map.setdefault((t, d), []).append((i, m))

    clashes = 0

    for _, assigned_events in slot_map.items():
        if len(assigned_events) > 1:
            clashes += len(assigned_events) - 1

    return clashes

#Candidate Selection for crossover
def select_parent(population, fitnesses):
    Vmax = max(fitnesses)

    if Vmax == 0:
        weights = [1 for _ in fitnesses]
    else:
        weights = [(Vmax - f + 1) / (Vmax + 1) for f in fitnesses]

    return random.choices(population, weights=weights, k=1)[0]

#Cross over between two parents to create a child
def crossover(p1, p2):
    child = []

    for gene1, gene2 in zip(p1, p2):
        t1, d1 = gene1
        t2, d2 = gene2

        r = random.random()

        if r < 0.25:
            child.append((t1, d1))
        elif r < 0.5:
            child.append((t2, d1))
        elif r < 0.75:
            child.append((t1, d2))
        else:
            child.append((t2, d2))

    return child

#Mutation of a child
def mutate(individual, T, D, p=0.1):
    if random.random() > p:
        return individual

    individual = individual.copy()

    if random.random() < 0.5:
        # Mutation type (i): random reassignment
        idx = random.randint(0, len(individual) - 1)
        individual[idx] = (random.choice(T), random.choice(D))
    else:
        # Mutation type (ii): swap two events
        i, j = random.sample(range(len(individual)), 2)
        individual[i], individual[j] = individual[j], individual[i]

    return individual

#Local search
def local_search(individual, events, T, D, max_iters=50):

    for _ in range(max_iters):

        # Build slot map
        slot_map = {}
        for idx, (t, d) in enumerate(individual):
            slot_map.setdefault((t, d), []).append(idx)

        # Identify conflicts
        conflicts = []
        for _, idxs in slot_map.items():
            if len(idxs) > 1:
                conflicts.extend(idxs)

        if not conflicts:
            break

        # Fix one random conflicting event
        idx = random.choice(conflicts)
        individual[idx] = (random.choice(T), random.choice(D))

    return individual

#Main GA Loop
def run_ga(event_df, T, D, mode="alg1", pop_size=50, generations=100, initial_population=None):

    # --- Prepare structured inputs ---
    events, demand = prepare_events_and_demand(event_df)
    
    events, demand = prepare_events_and_demand(event_df)

    if mode == "alg1":
        fitness_func = lambda ind: evaluate_alg1(ind, events, demand)
    else:
        fitness_func = lambda ind: evaluate_alg2(ind, events)

    # --- Initialise population ---
    if initial_population is not None:
        population = initial_population
    else:
        population = initialize_population(pop_size, events, T, D)

    for _ in range(generations):

        fitnesses = [fitness_func(ind) for ind in population]

        # STOP CONDITION FOR ALG1
        if mode == "alg1" and all(f == 0 for f in fitnesses):
            break

        # Early stopping if feasible
        if min(fitnesses) == 0:
            break

        new_population = []

        for _ in range(pop_size):

            p1 = select_parent(population, fitnesses)
            p2 = select_parent(population, fitnesses)

            child = crossover(p1, p2)
            child = mutate(child, T, D)
            child = local_search(child, events, T, D)

            new_population.append(child)

        population = new_population

    # Final selection
    # For Alg1, return entire feasible population
    if mode == "alg1":
        return population, events

    # For Alg2, still return best solution
    fitnesses = [fitness_func(ind) for ind in population]
    best_idx = np.argmin(fitnesses)
    best_solution = population[best_idx]

    return best_solution, events
# calculations.py - COMPLETE FILE with Corrected Trips & Logging

import numpy as np
import math # Make sure math is imported for isnan if needed later

# Constants
DAYS_PER_YEAR = 365.0 # Still potentially needed elsewhere, keep for now

# --- Calculate Daily Trips Function (CORRECTED) ---
def calculate_daily_trips(population_per_year, processed_mode_shares, show_rate_percent):
    """
    Calculates the AVERAGE DAILY trips for each active mode, considering the show rate.
    Assumes 1 trip per person present per day.

    Args:
        population_per_year (list): Total population for each year.
        processed_mode_shares (dict): Final mode shares for *active* modes (keyed by mode key, summing to 100).
        show_rate_percent (float): The percentage of population present daily (0-100).

    Returns:
        tuple: (dict of AVERAGE DAILY trips per mode per year keyed by active mode key,
                list of total AVERAGE DAILY trips per year for the effective population)
    """
    print("[Calc] calculate_daily_trips called.") # LOG START
    num_years = len(population_per_year)
    if num_years == 0:
        print("[Calc] calculate_daily_trips: No years, returning empty.")
        return {}, []

    # Validate show_rate_percent
    if not isinstance(show_rate_percent, (int, float)) or not (0 <= show_rate_percent <= 100):
        raise ValueError("Show Rate must be a number between 0 and 100.")
    show_rate_fraction = show_rate_percent / 100.0
    print(f"[Calc] calculate_daily_trips: Show rate fraction: {show_rate_fraction}") # LOG

    active_mode_keys = list(processed_mode_shares.keys())
    if not active_mode_keys:
        print("[Calc] calculate_daily_trips: No active mode keys, returning empty.")
        return {}, [0.0] * num_years
    print(f"[Calc] calculate_daily_trips: Active keys: {active_mode_keys}") # LOG

    # Initialize result structures
    trips_per_mode_per_year = {mode_key: np.zeros(num_years) for mode_key in active_mode_keys}
    total_daily_trips_per_year = np.zeros(num_years)

    population_array = np.array(population_per_year)

    # Calculate effective population present on an AVERAGE DAY for each year
    effective_daily_population_per_year = population_array * show_rate_fraction
    print(f"[Calc] calculate_daily_trips: Effective daily population per year: {effective_daily_population_per_year.tolist()}") # LOG

    for i in range(num_years):
        # The total number of trips on an average day is equal to the effective population present
        total_trips_on_avg_day = effective_daily_population_per_year[i]
        total_daily_trips_per_year[i] = total_trips_on_avg_day # Store this total

        # Distribute these total daily trips across active modes based on share
        for mode_key in active_mode_keys:
            share_fraction = processed_mode_shares.get(mode_key, 0.0) / 100.0
            # Calculate absolute daily trips for this mode for this year
            trips_per_mode_per_year[mode_key][i] = total_trips_on_avg_day * share_fraction

    # Convert numpy arrays to lists for JSON serialization
    trips_per_mode_per_year_list = {
        mode_key: arr.tolist() for mode_key, arr in trips_per_mode_per_year.items()
    }
    total_daily_trips_per_year_list = total_daily_trips_per_year.tolist()

    # --- ADD LOG BEFORE RETURN ---
    print(f"[Calc] DEBUG: Calculated trips_per_mode_per_year_list: {trips_per_mode_per_year_list}")
    print(f"[Calc] DEBUG: Calculated total_daily_trips_per_year_list: {total_daily_trips_per_year_list}")
    # --- END LOG ---

    return trips_per_mode_per_year_list, total_daily_trips_per_year_list


# --- Analyze Parking Function (Keep as previously refactored) ---
def analyze_parking(population_per_year, processed_mode_shares, parking_supply_per_year,
                    parking_cost_per_space, show_rate_percent, active_mode_info):
    # ... (Implementation remains the same - ensure no / DAYS_PER_YEAR here either if it existed) ...
    print("[Calc] analyze_parking called.") # LOG START
    num_years = len(population_per_year)
    if num_years == 0: return [], [], []
    if not isinstance(parking_supply_per_year, list) or len(parking_supply_per_year) != num_years: raise ValueError("Parking supply length mismatch.")
    if not isinstance(parking_cost_per_space, (int, float)) or parking_cost_per_space < 0: raise ValueError("Parking cost non-negative.")
    if not isinstance(show_rate_percent, (int, float)) or not (0 <= show_rate_percent <= 100): raise ValueError("Show Rate invalid.")
    show_rate_fraction = show_rate_percent / 100.0
    demand_per_year = np.zeros(num_years)
    population_array = np.array(population_per_year)
    supply_array = np.array(parking_supply_per_year)
    effective_population_per_year = population_array * show_rate_fraction
    active_mode_keys = list(processed_mode_shares.keys())
    print(f"[Calc] analyze_parking: Effective daily pop: {effective_population_per_year.tolist()}") # LOG
    print(f"[Calc] analyze_parking: Active mode info received: {active_mode_info}") # LOG

    for i in range(num_years):
        current_year_demand = 0.0
        current_effective_population = effective_population_per_year[i]
        for mode_key in active_mode_keys:
            mode_info = active_mode_info.get(mode_key)
            if not mode_info: print(f"Warning: Mode info missing for {mode_key} in parking."); continue
            if mode_info['flags'].get('affects_parking', False):
                share_percentage = processed_mode_shares.get(mode_key, 0.0)
                if share_percentage > 0:
                    share_fraction = share_percentage / 100.0
                    people_present_using_mode = current_effective_population * share_fraction
                    parking_factor = mode_info.get('parking_factor_per_person', 0.0)
                    if parking_factor == 0.0 and mode_info['flags'].get('affects_parking'): print(f"Warning: Mode {mode_key} affects parking but factor is 0.")
                    current_year_demand += people_present_using_mode * parking_factor
        demand_per_year[i] = current_year_demand

    shortfall_per_year = np.maximum(0, demand_per_year - supply_array)
    cost_per_year = shortfall_per_year * parking_cost_per_space
    print(f"[Calc] analyze_parking results: demand={demand_per_year.tolist()}, shortfall={shortfall_per_year.tolist()}, cost={cost_per_year.tolist()}") # LOG Results
    return demand_per_year.tolist(), shortfall_per_year.tolist(), cost_per_year.tolist()


# --- Create Summary Table Function (Keep as is) ---
def create_summary_table(years, population_per_year, total_daily_trips_per_year,
                         parking_demand_per_year, parking_supply_per_year, parking_shortfall_per_year):
    print("[Calc] create_summary_table called.") # LOG START
    summary = []
    num_years = len(years)
    total_population_display = population_per_year
    # Simple inline helper to get value safely
    get_val = lambda lst, index, default=0: lst[index] if isinstance(lst, list) and 0 <= index < len(lst) else default
    for i in range(num_years):
        summary.append({
            "year": years[i],
            "population": round(get_val(total_population_display, i)),
            "total_daily_trips": round(get_val(total_daily_trips_per_year, i)),
            "parking_demand": round(get_val(parking_demand_per_year, i)),
            "parking_supply": get_val(parking_supply_per_year, i),
            "parking_shortfall": round(get_val(parking_shortfall_per_year, i)),
        })
    print(f"[Calc] create_summary_table result: {summary}") # LOG
    return summary
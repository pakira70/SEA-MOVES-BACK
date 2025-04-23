# calculations.py - Updated to use Show Rate

import numpy as np
# import pandas as pd # Optional

# --- Constants ---
MODES = ["Drive", "Light Rail", "Bus", "Drop-off", "Walk", "Carpool", "Vanpool", "Bike"]
BASELINE_MODE_SHARES = { # Keep for reference or potential future use
    "Drive": 71.0, "Light Rail": 10.0, "Bus": 9.0, "Drop-off": 5.0,
    "Walk": 2.0, "Carpool": 1.0, "Vanpool": 1.0, "Bike": 1.0
}
PARKING_DEMAND_FACTORS_PER_PERSON = { # Per person *present*
    "Drive": 1.0, "Carpool": 0.5, "Vanpool": 0.25
}
DAYS_PER_YEAR = 365.0 # Or potentially adjust based on context? Keep simple for now.
DRIVE_KEY = "Drive"


# --- Normalization and Balancing Function ---
# Use the last correct version (proportional for all changes)
def normalize_and_balance_shares(input_shares, changed_mode=None, new_value=None):
    """ Normalizes shares ensuring sum = 100. Applies proportional redistribution. """
    # Step 1: Initialize and clean inputs
    working_shares = {}; original_numeric_shares = {}; current_input_sum = 0.0
    for mode in MODES:
        raw_value = input_shares.get(mode, 0.0); num_value = 0.0
        try: num_value = float(raw_value)
        except (ValueError, TypeError): num_value = 0.0
        clean_value = max(0.0, num_value)
        working_shares[mode] = clean_value
        original_numeric_shares[mode] = clean_value
        current_input_sum += clean_value
    if current_input_sum <= 1e-9: return BASELINE_MODE_SHARES.copy() # Handle zero sum
    if abs(current_input_sum - 100.0) > 1e-7: # Normalize originals for proportions
        factor = 100.0 / current_input_sum
        for mode in original_numeric_shares: original_numeric_shares[mode] *= factor

    # Step 2: Determine change delta
    delta = 0.0; target_value = None; is_change_valid = False
    if changed_mode and changed_mode in working_shares and new_value is not None:
        try:
            target_value = max(0.0, min(100.0, float(new_value)))
            delta = target_value - original_numeric_shares.get(changed_mode, 0.0)
            if abs(delta) > 1e-9: is_change_valid = True
            else: changed_mode = None # No redistribution if delta is tiny
        except (ValueError, TypeError):
            print(f"Warning: Invalid new value '{new_value}' for {changed_mode}.")
            changed_mode = None

    # Step 3: Apply Proportional Redistribution
    if is_change_valid:
        working_shares[changed_mode] = target_value
        other_sum_before_change = sum(v for k, v in original_numeric_shares.items() if k != changed_mode)
        if other_sum_before_change > 1e-9:
            adjustment_factor = -delta / other_sum_before_change
            for k in working_shares:
                if k != changed_mode:
                    adjustment = original_numeric_shares[k] * adjustment_factor
                    working_shares[k] = max(0.0, min(100.0, original_numeric_shares[k] + adjustment))
        else:
             print(f"Warning: Sum of other modes is zero for {changed_mode}, cannot redistribute.")
             for k in working_shares:
                 if k != changed_mode: working_shares[k] = 0.0

    # Step 4: Final Balancing & Float Precision Cleanup
    final_shares = working_shares.copy()
    current_sum = sum(final_shares.values()); final_diff = 100.0 - current_sum
    if abs(final_diff) > 1e-9:
        drive_share = final_shares.get(DRIVE_KEY, 0.0)
        can_adjust_drive = (drive_share + final_diff >= -1e-9) and (drive_share + final_diff <= 100.0 + 1e-9)
        adjust_mode = DRIVE_KEY
        if not can_adjust_drive:
             other_modes = {k:v for k,v in final_shares.items() if k != DRIVE_KEY and v > 1e-9}
             if other_modes: adjust_mode = max(other_modes, key=other_modes.get)
        if adjust_mode in final_shares:
             final_shares[adjust_mode] += final_diff
             final_shares[adjust_mode] = max(0.0, min(100.0, final_shares[adjust_mode]))
        else: print(f"Warning: Could not find mode ('{adjust_mode}') for final sum correction.")
    for mode in final_shares: # Final non-negative check
        if final_shares[mode] < 0: final_shares[mode] = 0.0
    final_sum_check = sum(final_shares.values()) # Final attempt to fix sum
    if abs(100.0 - final_sum_check) > 1e-7:
       final_diff_again = 100.0 - final_sum_check
       final_shares[DRIVE_KEY] = max(0.0, min(100.0, final_shares.get(DRIVE_KEY, 0.0) + final_diff_again))

    return final_shares


# --- Calculate Daily Trips Function (MODIFIED) ---
def calculate_daily_trips(population_per_year, mode_shares, show_rate_percent):
    """
    Calculates the average daily trips for each mode, considering the show rate.

    Args:
        population_per_year (list): Total annual population for each year.
        mode_shares (dict): Final mode shares (summing to 100).
        show_rate_percent (float): The percentage of population present daily (0-100).

    Returns:
        tuple: (dict of mode trips per year, list of total daily trips per year)
    """
    num_years = len(population_per_year)
    if num_years == 0: return {}, []

    # Validate show_rate_percent
    if not isinstance(show_rate_percent, (int, float)) or not (0 <= show_rate_percent <= 100):
        raise ValueError("Show Rate must be a number between 0 and 100.")
    show_rate_fraction = show_rate_percent / 100.0

    trips_per_mode_per_year = {mode: np.zeros(num_years) for mode in MODES}
    total_daily_trips_per_year = np.zeros(num_years)
    population_array = np.array(population_per_year)

    # Calculate effective daily population considering show rate
    effective_daily_population_per_year = population_array * show_rate_fraction

    for i in range(num_years):
        # Total daily trips *for the population present*
        # Assuming 1 trip per person present per day for now
        daily_total_trips_year_effective = effective_daily_population_per_year[i] / DAYS_PER_YEAR
        total_daily_trips_per_year[i] = daily_total_trips_year_effective # Store the effective total

        # Distribute these effective daily trips across modes
        for mode in MODES:
            share_fraction = mode_shares.get(mode, 0.0) / 100.0
            trips_per_mode_per_year[mode][i] = daily_total_trips_year_effective * share_fraction

    # Convert back to lists for JSON response
    trips_per_mode_per_year_list = {mode: arr.tolist() for mode, arr in trips_per_mode_per_year.items()}
    total_daily_trips_per_year_list = total_daily_trips_per_year.tolist()

    return trips_per_mode_per_year_list, total_daily_trips_per_year_list


# --- Analyze Parking Function (MODIFIED) ---
def analyze_parking(population_per_year, mode_shares, parking_supply_per_year,
                    parking_cost_per_space, show_rate_percent):
    """
    Calculates annual PEAK parking demand, shortfall, and cost, considering show rate.

    Args:
        population_per_year (list): Total annual population for each year.
        mode_shares (dict): Final mode shares (summing to 100).
        parking_supply_per_year (list): Annual parking supply.
        parking_cost_per_space (float): Cost per parking space.
        show_rate_percent (float): The percentage of population present daily (0-100).

    Returns:
        tuple: (list of demand per year, list of shortfall per year, list of cost per year)
    """
    num_years = len(population_per_year)
    if num_years == 0: return [], [], []

    # Validate inputs
    if not isinstance(parking_supply_per_year, list) or len(parking_supply_per_year) != num_years:
        raise ValueError("Parking supply data length mismatch.")
    if not isinstance(parking_cost_per_space, (int, float)) or parking_cost_per_space < 0:
        raise ValueError("Parking cost must be non-negative.")
    if not isinstance(show_rate_percent, (int, float)) or not (0 <= show_rate_percent <= 100):
        raise ValueError("Show Rate must be a number between 0 and 100.")
    show_rate_fraction = show_rate_percent / 100.0

    demand_per_year = np.zeros(num_years)
    population_array = np.array(population_per_year)
    supply_array = np.array(parking_supply_per_year)

    # Calculate effective daily population considering show rate
    effective_population_per_year = population_array * show_rate_fraction

    for i in range(num_years):
        current_year_demand = 0.0
        current_effective_population = effective_population_per_year[i] # Use effective pop

        # Calculate demand based on people *actually present*
        for mode, factor in PARKING_DEMAND_FACTORS_PER_PERSON.items():
            share_percentage = mode_shares.get(mode, 0.0)
            if share_percentage > 0: # Only calculate if share > 0
                share_fraction = share_percentage / 100.0
                # Apply mode share to the effective population
                people_present_using_mode = current_effective_population * share_fraction
                current_year_demand += people_present_using_mode * factor

        demand_per_year[i] = current_year_demand

    # Calculate shortfall and cost based on demand vs supply
    shortfall_per_year = np.maximum(0, demand_per_year - supply_array)
    cost_per_year = shortfall_per_year * parking_cost_per_space

    return demand_per_year.tolist(), shortfall_per_year.tolist(), cost_per_year.tolist()


# --- Create Summary Table Function ---
# (No changes needed here, it just takes the calculated results)
def create_summary_table(years, population_per_year, total_daily_trips_per_year,
                         parking_demand_per_year, parking_supply_per_year, parking_shortfall_per_year):
    """Creates a list of dictionaries summarizing key metrics per year."""
    summary = []
    num_years = len(years)
    # Use total_population for display in the table, even if trips/demand use effective pop
    total_population_display = population_per_year

    def get_val(lst, index, default=0):
        try: return lst[index] if lst and index < len(lst) else default
        except IndexError: return default

    for i in range(num_years):
        summary.append({
            "year": years[i],
            "population": get_val(total_population_display, i), # Show total pop
            "total_daily_trips": round(get_val(total_daily_trips_per_year, i)), # Show effective trips
            "parking_demand": round(get_val(parking_demand_per_year, i)), # Show effective demand
            "parking_supply": get_val(parking_supply_per_year, i),
            "parking_shortfall": round(get_val(parking_shortfall_per_year, i)),
        })
    return summary
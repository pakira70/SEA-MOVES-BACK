# calculations.py - Updated for Proportional Balancing on ALL Changes

import numpy as np
# import pandas as pd # Optional

# --- Constants ---
MODES = ["Drive", "Light Rail", "Bus", "Drop-off", "Walk", "Carpool", "Vanpool", "Bike"]
BASELINE_MODE_SHARES = {
    "Drive": 71.0, "Light Rail": 10.0, "Bus": 9.0, "Drop-off": 5.0,
    "Walk": 2.0, "Carpool": 1.0, "Vanpool": 1.0, "Bike": 1.0
}
PARKING_DEMAND_FACTORS_PER_PERSON = {
    "Drive": 1.0, "Carpool": 0.5, "Vanpool": 0.25
}
DAYS_PER_YEAR = 365.0
DRIVE_KEY = "Drive"


# --- Normalization and Balancing Function (MODIFIED) ---
def normalize_and_balance_shares(input_shares, changed_mode=None, new_value=None):
    """
    Normalizes shares ensuring sum = 100.
    If changed_mode and new_value are provided, it applies proportional
    redistribution based on the change delta before final balancing.

    Args:
        input_shares (dict): Raw input shares (can have strings or numbers).
        changed_mode (str, optional): The key of the mode the user explicitly changed.
        new_value (float or str, optional): The target numeric value for the changed_mode.

    Returns:
        dict: Fully normalized and balanced dictionary with numeric shares summing to 100.
    """
    # Step 1: Initialize and clean inputs to numeric, non-negative floats
    working_shares = {}
    original_numeric_shares = {}
    current_input_sum = 0.0
    for mode in MODES:
        raw_value = input_shares.get(mode, 0.0)
        num_value = 0.0
        try:
            num_value = float(raw_value)
        except (ValueError, TypeError):
            num_value = 0.0 # Default to 0 if conversion fails
        clean_value = max(0.0, num_value) # Ensure non-negative
        working_shares[mode] = clean_value
        original_numeric_shares[mode] = clean_value
        current_input_sum += clean_value

    # Handle case where initial sum is zero
    if current_input_sum <= 1e-9:
        print("Warning: Initial sum of shares is zero. Returning baseline.")
        return BASELINE_MODE_SHARES.copy()

    # Normalize original_numeric_shares if needed (for proportion calculation)
    if abs(current_input_sum - 100.0) > 1e-7:
        factor = 100.0 / current_input_sum
        for mode in original_numeric_shares:
            original_numeric_shares[mode] *= factor


    # Step 2: Determine the change delta if a specific mode was changed
    delta = 0.0
    target_value = None
    is_change_valid = False
    if changed_mode and changed_mode in working_shares and new_value is not None:
        try:
            # Clamp target value between 0 and 100
            target_value = max(0.0, min(100.0, float(new_value)))
            # Calculate delta based on the cleaned & potentially normalized original value
            delta = target_value - original_numeric_shares.get(changed_mode, 0.0)
            # Only consider it a valid change if the delta is significant
            if abs(delta) > 1e-9:
                is_change_valid = True
            else:
                # If delta is effectively zero, treat as no change for redistribution
                changed_mode = None # Prevent Step 3 redistribution
                # Set the working share to the target value anyway for final balancing
                working_shares[changed_mode] = target_value

        except (ValueError, TypeError):
            print(f"Warning: Invalid new value '{new_value}' for {changed_mode}. No redistribution applied.")
            # If value is invalid, don't apply specific redistribution
            changed_mode = None # Prevent Step 3 redistribution


    # Step 3: Apply Proportional Redistribution Logic (If Valid Change Occurred)
    if is_change_valid: # is_change_valid is now true only if delta is significant
        working_shares[changed_mode] = target_value # Apply the primary change

        # Calculate sum of OTHERS before the change, using normalized original values
        other_sum_before_change = sum(v for k, v in original_numeric_shares.items() if k != changed_mode)

        if other_sum_before_change > 1e-9:
            # Calculate the factor to adjust other modes.
            # If delta > 0 (mode increased), factor is negative (others decrease).
            # If delta < 0 (mode decreased), factor is positive (others increase).
            adjustment_factor = -delta / other_sum_before_change

            # Apply proportional adjustment to all other modes
            for k in working_shares:
                if k != changed_mode:
                    # Calculate the change amount for this 'other' mode based on its original share
                    adjustment = original_numeric_shares[k] * adjustment_factor
                    # Apply the adjustment, ensuring bounds (0-100)
                    working_shares[k] = max(0.0, min(100.0, original_numeric_shares[k] + adjustment))
        else:
             # Edge case: If other sum is zero, cannot redistribute proportionally.
             # The changed_mode has its target_value, others remain zero.
             # Final balancing (Step 4) will handle ensuring sum is 100.
             print(f"Warning: Sum of other modes is zero for {changed_mode}, cannot redistribute delta={delta} proportionally.")
             # Ensure other modes are explicitly zero if they weren't already
             for k in working_shares:
                 if k != changed_mode:
                     working_shares[k] = 0.0

    # --- Step 4: Final Balancing & Float Precision Cleanup ---
    # This step ensures the final sum is exactly 100, primarily adjusting Drive.
    # If Drive can't absorb the full difference, it adjusts the largest other mode.
    final_shares = working_shares.copy()
    current_sum = sum(final_shares.values())
    final_diff = 100.0 - current_sum

    # Only adjust if the difference is significant
    if abs(final_diff) > 1e-9:
        # Prioritize adjusting Drive if it won't go out of 0-100 bounds
        drive_share = final_shares.get(DRIVE_KEY, 0.0)
        can_adjust_drive = (drive_share + final_diff >= -1e-9) and (drive_share + final_diff <= 100.0 + 1e-9)

        adjust_mode = DRIVE_KEY
        if not can_adjust_drive:
             # If Drive can't be adjusted, find the largest other mode to adjust
             other_modes = {k:v for k,v in final_shares.items() if k != DRIVE_KEY and v > 1e-9} # Find non-zero others
             if other_modes:
                 adjust_mode = max(other_modes, key=other_modes.get)
             # If only Drive exists or all others are zero, adjust_mode remains Drive

        if adjust_mode in final_shares:
             final_shares[adjust_mode] += final_diff
             # Clamp the final adjusted value strictly between 0 and 100
             final_shares[adjust_mode] = max(0.0, min(100.0, final_shares[adjust_mode]))
        else:
             # This should be rare - indicates no mode could be adjusted
             print(f"Warning: Could not find suitable mode ('{adjust_mode}') to apply final sum correction of {final_diff:.4f}.")

    # Final check to ensure all values are non-negative after potential adjustments
    for mode in final_shares:
        if final_shares[mode] < 0:
            final_shares[mode] = 0.0

    # Ensure final sum is exactly 100 after clamping/adjustments
    final_sum_check = sum(final_shares.values())
    if abs(100.0 - final_sum_check) > 1e-7:
       # If still not 100, apply remaining difference to Drive as last resort
       final_diff_again = 100.0 - final_sum_check
       final_shares[DRIVE_KEY] = max(0.0, min(100.0, final_shares.get(DRIVE_KEY, 0.0) + final_diff_again))
       # print(f"Warning: Applied final correction {final_diff_again:.4f} to Drive after clamping.")

    return final_shares


# --- Calculate Daily Trips Function ---
# (Keep the existing correct version)
def calculate_daily_trips(population_per_year, mode_shares):
    """Calculates the average daily trips for each mode."""
    num_years = len(population_per_year)
    if num_years == 0: return {}, []
    trips_per_mode_per_year = {mode: np.zeros(num_years) for mode in MODES}
    total_daily_trips_per_year = np.zeros(num_years)
    population_array = np.array(population_per_year)
    annual_total_trips = population_array # Assuming 1 trip per person per year (adjust if needed)
    for i in range(num_years):
        daily_total_trips_year = annual_total_trips[i] / DAYS_PER_YEAR
        total_daily_trips_per_year[i] = daily_total_trips_year
        for mode in MODES:
            share_fraction = mode_shares.get(mode, 0.0) / 100.0
            trips_per_mode_per_year[mode][i] = daily_total_trips_year * share_fraction
    trips_per_mode_per_year_list = {mode: arr.tolist() for mode, arr in trips_per_mode_per_year.items()}
    total_daily_trips_per_year_list = total_daily_trips_per_year.tolist()
    return trips_per_mode_per_year_list, total_daily_trips_per_year_list


# --- Analyze Parking Function ---
# (Keep the existing correct version)
def analyze_parking(population_per_year, mode_shares, parking_supply_per_year, parking_cost_per_space):
    """Calculates annual PEAK parking demand, shortfall, and cost."""
    num_years = len(population_per_year)
    if num_years == 0: return [], [], []
    if not isinstance(parking_supply_per_year, list) or len(parking_supply_per_year) != num_years: raise ValueError("Parking supply data length mismatch.")
    if not isinstance(parking_cost_per_space, (int, float)) or parking_cost_per_space < 0: raise ValueError("Parking cost must be non-negative.")
    demand_per_year = np.zeros(num_years)
    population_array = np.array(population_per_year)
    supply_array = np.array(parking_supply_per_year)
    for i in range(num_years):
        current_year_demand = 0.0
        current_population = population_array[i]
        for mode, factor in PARKING_DEMAND_FACTORS_PER_PERSON.items():
            share_percentage = mode_shares.get(mode, 0.0)
            if share_percentage > 0: # Only calculate if share > 0
                share_fraction = share_percentage / 100.0
                people_using_mode = current_population * share_fraction
                current_year_demand += people_using_mode * factor
        demand_per_year[i] = current_year_demand
    shortfall_per_year = np.maximum(0, demand_per_year - supply_array)
    cost_per_year = shortfall_per_year * parking_cost_per_space
    return demand_per_year.tolist(), shortfall_per_year.tolist(), cost_per_year.tolist()


# --- Create Summary Table Function ---
# (Keep the existing correct version)
def create_summary_table(years, population_per_year, total_daily_trips_per_year,
                         parking_demand_per_year, parking_supply_per_year, parking_shortfall_per_year):
    """Creates a list of dictionaries summarizing key metrics per year."""
    summary = []
    num_years = len(years)
    def get_val(lst, index, default=0):
        try: return lst[index] if lst and index < len(lst) else default
        except IndexError: return default
    for i in range(num_years):
        summary.append({
            "year": years[i],
            "population": get_val(population_per_year, i),
            "total_daily_trips": round(get_val(total_daily_trips_per_year, i)),
            "parking_demand": round(get_val(parking_demand_per_year, i)),
            "parking_supply": get_val(parking_supply_per_year, i),
            "parking_shortfall": round(get_val(parking_shortfall_per_year, i)),
        })
    return summary
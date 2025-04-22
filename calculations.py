# calculations.py - CLEAN VERSION - Oct 2023 (or date relevant to generation)

import numpy as np
# import pandas as pd # Optional: Keep if needed elsewhere, remove if not

# --- Constants ---
MODES = ["Drive", "Light Rail", "Bus", "Drop-off", "Walk", "Carpool", "Vanpool", "Bike"]
BASELINE_MODE_SHARES = {
    "Drive": 71.0, "Light Rail": 10.0, "Bus": 9.0, "Drop-off": 5.0,
    "Walk": 2.0, "Carpool": 1.0, "Vanpool": 1.0, "Bike": 1.0
}
# Parking demand factor PER PERSON using that mode
PARKING_DEMAND_FACTORS_PER_PERSON = {
    "Drive": 1.0,
    "Carpool": 0.5,
    "Vanpool": 0.25
}
DAYS_PER_YEAR = 365.0
DRIVE_KEY = "Drive" # Constant for the Drive mode key


# --- Normalization and Balancing Function ---
# This is the primary function called by app.py now
def normalize_and_balance_shares(input_shares, changed_mode=None, new_value=None):
    """
    Normalizes shares ensuring Drive + Sum(NonDrive) = 100.
    If changed_mode and new_value are provided, it applies redistribution rules
    prioritizing Drive interaction before final balancing and normalization.

    Args:
        input_shares (dict): Raw input shares (can have strings or numbers).
        changed_mode (str, optional): The key of the mode the user explicitly changed.
        new_value (float or str, optional): The target numeric value for the changed_mode.

    Returns:
        dict: Fully normalized and balanced dictionary with numeric shares summing to 100.
    """
    # Step 1: Initialize and clean inputs to numeric, non-negative floats
    # Creates working_shares (cleaned numbers) and original_numeric_shares
    working_shares = {}
    original_numeric_shares = {}
    current_input_sum = 0.0 # Track sum of initial numeric values for edge cases
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

    # Handle case where initial sum is zero (cannot proceed)
    if current_input_sum <= 1e-9:
        print("Warning: Initial sum of shares is zero. Returning baseline.")
        return BASELINE_MODE_SHARES.copy()

    # If initial sum is not 100, normalize original_numeric_shares for proportion calculation later
    # This prevents issues if the input dict didn't sum to 100 initially
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
            target_value = max(0.0, min(100.0, float(new_value)))
            # Calculate delta based on the cleaned initial numeric value
            delta = target_value - original_numeric_shares.get(changed_mode, 0.0)
            is_change_valid = True
        except (ValueError, TypeError):
            print(f"Warning: Invalid new value '{new_value}' for {changed_mode}. No redistribution applied.")
            # If value is invalid, we won't apply specific redistribution

    # Step 3: Apply Redistribution Logic OR Simple Balancing

    if is_change_valid and abs(delta) > 1e-9:
        # --- A specific mode was validly changed ---
        working_shares[changed_mode] = target_value # Apply the change

        if changed_mode == DRIVE_KEY:
            # --- Drive Changed ---
            if delta > 0: # Drive Increased -> Reduce others proportionally
                # Use normalized original shares for proportions
                other_sum_before_change = sum(v for k, v in original_numeric_shares.items() if k != DRIVE_KEY)
                if other_sum_before_change > 1e-9:
                    reduction_factor = delta / other_sum_before_change
                    for k in working_shares:
                        if k != DRIVE_KEY:
                             reduction = original_numeric_shares[k] * reduction_factor
                             working_shares[k] = max(0.0, original_numeric_shares[k] - reduction) # Clamp at 0
            else: # Drive Decreased (delta < 0) -> Increase others proportionally
                other_sum_before_change = sum(v for k, v in original_numeric_shares.items() if k != DRIVE_KEY)
                if other_sum_before_change > 1e-9:
                    increase_amount = abs(delta)
                    increase_factor = increase_amount / other_sum_before_change
                    for k in working_shares:
                        if k != DRIVE_KEY:
                            working_shares[k] = min(100.0, original_numeric_shares[k] * (1.0 + increase_factor)) # Clamp at 100

        else: # changed_mode != DRIVE_KEY
            # --- Non-Drive Mode Changed ---
            if delta > 0: # Non-Drive Increased -> Reduce Drive ONLY
                current_drive_share = original_numeric_shares.get(DRIVE_KEY, 0.0)
                possible_drive_reduction = min(delta, current_drive_share)
                final_new_value = original_numeric_shares[changed_mode] + possible_drive_reduction # Adjust target
                working_shares[changed_mode] = final_new_value
                working_shares[DRIVE_KEY] = current_drive_share - possible_drive_reduction
                # Restore other non-drive modes to their original numeric values explicitly
                for k in MODES:
                    if k != changed_mode and k != DRIVE_KEY:
                        working_shares[k] = original_numeric_shares[k]

            else: # Non-Drive Decreased (delta < 0) -> Increase Drive ONLY
                current_drive_share = original_numeric_shares.get(DRIVE_KEY, 0.0)
                increase_amount = abs(delta)
                working_shares[DRIVE_KEY] = min(100.0, current_drive_share + increase_amount) # Clamp at 100
                working_shares[changed_mode] = target_value # Set the decreased value
                # Restore other non-drive modes to their original numeric values explicitly
                for k in MODES:
                    if k != changed_mode and k != DRIVE_KEY:
                        working_shares[k] = original_numeric_shares[k]

    # --- Step 4: Final Balancing & Float Precision Cleanup ---
    # Regardless of redistribution, ensure Drive balances the non-drive sum
    final_shares = working_shares.copy() # Use the result of redistribution or initial cleanup
    non_drive_sum = sum(v for k, v in final_shares.items() if k != DRIVE_KEY)

    if non_drive_sum > 100.0 + 1e-9: # Allow tiny overshoot initially
         # Scale down non-drive modes if their sum is too high
         scale_factor = 100.0 / non_drive_sum if non_drive_sum > 1e-9 else 0
         non_drive_sum = 0.0
         for mode in MODES:
             if mode != DRIVE_KEY:
                 final_shares[mode] *= scale_factor
                 non_drive_sum += final_shares[mode]
         final_shares[DRIVE_KEY] = 0.0 # Drive must be 0
    else:
        # Set Drive based on valid non_drive_sum, ensuring non-negative
        final_shares[DRIVE_KEY] = max(0.0, 100.0 - non_drive_sum)

    # Final pass to correct tiny floating point sum errors to hit exactly 100
    final_sum_check = sum(final_shares.values())
    diff = 100.0 - final_sum_check
    if abs(diff) > 1e-9:
        # Prefer adjusting Drive if it has room, otherwise adjust largest share
        adjust_mode = DRIVE_KEY
        # Check if Drive can absorb the difference without going below 0
        if final_shares.get(DRIVE_KEY, 0.0) < abs(diff) and diff < 0 : # Need to add, but Drive is too small
             # Find largest other mode to adjust
             other_modes = {k:v for k,v in final_shares.items() if k != DRIVE_KEY}
             if other_modes:
                 adjust_mode = max(other_modes, key=other_modes.get)
             # If only Drive exists (e.g., 99.9999), adjust_mode remains Drive
        elif final_shares.get(DRIVE_KEY, 0.0) + diff > 100.0 : # Need to subtract, but Drive would go over 100 (shouldn't happen)
             other_modes = {k:v for k,v in final_shares.items() if k != DRIVE_KEY}
             if other_modes:
                 adjust_mode = max(other_modes, key=other_modes.get)


        if adjust_mode in final_shares:
            final_shares[adjust_mode] += diff
            # Final clamp after correction
            final_shares[adjust_mode] = max(0.0, min(100.0, final_shares[adjust_mode]))
        else:
            # This case should be very rare, indicates potentially all shares became zero
            print(f"Warning: Could not find suitable mode to apply final sum correction.")

    # Final check (for debugging)
    # final_final_sum = sum(final_shares.values())
    # if abs(100.0 - final_final_sum) > 1e-7:
    #    print(f"ERROR: Final sum check failed significantly! Sum={final_final_sum:.5f}")

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
    annual_total_trips = population_array
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
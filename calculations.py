# calculations.py

import numpy as np
# Keep pandas import if you anticipate using it later, otherwise optional
# import pandas as pd

# --- Constants ---
MODES = ["Drive", "Light Rail", "Bus", "Drop-off", "Walk", "Carpool", "Vanpool", "Bike"]
BASELINE_MODE_SHARES = {
    "Drive": 71.0, "Light Rail": 10.0, "Bus": 9.0, "Drop-off": 5.0,
    "Walk": 2.0, "Carpool": 1.0, "Vanpool": 1.0, "Bike": 1.0
}
# Parking demand factor PER PERSON using that mode
PARKING_DEMAND_FACTORS_PER_PERSON = {
    "Drive": 1.0,    # Each person driving alone needs 1 space
    "Carpool": 0.5,  # Each person carpooling effectively 'uses' 0.5 spaces
    "Vanpool": 0.25 # Each person vanpooling effectively 'uses' 0.25 spaces
}
DAYS_PER_YEAR = 365.0
DRIVE_KEY = "Drive" # Constant for the Drive mode key


# --- Normalization and Balancing Function ---
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
    # Step 1: Initialize and clean inputs to numeric, non-negative values
    working_shares = {}
    original_numeric_shares = {} # Keep original numeric values for proportion calculation
    for mode in MODES:
        raw_value = input_shares.get(mode, 0.0)
        num_value = 0.0
        try:
            num_value = float(raw_value)
        except (ValueError, TypeError):
            # Ignore invalid values during initial cleanup, default to 0
            num_value = 0.0
        # Ensure values start non-negative
        working_shares[mode] = max(0.0, num_value)
        original_numeric_shares[mode] = working_shares[mode] # Store initial numeric value

    # Step 2: Determine the change delta if a specific mode was changed
    delta = 0.0
    target_value = None
    is_change_valid = False # Flag to track if user change should be applied
    if changed_mode and changed_mode in working_shares and new_value is not None:
        try:
            # Validate and clamp the target new value
            target_value = max(0.0, min(100.0, float(new_value)))
            delta = target_value - working_shares[changed_mode] # Calculate based on cleaned initial value
            is_change_valid = True # Mark change as valid
        except (ValueError, TypeError):
            print(f"Warning: Invalid new value '{new_value}' for {changed_mode}. Ignoring specific redistribution.")
            # Proceed with simple balancing if new value is invalid

    # Step 3: Apply Redistribution Logic OR Simple Balancing

    if is_change_valid and abs(delta) > 1e-9:
        # --- A specific mode was validly changed, apply redistribution rules ---
        working_shares[changed_mode] = target_value # Apply the valid change

        if changed_mode == DRIVE_KEY:
            # --- Drive Changed ---
            if delta > 0: # Drive Increased -> Reduce others proportionally
                other_sum_before_change = sum(v for k, v in original_numeric_shares.items() if k != DRIVE_KEY)
                if other_sum_before_change > 1e-9:
                    # Calculate how much reduction is needed per unit of original share
                    reduction_factor = delta / other_sum_before_change
                    for k in working_shares:
                        if k != DRIVE_KEY:
                             # Apply reduction proportionally based on original numeric share
                             reduction = original_numeric_shares[k] * reduction_factor
                             # Ensure we don't reduce below zero
                             working_shares[k] = max(0.0, original_numeric_shares[k] - reduction)
                # If other_sum_before_change is zero, other shares are already 0, Drive goes to 100 (handled by clamp/normalization)
            else: # Drive Decreased (delta < 0) -> Increase others proportionally
                other_sum_before_change = sum(v for k, v in original_numeric_shares.items() if k != DRIVE_KEY)
                if other_sum_before_change > 1e-9:
                    increase_amount = abs(delta)
                    increase_factor = increase_amount / other_sum_before_change
                    for k in working_shares:
                        if k != DRIVE_KEY:
                            # Increase based on original numeric share proportion
                            working_shares[k] = min(100.0, original_numeric_shares[k] * (1.0 + increase_factor)) # Clamp at 100

        else: # changed_mode != DRIVE_KEY
            # --- Non-Drive Mode Changed ---
            if delta > 0: # Non-Drive Increased -> Reduce Drive ONLY
                current_drive_share = original_numeric_shares.get(DRIVE_KEY, 0.0)
                # Calculate how much Drive can actually decrease
                possible_drive_reduction = min(delta, current_drive_share)
                # Adjust the target non-drive mode value based on possible reduction
                final_new_value = original_numeric_shares[changed_mode] + possible_drive_reduction
                working_shares[changed_mode] = final_new_value # Set adjusted target
                # Apply reduction to Drive
                working_shares[DRIVE_KEY] = current_drive_share - possible_drive_reduction
                # Other non-drive modes remain untouched (use values from original_numeric_shares which are same as working_shares before this block)

            else: # Non-Drive Decreased (delta < 0) -> Increase Drive ONLY
                current_drive_share = original_numeric_shares.get(DRIVE_KEY, 0.0)
                increase_amount = abs(delta)
                # Increase drive, clamping at 100
                working_shares[DRIVE_KEY] = min(100.0, current_drive_share + increase_amount)
                # Changed non-drive mode value is already set
                # Other non-drive modes remain untouched

    # --- Step 4: Final Balancing & Float Precision Cleanup ---
    # This step ensures sum is exactly 100, using Drive as the primary buffer
    # It acts as the default balancing if no specific mode was changed, or as a cleanup after redistribution
    final_shares = working_shares.copy() # Work on a final copy
    non_drive_sum = sum(v for k, v in final_shares.items() if k != DRIVE_KEY)

    if non_drive_sum > 100.0 + 1e-9: # Allow tiny overshoot initially
         # Non-drive sum is too high, scale them down to 100 and set Drive to 0
         scale_factor = 100.0 / non_drive_sum if non_drive_sum > 1e-9 else 0
         non_drive_sum = 0.0 # Recalculate
         for mode in MODES:
             if mode != DRIVE_KEY:
                 final_shares[mode] *= scale_factor
                 non_drive_sum += final_shares[mode]
         final_shares[DRIVE_KEY] = 0.0
    else:
        # Non-drive sum is <= 100, set Drive to the difference
        final_shares[DRIVE_KEY] = max(0.0, 100.0 - non_drive_sum) # Ensure Drive isn't negative

    # Final pass to correct tiny floating point sum errors
    final_sum_check = sum(final_shares.values())
    diff = 100.0 - final_sum_check
    if abs(diff) > 1e-9:
        # Prefer adjusting Drive if it has room, otherwise adjust largest share
        adjust_mode = DRIVE_KEY if final_shares.get(DRIVE_KEY, 0.0) >= abs(diff) else max(final_shares, key=final_shares.get)
        if adjust_mode in final_shares:
             final_shares[adjust_mode] += diff
             # Final clamp after correction
             final_shares[adjust_mode] = max(0.0, min(100.0, final_shares[adjust_mode]))

    return final_shares


# --- Calculate Daily Trips Function ---
def calculate_daily_trips(population_per_year, mode_shares):
    """
    Calculates the average daily trips for each mode over the simulation period.
    Uses the final processed mode_shares.
    """
    num_years = len(population_per_year)
    if num_years == 0:
        return {}, []

    trips_per_mode_per_year = {mode: np.zeros(num_years) for mode in MODES}
    total_daily_trips_per_year = np.zeros(num_years)
    population_array = np.array(population_per_year)
    annual_total_trips = population_array # Base assumption: 1 trip/person/year (scaled by mode share later)

    for i in range(num_years):
        # Calculate total trips for the year first based on population
        # The division by DAYS_PER_YEAR averages it out
        daily_total_trips_year = annual_total_trips[i] / DAYS_PER_YEAR
        total_daily_trips_per_year[i] = daily_total_trips_year
        # Distribute total daily trips according to mode share
        for mode in MODES:
            share_fraction = mode_shares.get(mode, 0.0) / 100.0
            trips_per_mode_per_year[mode][i] = daily_total_trips_year * share_fraction

    # Convert numpy arrays to lists for JSON serialization
    trips_per_mode_per_year_list = {
        mode: arr.tolist() for mode, arr in trips_per_mode_per_year.items()
    }
    total_daily_trips_per_year_list = total_daily_trips_per_year.tolist()

    return trips_per_mode_per_year_list, total_daily_trips_per_year_list


# --- Analyze Parking Function ---
def analyze_parking(population_per_year, mode_shares, parking_supply_per_year, parking_cost_per_space):
    """
    Calculates annual PEAK parking demand based on population and mode share for relevant modes,
    then calculates shortfall and potential cost based on supply.
    Uses the final processed mode_shares.
    """
    num_years = len(population_per_year)
    if num_years == 0: return [], [], []

    # Validate inputs (already done in app.py, but good practice)
    if not isinstance(parking_supply_per_year, list) or len(parking_supply_per_year) != num_years:
        raise ValueError("Parking supply data length mismatch.")
    if not isinstance(parking_cost_per_space, (int, float)) or parking_cost_per_space < 0:
        raise ValueError("Parking cost must be non-negative.")

    demand_per_year = np.zeros(num_years)
    population_array = np.array(population_per_year)
    supply_array = np.array(parking_supply_per_year)

    for i in range(num_years):
        current_year_demand = 0.0
        current_population = population_array[i]
        for mode, factor in PARKING_DEMAND_FACTORS_PER_PERSON.items():
            share_percentage = mode_shares.get(mode, 0.0) # Use final shares
            share_fraction = share_percentage / 100.0
            people_using_mode = current_population * share_fraction
            current_year_demand += people_using_mode * factor
        demand_per_year[i] = current_year_demand

    shortfall_per_year = np.maximum(0, demand_per_year - supply_array)
    cost_per_year = shortfall_per_year * parking_cost_per_space

    return demand_per_year.tolist(), shortfall_per_year.tolist(), cost_per_year.tolist()


# --- Create Summary Table Function ---
def create_summary_table(years, population_per_year, total_daily_trips_per_year,
                         parking_demand_per_year, parking_supply_per_year, parking_shortfall_per_year):
    """Creates a list of dictionaries summarizing key metrics per year."""
    summary = []
    num_years = len(years)

    # Helper for safe access, although lists should be validated upstream
    def get_val(lst, index, default=0):
        try: return lst[index] if lst and index < len(lst) else default
        except IndexError: return default

    for i in range(num_years):
        summary.append({
            "year": years[i],
            "population": get_val(population_per_year, i),
            "total_daily_trips": round(get_val(total_daily_trips_per_year, i)),
            "parking_demand": round(get_val(parking_demand_per_year, i)),
            "parking_supply": get_val(parking_supply_per_year, i), # Usually integer input
            "parking_shortfall": round(get_val(parking_shortfall_per_year, i)),
        })
    return summary
# SEA-MOVES-BACK/calculations.py - PARKING LOGIC CORRECTED
import numpy as np
import math

# --- (calculate_daily_trips and create_summary_table remain the same) ---

def calculate_daily_trips(population_per_year, processed_mode_shares, show_rate_percent):
    num_years = len(population_per_year)
    if num_years == 0: return {}, []
    if not isinstance(show_rate_percent, (int, float)) or not (0 <= show_rate_percent <= 100):
        raise ValueError("Show Rate must be a number between 0 and 100.")
    show_rate_fraction = show_rate_percent / 100.0
    active_mode_keys = list(processed_mode_shares.keys())
    if not active_mode_keys: return {}, [0.0] * num_years
    trips_per_mode_per_year = {mode_key: np.zeros(num_years) for mode_key in active_mode_keys}
    total_daily_trips_per_year = np.zeros(num_years)
    population_array = np.array(population_per_year)
    effective_daily_population_per_year = population_array * show_rate_fraction
    for i in range(num_years):
        total_trips_on_avg_day = effective_daily_population_per_year[i]
        total_daily_trips_per_year[i] = total_trips_on_avg_day
        for mode_key in active_mode_keys:
            share_fraction = processed_mode_shares.get(mode_key, 0.0) / 100.0
            trips_per_mode_per_year[mode_key][i] = total_trips_on_avg_day * share_fraction
    trips_per_mode_per_year_list = {k: arr.tolist() for k, arr in trips_per_mode_per_year.items()}
    total_daily_trips_per_year_list = total_daily_trips_per_year.tolist()
    return trips_per_mode_per_year_list, total_daily_trips_per_year_list

def analyze_parking(population_per_year, processed_mode_shares, parking_supply_per_year,
                    parking_cost_per_space, show_rate_percent, active_mode_info):
    num_years = len(population_per_year)
    if num_years == 0: return [], [], []
    
    # --- BUG FIX START: The calculation logic is now iterative to handle cumulative supply ---
    
    show_rate_fraction = show_rate_percent / 100.0
    population_array = np.array(population_per_year)
    initial_supply_array = np.array(parking_supply_per_year)
    effective_population_per_year = population_array * show_rate_fraction

    # Initialize lists to store results
    demand_per_year_list = []
    shortfall_per_year_list = []
    cost_per_year_list = []
    
    # Track the supply as it grows year by year
    cumulative_supply = initial_supply_array[0] if num_years > 0 else 0

    for i in range(num_years):
        # 1. Calculate this year's total parking demand
        current_year_demand = 0.0
        current_effective_population = effective_population_per_year[i]
        for mode_key in processed_mode_shares.keys():
            mode_info = active_mode_info.get(mode_key)
            if mode_info and mode_info['flags'].get('affects_parking', False):
                share_fraction = processed_mode_shares.get(mode_key, 0.0) / 100.0
                parking_factor = mode_info.get('parking_factor_per_person', 0.0)
                current_year_demand += (current_effective_population * share_fraction * parking_factor)
        
        demand_per_year_list.append(current_year_demand)

        # 2. Calculate shortfall against the CURRENT cumulative supply
        current_shortfall = max(0, current_year_demand - cumulative_supply)
        shortfall_per_year_list.append(current_shortfall)
        
        # 3. Calculate cost based ONLY on this year's shortfall
        current_cost = current_shortfall * parking_cost_per_space
        cost_per_year_list.append(current_cost)
        
        # 4. CRITICAL: Add newly built stalls to the cumulative supply for the next year
        cumulative_supply += current_shortfall

    return demand_per_year_list, shortfall_per_year_list, cost_per_year_list
    # --- BUG FIX END ---

def create_summary_table(years, population_per_year, total_daily_trips_per_year,
                         parking_demand_per_year, parking_supply_per_year, parking_shortfall_per_year):
    summary = []
    num_years = len(years)
    get_val = lambda lst, index, default=0: lst[index] if isinstance(lst, list) and 0 <= index < len(lst) else default
    for i in range(num_years):
        summary.append({
            "year": years[i], "population": round(get_val(population_per_year, i)),
            "total_daily_trips": round(get_val(total_daily_trips_per_year, i)),
            "parking_demand": round(get_val(parking_demand_per_year, i)),
            "parking_supply": get_val(parking_supply_per_year, i),
            "parking_shortfall": round(get_val(parking_shortfall_per_year, i)),
        })
    return summary


def analyze_shuttle_costs(baseline_drive_trips_per_year, scenario_drive_trips_per_year, shuttle_params):
    if not shuttle_params.get('includeShuttleCosts', False):
        return { 'baseline_annual_cost_per_year': [], 'scenario_annual_cost_per_year': [], 'baseline_shuttles_per_year': [], 'scenario_shuttles_per_year': [] }

    user_provided_baseline_cost = shuttle_params.get('shuttleBaselineCost', 0)
    parking_percentage = shuttle_params.get('shuttleParkingPercentage', 0)
    peak_hours = shuttle_params.get('shuttlePeakHours', 3)
    vehicle_capacity = shuttle_params.get('shuttleVehicleCapacity', 30)
    cost_per_hour = shuttle_params.get('shuttleCostPerHour', 100)
    min_contract_hours = shuttle_params.get('shuttleMinContractHours', 4)
    operating_days = shuttle_params.get('shuttleOperatingDays', 280)

    if peak_hours <= 0 or vehicle_capacity <= 0:
        raise ValueError("Shuttle peak hours and vehicle capacity must be positive numbers.")

    num_years = len(scenario_drive_trips_per_year)
    if num_years == 0 or len(baseline_drive_trips_per_year) != num_years:
        return { 'baseline_annual_cost_per_year': [user_provided_baseline_cost] * num_years, 'scenario_annual_cost_per_year': [user_provided_baseline_cost] * num_years, 'baseline_shuttles_per_year': [0] * num_years, 'scenario_shuttles_per_year': [0] * num_years }

    baseline_trips_arr = np.array(baseline_drive_trips_per_year)
    scenario_trips_arr = np.array(scenario_drive_trips_per_year)
    
    def _calculate_shuttles_from_trips(trips_array):
        daily_shuttle_riders = trips_array * (parking_percentage / 100.0)
        peak_hour_riders = daily_shuttle_riders / peak_hours
        return np.ceil(peak_hour_riders / vehicle_capacity)

    baseline_shuttles_needed = _calculate_shuttles_from_trips(baseline_trips_arr)
    scenario_shuttles_needed = _calculate_shuttles_from_trips(scenario_trips_arr)

    # THIS IS THE KEY CHANGE: Calculate the raw difference. It can be negative.
    change_in_shuttles_per_year = scenario_shuttles_needed - baseline_shuttles_needed

    cost_per_shuttle_block = cost_per_hour * min_contract_hours
    incremental_annual_cost = change_in_shuttles_per_year * cost_per_shuttle_block * operating_days

    scenario_annual_cost = user_provided_baseline_cost + incremental_annual_cost

    return {
        'baseline_annual_cost_per_year': [user_provided_baseline_cost] * num_years,
        'scenario_annual_cost_per_year': scenario_annual_cost.tolist(),
        'baseline_shuttles_per_year': baseline_shuttles_needed.tolist(),
        'scenario_shuttles_per_year': scenario_shuttles_needed.tolist()
    }
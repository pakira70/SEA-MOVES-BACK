# app.py - MODIFIED

try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    import traceback
    import numpy as np # Keep import
    import sys # Needed for sys.exit() in except block
    import logging # Use Flask's logger
    import math # For isnan check

    print("--- Attempting Imports ---")

    # === Import calculation functions (Refactored) ===
    from calculations import (
        calculate_daily_trips,
        analyze_parking,
        create_summary_table,
    )
    print("--- Imports from calculations.py successful (assuming refactored) ---")

    # === Initialize Flask App and CORS ===
    print("--- Initializing Flask App ---")
    app = Flask(__name__)
    # Configure logging
    logging.basicConfig(level=logging.INFO) # Sets root logger level
    app.logger.setLevel(logging.DEBUG) # Set app logger to DEBUG to catch everything

    CORS(app) # Allow requests from frontend origin
    print("--- Flask App Initialized Successfully ---")


    # =============================================================
    # === Define Available Modes Structure ===
    # =============================================================
# In app.py

    # ... (other parts of app.py) ...

    AVAILABLE_MODES = [
      # --- Personal Vehicles ---
      {
        "key": "DRIVE", "defaultName": "Drive", "defaultColor": "#D32F2F", "category": "Personal Vehicles",
        "flags": { "affects_parking": True, "affects_emissions": True, "affects_cost": True },
        "parking_factor_per_person": 1.0, "isDefaultActive": True, "defaultBaselineShare": 71.0
      },
      { # ADDED DROPOFF
        "key": "DROPOFF", "defaultName": "Drop-off", "defaultColor": "#455A64", "category": "Personal Transport",
        "flags": { "affects_parking": False, "affects_emissions": True, "affects_cost": True },
        "parking_factor_per_person": 0.0, "isDefaultActive": True, "defaultBaselineShare": 5.0
      },
      {
        "key": "BEV", "defaultName": "Drive (BEV)", "defaultColor": "#1976D2", "category": "Personal Vehicles",
        "flags": { "affects_parking": True, "affects_emissions": False, "affects_cost": True },
        "parking_factor_per_person": 1.0, "isDefaultActive": False, "defaultBaselineShare": 0.0
      },
      {
        "key": "MOTORCYCLE", "defaultName": "Motorcycle", "defaultColor": "#FFA000", "category": "Personal Vehicles",
        "flags": { "affects_parking": True, "affects_emissions": True, "affects_cost": True },
        "parking_factor_per_person": 0.5, "isDefaultActive": False, "defaultBaselineShare": 0.0
      },
      {
        "key": "MOPED", "defaultName": "Moped/Scooter", "defaultColor": "#FBC02D", "category": "Personal Vehicles",
        "flags": { "affects_parking": True, "affects_emissions": True, "affects_cost": True },
        "parking_factor_per_person": 0.3, "isDefaultActive": False, "defaultBaselineShare": 0.0
      },
      # --- Carpool & Vanpool ---
      {
         "key": "CARPOOL", "defaultName": "Carpool", "defaultColor": "#FF6F00", "category": "Carpool & Vanpool",
         "flags": { "affects_parking": True, "affects_emissions": True, "affects_cost": True },
         "parking_factor_per_person": 0.5, "isDefaultActive": True, "defaultBaselineShare": 1.0
       },
       {
         "key": "VANPOOL", "defaultName": "Vanpool", "defaultColor": "#4E342E", "category": "Carpool & Vanpool",
         "flags": { "affects_parking": True, "affects_emissions": True, "affects_cost": True },
         "parking_factor_per_person": 0.2, "isDefaultActive": True, "defaultBaselineShare": 1.0
       },
       # --- Micromobility & Active Modes ---
       {
        "key": "BIKE", "defaultName": "Bike", "defaultColor": "#0288D1", "category": "Micromobility & Active",
        "flags": { "affects_parking": False, "affects_emissions": False, "affects_cost": False },
        "parking_factor_per_person": 0.0, "isDefaultActive": True, "defaultBaselineShare": 1.0
      },
      {
        "key": "E_BIKE", "defaultName": "E-Bike", "defaultColor": "#0097A7", "category": "Micromobility & Active",
        "flags": { "affects_parking": False, "affects_emissions": False, "affects_cost": False },
        "parking_factor_per_person": 0.0, "isDefaultActive": False, "defaultBaselineShare": 0.0
      },
      {
        "key": "SKATEBOARD", "defaultName": "Skateboard/Scooter (Manual)", "defaultColor": "#7B1FA2", "category": "Micromobility & Active",
        "flags": { "affects_parking": False, "affects_emissions": False, "affects_cost": False },
        "parking_factor_per_person": 0.0, "isDefaultActive": False, "defaultBaselineShare": 0.0
      },
       {
        "key": "WALK", "defaultName": "Walk", "defaultColor": "#388E3C", "category": "Micromobility & Active",
        "flags": { "affects_parking": False, "affects_emissions": False, "affects_cost": False },
        "parking_factor_per_person": 0.0, "isDefaultActive": True, "defaultBaselineShare": 2.0
      },
       {
        "key": "REGIONAL_TRAIL", "defaultName": "Regional Trail (Walk/Bike)", "defaultColor": "#689F38", "category": "Micromobility & Active",
        "flags": { "affects_parking": False, "affects_emissions": False, "affects_cost": False },
        "parking_factor_per_person": 0.0, "isDefaultActive": False, "defaultBaselineShare": 0.0
      },
       # --- Transit ---
      { 
        "key": "TRANSIT", "defaultName": "Transit", "defaultColor": "#F57C00", 
        "category": "Transit",
        "flags": { "affects_parking": False, "affects_emissions": True, "affects_cost": True }, 
        "parking_factor_per_person": 0.0,
        "isDefaultActive": True, "defaultBaselineShare": 19.0 
      },
      {
        "key": "TRAIN", "defaultName": "Train (Commuter/Heavy Rail)", "defaultColor": "#5D4037", "category": "Transit",
        "flags": { "affects_parking": False, "affects_emissions": True, "affects_cost": True },
        "parking_factor_per_person": 0.0, "isDefaultActive": False, "defaultBaselineShare": 0.0
      },
      {
        "key": "SUBWAY", "defaultName": "Subway/Metro", "defaultColor": "#0D47A1", "category": "Transit",
        "flags": { "affects_parking": False, "affects_emissions": False, "affects_cost": True },
        "parking_factor_per_person": 0.0, "isDefaultActive": False, "defaultBaselineShare": 0.0
      },
       {
        "key": "MONORAIL", "defaultName": "Monorail", "defaultColor": "#E0E0E0", "category": "Transit", 
        "flags": { "affects_parking": False, "affects_emissions": False, "affects_cost": True },
        "parking_factor_per_person": 0.0, "isDefaultActive": False, "defaultBaselineShare": 0.0
      },
      {
        "key": "FERRY", "defaultName": "Ferry", "defaultColor": "#006064", "category": "Transit",
        "flags": { "affects_parking": False, "affects_emissions": True, "affects_cost": True },
        "parking_factor_per_person": 0.0, "isDefaultActive": False, "defaultBaselineShare": 0.0
      },
      # --- Other Slots ---
      {
        "key": "OTHER_1", "defaultName": "Other 1", "defaultColor": "#9E9E9E", "category": "Custom Slots",
        "flags": { "affects_parking": False, "affects_emissions": False, "affects_cost": False },
        "parking_factor_per_person": 0.0, "isDefaultActive": False, "defaultBaselineShare": 0.0
      },
      {
        "key": "OTHER_2", "defaultName": "Other 2", "defaultColor": "#616161", "category": "Custom Slots",
        "flags": { "affects_parking": False, "affects_emissions": False, "affects_cost": False },
        "parking_factor_per_person": 0.0, "isDefaultActive": False, "defaultBaselineShare": 0.0
      }
    ]
    AVAILABLE_MODES_DICT = {mode['key']: mode for mode in AVAILABLE_MODES}
    # The sum of defaultBaselineShare for isDefaultActive: True modes should now be:
    # 71(DRIVE) + 5(DROPOFF) + 1(CARPOOL) + 1(VANPOOL) + 1(BIKE) + 2(WALK) + 19(TRANSIT) = 100
    # ... (rest of app.py) ...
    # ... (rest of the file remains the same) ...

    try:
        default_active_share_sum = sum(
            mode.get('defaultBaselineShare', 0) for mode in AVAILABLE_MODES if mode.get('isDefaultActive')
        )
        if abs(default_active_share_sum - 100.0) > 0.01 and default_active_share_sum > 0:
             print(f"\n!!! WARNING: Sum of 'defaultBaselineShare' for default active modes is {default_active_share_sum:.2f}, not 100.00 !!!")
        elif default_active_share_sum == 0 and any(mode.get('isDefaultActive') for mode in AVAILABLE_MODES):
             print("\n!!! WARNING: No default shares assigned for default active modes. !!!")
        else:
            print(f"--- Default baseline shares sum validated ({default_active_share_sum:.1f}%) ---")
    except Exception as share_val_err:
        print(f"\n!!! Error validating default baseline shares: {share_val_err} !!!")
    # =============================================================

    DEFAULT_PARKING_COST = 5000
    DEFAULT_SHOW_RATE = 100

except Exception as startup_error:
    print("\n!!! AN ERROR OCCURRED DURING APP STARTUP !!!")
    print(f"Error Type: {type(startup_error).__name__}")
    print(f"Error Message: {startup_error}")
    print("\n--- Traceback ---")
    print(traceback.format_exc())
    print("-----------------\n")
    _startup_failed = True
    app = Flask(__name__) # Minimal app to avoid secondary errors
    CORS(app)
else:
    _startup_failed = False


@app.route('/')
def home():
    if _startup_failed: return "Error: Flask app failed to initialize. Check server logs.", 500
    return "SEA MOVES API (v3 - Dynamic Modes) is running."

@app.route('/api/modes/available', methods=['GET'])
def get_available_modes():
    if _startup_failed: return jsonify({"error": "Flask app failed to initialize."}), 500
    try:
        if 'AVAILABLE_MODES' not in globals() or not isinstance(AVAILABLE_MODES, list):
             app.logger.error("CRITICAL: AVAILABLE_MODES not defined or invalid.")
             raise ValueError("AVAILABLE_MODES structure not defined correctly.")
        # The AVAILABLE_MODES list now contains the "TRANSIT" mode and excludes "BUS" and "LIGHT_RAIL"
        return jsonify(AVAILABLE_MODES), 200
    except Exception as e:
        app.logger.error(f"Error in /api/modes/available: {e}\n{traceback.format_exc()}")
        return jsonify({"error": "Internal server error fetching available modes."}), 500

@app.route('/api/calculate', methods=['POST'])
def calculate():
    if _startup_failed: return jsonify({"error": "Flask app failed to initialize."}), 500
    app.logger.debug(f"Received /api/calculate request. Headers: {request.headers}")

    try:
        data = request.get_json()
        if not data:
            app.logger.warning("CALCULATE API: Received empty or invalid JSON payload.")
            return jsonify({"error": "Invalid JSON payload"}), 400
        
        app.logger.info(f"CALCULATE API: Received data: {data}") # Log received data

        active_mode_keys = data.get('activeModeKeys')
        mode_customizations = data.get('modeCustomizations', {})
        input_parameters = data.get('inputParameters', {})
        mode_shares_input = input_parameters.get('modeShares', {})
        population_per_year = input_parameters.get('population_per_year')
        parking_supply_per_year = input_parameters.get('parking_supply_per_year')
        parking_cost_per_space = input_parameters.get('parking_cost_per_space', DEFAULT_PARKING_COST)
        show_rate_percent = input_parameters.get('show_rate_percent', DEFAULT_SHOW_RATE)
        num_years = input_parameters.get('num_years', len(population_per_year) if isinstance(population_per_year, list) else 0)

        # --- Validation ---
        # This validation section now implicitly expects "TRANSIT" and will reject "BUS" or "LIGHT_RAIL"
        # if they are sent by the client, because AVAILABLE_MODES_DICT (derived from AVAILABLE_MODES)
        # no longer contains "BUS" or "LIGHT_RAIL".
        if not isinstance(active_mode_keys, list) or not active_mode_keys:
            app.logger.error(f"VALIDATION FAIL: 'activeModeKeys' must be a non-empty list. Received: {active_mode_keys}")
            return jsonify({"error": "'activeModeKeys' must be a non-empty list"}), 400
        if not isinstance(mode_customizations, dict):
            app.logger.error(f"VALIDATION FAIL: 'modeCustomizations' must be an object. Received: {mode_customizations}")
            return jsonify({"error": "'modeCustomizations' must be an object"}), 400
        # ... (keep other basic type/existence checks as they were, or add more logging if needed)

        calculated_num_years = len(population_per_year) if isinstance(population_per_year, list) else 0
        if num_years != calculated_num_years:
             app.logger.warning(f"Num_years mismatch: passed {num_years}, calculated from pop_per_year {calculated_num_years}. Using calculated.")
        num_years = calculated_num_years # Correct num_years based on actual data length

        if parking_supply_per_year and len(parking_supply_per_year) != num_years: # check if parking_supply_per_year is not None
            app.logger.error(f"VALIDATION FAIL: Data length mismatch: Population ({num_years}) vs Parking Supply ({len(parking_supply_per_year)}).")
            return jsonify({"error": f"Data length mismatch: Population ({num_years}) vs Parking Supply ({len(parking_supply_per_year)})."}), 400

        unknown_keys = [k for k in active_mode_keys if k not in AVAILABLE_MODES_DICT]
        if unknown_keys:
            app.logger.error(f"VALIDATION FAIL: Unknown mode keys provided: {', '.join(unknown_keys)}. Active keys were: {active_mode_keys}")
            return jsonify({"error": f"Unknown mode keys provided: {', '.join(unknown_keys)}"}), 400
        
        share_keys = list(mode_shares_input.keys())
        # Compare sets for content equality regardless of order
        if set(share_keys) != set(active_mode_keys):
            app.logger.error(f"VALIDATION FAIL: Mismatch between keys in 'activeModeKeys' ({sorted(active_mode_keys)}) and 'modeShares' ({sorted(share_keys)}).")
            return jsonify({"error": "Mismatch between keys in 'activeModeKeys' and 'modeShares'"}), 400

        total_share = 0
        for key in active_mode_keys: # Iterate based on active_mode_keys which should now match mode_shares_input keys
            share_val = mode_shares_input.get(key) # Safely get value
            if share_val is None: # Explicitly check if a key from activeModeKeys is missing in modeShares
                detailed_error_msg = f"VALIDATION FAIL: Share value for active mode '{key}' is missing from modeShares input. mode_shares_input: {mode_shares_input}"
                app.logger.error(detailed_error_msg)
                return jsonify({"error": f"Share value for active mode '{key}' is missing from modeShares input."}), 400

            if not isinstance(share_val, (int, float)) or math.isnan(share_val) or share_val < 0 or share_val > 100:
                detailed_error_msg = f"VALIDATION FAIL: Invalid share value for mode '{key}': {share_val}. Type: {type(share_val)}. Payload mode_shares_input: {mode_shares_input}"
                app.logger.error(detailed_error_msg)
                return jsonify({"error": f"Invalid share value for mode '{key}': {share_val}"}), 400
            total_share += share_val
        
        if not (99.9 < total_share < 100.1): # Slightly wider tolerance for sum, frontend should send 100.0
             detailed_error_msg_sum = f"VALIDATION FAIL: Input 'modeShares' sum is {total_share:.2f} (must be 100.0). Active keys: {active_mode_keys}. Payload mode_shares_input: {mode_shares_input}"
             app.logger.error(detailed_error_msg_sum)
             return jsonify({"error": f"Input 'modeShares' for active modes must sum to 100 (received {total_share:.2f})"}), 400
        
        # --- End Validation ---

        active_mode_info = {}
        for key in active_mode_keys:
             base_mode = AVAILABLE_MODES_DICT[key] # This will now fetch "TRANSIT" properties
             custom = mode_customizations.get(key, {})
             active_mode_info[key] = {
                 "key": key,
                 "name": custom.get("name", base_mode["defaultName"]),
                 "color": custom.get("color", base_mode["defaultColor"]),
                 "flags": base_mode["flags"],
                 "parking_factor_per_person": base_mode.get("parking_factor_per_person", 0.0)
             }

        app.logger.info("Calling calculation functions...")
        processed_mode_shares = mode_shares_input # Expects "TRANSIT" key if active

        trips_per_mode_per_year, total_daily_trips_per_year = calculate_daily_trips(
            population_per_year=population_per_year,
            processed_mode_shares=processed_mode_shares, # Will use "TRANSIT" if provided
            show_rate_percent=show_rate_percent
        )
        parking_demand_per_year, parking_shortfall_per_year, parking_cost_per_year = analyze_parking(
            population_per_year=population_per_year,
            processed_mode_shares=processed_mode_shares, # Will use "TRANSIT" if provided
            parking_supply_per_year=parking_supply_per_year,
            parking_cost_per_space=parking_cost_per_space,
            show_rate_percent=show_rate_percent,
            active_mode_info=active_mode_info # Will contain "TRANSIT" info if active
        )
        years_for_table = list(range(1, num_years + 1)) if num_years > 0 else []
        
        summary_table = create_summary_table(
            years=years_for_table, # Use actual years
            population_per_year=population_per_year,
            total_daily_trips_per_year=total_daily_trips_per_year,
            parking_demand_per_year=parking_demand_per_year,
            parking_supply_per_year=parking_supply_per_year,
            parking_shortfall_per_year=parking_shortfall_per_year
        )
        app.logger.info("Calculation functions completed.")

        response = {
            "years": years_for_table, # Send actual years
            "population_per_year": population_per_year,
            "parking": {
                "demand_per_year": parking_demand_per_year,
                "supply_per_year": parking_supply_per_year,
                "shortfall_per_year": parking_shortfall_per_year,
                "cost_per_year": parking_cost_per_year,
                "cost_per_space": parking_cost_per_space
            },
            "trips_per_mode_per_year": trips_per_mode_per_year, # Will have "TRANSIT" key if calculated
            "processed_mode_shares": processed_mode_shares,    # Will have "TRANSIT" key if sent
            "mode_details_for_display": active_mode_info, # Send details of active modes used in calc
            "summary_table": summary_table,
            "calculation_parameters": { "show_rate_percent": show_rate_percent }
        }
        app.logger.info("Sending successful calculation response.")
        return jsonify(response), 200

    except ValueError as ve:
         app.logger.error(f"CALCULATE API - Value Error: {ve}\n{traceback.format_exc()}")
         return jsonify({"error": str(ve)}), 400
    except Exception as e:
         app.logger.error(f"CALCULATE API - Unexpected error: {e}\n{traceback.format_exc()}")
         return jsonify({"error": "Internal server error during calculation."}), 500

if __name__ == '__main__':
    if not _startup_failed:
        print("--- Starting Flask Development Server (v3 - Dynamic Modes, Enhanced Logging) ---")
        if 'app' in globals() and isinstance(app, Flask):
             # A small check for parking_supply_per_year length, should be based on num_years from data
             # For example, in calculate: if parking_supply_per_year and len(parking_supply_per_year) != num_years:
             app.run(debug=True, port=5001)
        else:
             print("!!! Critical Error: 'app' variable not defined. Cannot run server. !!!")
    else:
        print("!!! Flask app startup failed. Server will not run. !!!")
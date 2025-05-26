# app.py - FULL VERSION with DETAILED STARTUP LOGGING

print("[STARTUP_LOG] Stage 0: Top of app.py, about to attempt imports.") # LOG 0
try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    import traceback
    import numpy as np # Keep import
    import sys # Needed for sys.exit() in except block
    import logging # Use Flask's logger
    import math # For isnan check

    print("[STARTUP_LOG] Stage 1: Basic imports done.") # LOG 1

    # === Import calculation functions (Refactored) ===
    from calculations import (
        calculate_daily_trips,
        analyze_parking,
        create_summary_table,
    )
    print("[STARTUP_LOG] Stage 2: 'calculations' import done.") # LOG 2

    # === Initialize Flask App and CORS ===
    print("[STARTUP_LOG] Stage 3: About to initialize Flask app.") # LOG 3
    app = Flask(__name__)
    # Configure logging
    logging.basicConfig(level=logging.INFO) # Sets root logger level
    app.logger.setLevel(logging.DEBUG) # Set app logger to DEBUG to catch everything

    CORS(app) # Allow requests from frontend origin
    print("[STARTUP_LOG] Stage 4: Flask app initialized and CORS configured.") # LOG 4


    # =============================================================
    # === Define Available Modes Structure ===
    # =============================================================
    print("[STARTUP_LOG] Stage 5: About to define AVAILABLE_MODES.") # LOG 5
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
    print("[STARTUP_LOG] Stage 6: AVAILABLE_MODES defined.") # LOG 6

    AVAILABLE_MODES_DICT = {mode['key']: mode for mode in AVAILABLE_MODES}
    print("[STARTUP_LOG] Stage 7: AVAILABLE_MODES_DICT defined.") # LOG 7
    # =============================================================

    print("[STARTUP_LOG] Stage 8: About to validate shares sum.") # LOG 8
    try:
        default_active_share_sum = sum(
            mode.get('defaultBaselineShare', 0) for mode in AVAILABLE_MODES if mode.get('isDefaultActive')
        )
        if abs(default_active_share_sum - 100.0) > 0.01 and default_active_share_sum > 0:
             print(f"[STARTUP_LOG] !!! WARNING: Sum of 'defaultBaselineShare' for default active modes is {default_active_share_sum:.2f}, not 100.00 !!!")
        elif default_active_share_sum == 0 and any(mode.get('isDefaultActive') for mode in AVAILABLE_MODES):
             print("[STARTUP_LOG] !!! WARNING: No default shares assigned for default active modes. !!!")
        else:
            print(f"[STARTUP_LOG] Stage 9: Default baseline shares sum validated ({default_active_share_sum:.1f}%).") # LOG 9
    except Exception as share_val_err:
        print(f"[STARTUP_LOG] !!! Error validating default baseline shares: {share_val_err} !!!")
    # =============================================================

    DEFAULT_PARKING_COST = 5000
    DEFAULT_SHOW_RATE = 100
    print("[STARTUP_LOG] Stage 10: Default constants defined. End of main try block reached.") # LOG 10

except Exception as startup_error:
    print("[STARTUP_LOG] !!! AN ERROR OCCURRED DURING APP STARTUP (Caught by main try-except) !!!") # LOG 11
    print(f"[STARTUP_LOG] Error Type: {type(startup_error).__name__}")
    print(f"[STARTUP_LOG] Error Message: {startup_error}")
    print("\n[STARTUP_LOG] --- Traceback ---")
    print(traceback.format_exc()) # This will print the full traceback
    print("[STARTUP_LOG] -----------------\n")
    _startup_failed = True
    app = Flask(__name__) # Minimal app to avoid secondary errors if 'app' was not defined
    CORS(app)
else:
    _startup_failed = False
    print("[STARTUP_LOG] Stage 12: Main try block SUCCESSFUL, _startup_failed set to False.") # LOG 12

print("[STARTUP_LOG] Stage 13: Defining routes now...") # LOG 13
@app.route('/')
def home():
    if _startup_failed: return "Error: Flask app failed to initialize. Check server logs.", 500
    return "SEA MOVES API (v3 - Dynamic Modes) is running."

@app.route('/api/modes/available', methods=['GET'])
def get_available_modes():
    if _startup_failed:
        print("[ROUTE_LOG] /api/modes/available: Startup failed flag is True.")
        return jsonify({"error": "Flask app failed to initialize properly."}), 500
    try:
        if 'AVAILABLE_MODES' not in globals() or not isinstance(AVAILABLE_MODES, list):
             print("[ROUTE_LOG] CRITICAL (get_available_modes): AVAILABLE_MODES not defined or invalid.")
             # Potentially use app.logger if app object from try block is guaranteed
             return jsonify({"error": "AVAILABLE_MODES structure not defined correctly on server."}), 500
        # print(f"[ROUTE_LOG] /api/modes/available: Serving {len(AVAILABLE_MODES)} modes.") # Verbose log
        return jsonify(AVAILABLE_MODES), 200
    except Exception as e:
        print(f"[ROUTE_LOG] Error in /api/modes/available: {e}\n{traceback.format_exc()}")
        return jsonify({"error": "Internal server error fetching available modes."}), 500

@app.route('/api/calculate', methods=['POST'])
def calculate():
    if _startup_failed:
        print("[ROUTE_LOG] /api/calculate: Startup failed flag is True.")
        return jsonify({"error": "Flask app failed to initialize properly."}), 500
    
    # For brevity, the full calculate logic from your file is assumed here.
    # Ensure any print/logging uses a prefix like [ROUTE_LOG] or [CALC_LOG]
    # Example of adding a log at the start of this function:
    print(f"[ROUTE_LOG] /api/calculate: Received request. Headers: {request.headers}")


    try:
        data = request.get_json()
        if not data:
            print("[CALC_LOG] CALCULATE API: Received empty or invalid JSON payload.")
            return jsonify({"error": "Invalid JSON payload"}), 400
        
        # print(f"[CALC_LOG] CALCULATE API: Received data: {data}") # Verbose

        active_mode_keys = data.get('activeModeKeys')
        mode_customizations = data.get('modeCustomizations', {})
        input_parameters = data.get('inputParameters', {})
        mode_shares_input = input_parameters.get('modeShares', {})
        population_per_year = input_parameters.get('population_per_year')
        parking_supply_per_year = input_parameters.get('parking_supply_per_year')
        
        # Ensure DEFAULT_PARKING_COST and DEFAULT_SHOW_RATE are accessible.
        # If startup failed and these weren't defined in the main try block's scope,
        # provide fallbacks or handle it.
        # However, if _startup_failed is True, we return early.
        # If _startup_failed is False, these constants from the 'else' block's scope should be fine.
        # For safety, or if they were defined inside the main try:
        current_default_parking_cost = DEFAULT_PARKING_COST if 'DEFAULT_PARKING_COST' in globals() else 5000
        current_default_show_rate = DEFAULT_SHOW_RATE if 'DEFAULT_SHOW_RATE' in globals() else 100

        parking_cost_per_space = input_parameters.get('parking_cost_per_space', current_default_parking_cost)
        show_rate_percent = input_parameters.get('show_rate_percent', current_default_show_rate)
        
        num_years = input_parameters.get('num_years', len(population_per_year) if isinstance(population_per_year, list) else 0)

        # --- Validation ---
        if not isinstance(active_mode_keys, list) or not active_mode_keys:
            print(f"[CALC_LOG] VALIDATION FAIL: 'activeModeKeys' must be a non-empty list. Received: {active_mode_keys}")
            return jsonify({"error": "'activeModeKeys' must be a non-empty list"}), 400
        if not isinstance(mode_customizations, dict):
            print(f"[CALC_LOG] VALIDATION FAIL: 'modeCustomizations' must be an object. Received: {mode_customizations}")
            return jsonify({"error": "'modeCustomizations' must be an object"}), 400
        
        if not population_per_year or not isinstance(population_per_year, list):
            print(f"[CALC_LOG] VALIDATION FAIL: 'population_per_year' is missing or not a list.")
            return jsonify({"error": "'population_per_year' is missing or not a list"}), 400


        calculated_num_years = len(population_per_year)
        if num_years != calculated_num_years :
             print(f"[CALC_LOG] Num_years mismatch: passed {num_years}, calculated from pop_per_year {calculated_num_years}. Using calculated.")
        num_years = calculated_num_years 

        if parking_supply_per_year and len(parking_supply_per_year) != num_years: 
            print(f"[CALC_LOG] VALIDATION FAIL: Data length mismatch: Pop ({num_years}) vs Parking Supply ({len(parking_supply_per_year)}).")
            return jsonify({"error": f"Data length mismatch: Population ({num_years}) vs Parking Supply ({len(parking_supply_per_year)})."}), 400

        if 'AVAILABLE_MODES_DICT' not in globals():
             print("[CALC_LOG] CRITICAL (validation): AVAILABLE_MODES_DICT not defined.")
             return jsonify({"error": "Server configuration error: Mode dictionary unavailable."}), 500

        unknown_keys = [k for k in active_mode_keys if k not in AVAILABLE_MODES_DICT]
        if unknown_keys:
            print(f"[CALC_LOG] VALIDATION FAIL: Unknown mode keys: {', '.join(unknown_keys)}. Active: {active_mode_keys}")
            return jsonify({"error": f"Unknown mode keys provided: {', '.join(unknown_keys)}"}), 400
        
        share_keys = list(mode_shares_input.keys())
        if set(share_keys) != set(active_mode_keys):
            print(f"[CALC_LOG] VALIDATION FAIL: Mismatch keys 'activeModeKeys' ({sorted(active_mode_keys)}) vs 'modeShares' ({sorted(share_keys)}).")
            return jsonify({"error": "Mismatch between keys in 'activeModeKeys' and 'modeShares'"}), 400

        total_share = 0
        for key in active_mode_keys: 
            share_val = mode_shares_input.get(key) 
            if share_val is None: 
                print(f"[CALC_LOG] VALIDATION FAIL: Share for '{key}' missing. mode_shares_input: {mode_shares_input}")
                return jsonify({"error": f"Share value for active mode '{key}' is missing from modeShares input."}), 400
            if not isinstance(share_val, (int, float)) or math.isnan(share_val) or share_val < 0 or share_val > 100:
                print(f"[CALC_LOG] VALIDATION FAIL: Invalid share for '{key}': {share_val}. Payload: {mode_shares_input}")
                return jsonify({"error": f"Invalid share value for mode '{key}': {share_val}"}), 400
            total_share += share_val
        
        if not (99.9 < total_share < 100.1): 
             print(f"[CALC_LOG] VALIDATION FAIL: 'modeShares' sum is {total_share:.2f}. Active: {active_mode_keys}. Payload: {mode_shares_input}")
             return jsonify({"error": f"Input 'modeShares' for active modes must sum to 100 (received {total_share:.2f})"}), 400
        
        active_mode_info = {}
        for key in active_mode_keys:
             base_mode = AVAILABLE_MODES_DICT[key] 
             custom = mode_customizations.get(key, {})
             active_mode_info[key] = {
                 "key": key, "name": custom.get("name", base_mode["defaultName"]),
                 "color": custom.get("color", base_mode["defaultColor"]), "flags": base_mode["flags"],
                 "parking_factor_per_person": base_mode.get("parking_factor_per_person", 0.0)
             }

        print("[CALC_LOG] Calling calculation functions...")
        processed_mode_shares = mode_shares_input 

        trips_per_mode_per_year, total_daily_trips_per_year = calculate_daily_trips(
            population_per_year=population_per_year,
            processed_mode_shares=processed_mode_shares, 
            show_rate_percent=show_rate_percent
        )
        parking_demand_per_year, parking_shortfall_per_year, parking_cost_per_year = analyze_parking(
            population_per_year=population_per_year,
            processed_mode_shares=processed_mode_shares, 
            parking_supply_per_year=parking_supply_per_year,
            parking_cost_per_space=parking_cost_per_space,
            show_rate_percent=show_rate_percent,
            active_mode_info=active_mode_info 
        )
        years_for_table = list(range(1, num_years + 1)) if num_years > 0 else []
        
        summary_table = create_summary_table(
            years=years_for_table, population_per_year=population_per_year,
            total_daily_trips_per_year=total_daily_trips_per_year,
            parking_demand_per_year=parking_demand_per_year,
            parking_supply_per_year=parking_supply_per_year,
            parking_shortfall_per_year=parking_shortfall_per_year
        )
        print("[CALC_LOG] Calculation functions completed.")

        response = {
            "years": years_for_table, "population_per_year": population_per_year,
            "parking": {
                "demand_per_year": parking_demand_per_year, "supply_per_year": parking_supply_per_year,
                "shortfall_per_year": parking_shortfall_per_year, "cost_per_year": parking_cost_per_year,
                "cost_per_space": parking_cost_per_space
            },
            "trips_per_mode_per_year": trips_per_mode_per_year, 
            "processed_mode_shares": processed_mode_shares,    
            "mode_details_for_display": active_mode_info, 
            "summary_table": summary_table,
            "calculation_parameters": { "show_rate_percent": show_rate_percent }
        }
        print("[CALC_LOG] Sending successful calculation response.")
        return jsonify(response), 200

    except ValueError as ve:
         print(f"[CALC_LOG] CALCULATE API - Value Error: {ve}\n{traceback.format_exc()}")
         return jsonify({"error": str(ve)}), 400
    except Exception as e:
         print(f"[CALC_LOG] CALCULATE API - Unexpected error: {e}\n{traceback.format_exc()}")
         return jsonify({"error": "Internal server error during calculation."}), 500

print("[STARTUP_LOG] Stage 14: Routes defined.") # LOG 14

if __name__ == '__main__':
    print("[STARTUP_LOG] Running in __main__ (local dev server)") # LOG 15
    if not _startup_failed:
        print("[STARTUP_LOG] Starting Flask Development Server (local dev)...") # LOG 16
        if 'app' in globals() and isinstance(app, Flask):
             app.run(debug=True, port=5001)
        else:
             print("[STARTUP_LOG] !!! Critical Error: 'app' variable not defined. Cannot run server. !!!")
    else:
        print("[STARTUP_LOG] !!! Flask app startup failed (local dev). Server will not run. !!!") # LOG 17
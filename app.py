# app.py - FULL VERSION with CLEANED UP LOGGING

try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    import traceback
    import numpy as np # Keep import
    import sys # Needed for sys.exit() in except block
    import logging # Use Flask's logger
    import math # For isnan check

    # === Import calculation functions (Refactored) ===
    from calculations import (
        calculate_daily_trips,
        analyze_parking,
        create_summary_table,
    )

    # === Initialize Flask App and CORS ===
    app = Flask(__name__)
    # Configure logging
    # Set root logger level - this affects libraries as well.
    # Consider setting to INFO for production if library logs are too verbose.
    logging.basicConfig(level=logging.INFO) 
    # Set Flask's app logger to DEBUG to catch all app-specific logs.
    # Handlers (like the default stream handler to console) will then filter based on their own level.
    # For Render, logs will go to the console, which Render captures.
    app.logger.setLevel(logging.DEBUG) 
    # Example: If you wanted ONLY app's DEBUG and above, and suppress library INFO/DEBUG:
    # logging.getLogger().setLevel(logging.WARNING) # Set root logger higher
    # app.logger.setLevel(logging.DEBUG) # Keep app logger at debug

    CORS(app) # Allow requests from frontend origin


    # =============================================================
    # === Define Available Modes Structure ===
    # =============================================================
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
    # =============================================================

    try:
        default_active_share_sum = sum(
            mode.get('defaultBaselineShare', 0) for mode in AVAILABLE_MODES if mode.get('isDefaultActive')
        )
        if abs(default_active_share_sum - 100.0) > 0.01 and default_active_share_sum > 0:
             app.logger.warning(f"Sum of 'defaultBaselineShare' for default active modes is {default_active_share_sum:.2f}, not 100.00")
        elif default_active_share_sum == 0 and any(mode.get('isDefaultActive') for mode in AVAILABLE_MODES):
             app.logger.warning("No default shares assigned for default active modes.")
        else:
            app.logger.info(f"Default baseline shares sum validated ({default_active_share_sum:.1f}%).") # Changed from print
    except Exception as share_val_err:
        app.logger.error(f"Error validating default baseline shares: {share_val_err}")
    # =============================================================

    DEFAULT_PARKING_COST = 5000
    DEFAULT_SHOW_RATE = 100

except Exception as startup_error:
    # These print statements are kept for critical startup failures before logger might be fully available
    print("[CRITICAL_STARTUP_ERROR] !!! AN ERROR OCCURRED DURING APP STARTUP (Caught by main try-except) !!!")
    print(f"[CRITICAL_STARTUP_ERROR] Error Type: {type(startup_error).__name__}")
    print(f"[CRITICAL_STARTUP_ERROR] Error Message: {startup_error}")
    print("\n[CRITICAL_STARTUP_ERROR] --- Traceback ---")
    print(traceback.format_exc())
    print("[CRITICAL_STARTUP_ERROR] -----------------\n")
    _startup_failed = True
    # Minimal app to avoid secondary errors if 'app' was not defined, or if logger setup failed
    if 'app' not in globals() or not isinstance(app, Flask):
        app = Flask(__name__) 
        CORS(app)
else:
    _startup_failed = False
    app.logger.info("Flask app initialization and initial setup successful.")


@app.route('/')
def home():
    if _startup_failed: return "Error: Flask app failed to initialize. Check server logs.", 500
    return "SEA MOVES API (v3 - Dynamic Modes) is running."

@app.route('/api/modes/available', methods=['GET'])
def get_available_modes():
    if _startup_failed:
        app.logger.error("/api/modes/available: Access attempted but startup failed flag is True.")
        return jsonify({"error": "Flask app failed to initialize properly."}), 500
    try:
        if 'AVAILABLE_MODES' not in globals() or not isinstance(AVAILABLE_MODES, list):
             app.logger.critical("CRITICAL (get_available_modes): AVAILABLE_MODES not defined or invalid.")
             return jsonify({"error": "AVAILABLE_MODES structure not defined correctly on server."}), 500
        # app.logger.debug(f"/api/modes/available: Serving {len(AVAILABLE_MODES)} modes.") # If needed for verbose debugging
        return jsonify(AVAILABLE_MODES), 200
    except Exception as e:
        app.logger.exception("Error in /api/modes/available") # exc_info=True is implicit with .exception
        return jsonify({"error": "Internal server error fetching available modes."}), 500

@app.route('/api/calculate', methods=['POST'])
def calculate():
    if _startup_failed:
        app.logger.error("/api/calculate: Access attempted but startup failed flag is True.")
        return jsonify({"error": "Flask app failed to initialize properly."}), 500
    
    # app.logger.debug(f"CALCULATE API: Received request. Headers: {request.headers}") # Optional: for detailed debugging

    try:
        data = request.get_json()
        if not data:
            app.logger.warning("CALCULATE API: Received empty or invalid JSON payload.")
            return jsonify({"error": "Invalid JSON payload"}), 400
        
        # app.logger.debug(f"CALCULATE API: Received data: {data}") # Very verbose, enable if needed

        active_mode_keys = data.get('activeModeKeys')
        mode_customizations = data.get('modeCustomizations', {})
        input_parameters = data.get('inputParameters', {})
        mode_shares_input = input_parameters.get('modeShares', {})
        population_per_year = input_parameters.get('population_per_year')
        parking_supply_per_year = input_parameters.get('parking_supply_per_year')
        
        current_default_parking_cost = DEFAULT_PARKING_COST if 'DEFAULT_PARKING_COST' in globals() else 5000
        current_default_show_rate = DEFAULT_SHOW_RATE if 'DEFAULT_SHOW_RATE' in globals() else 100

        parking_cost_per_space = input_parameters.get('parking_cost_per_space', current_default_parking_cost)
        show_rate_percent = input_parameters.get('show_rate_percent', current_default_show_rate)
        
        num_years = input_parameters.get('num_years', len(population_per_year) if isinstance(population_per_year, list) else 0)

        # --- Validation ---
        if not isinstance(active_mode_keys, list) or not active_mode_keys:
            app.logger.warning(f"VALIDATION FAIL (calculate): 'activeModeKeys' must be a non-empty list. Received: {active_mode_keys}")
            return jsonify({"error": "'activeModeKeys' must be a non-empty list"}), 400
        if not isinstance(mode_customizations, dict):
            app.logger.warning(f"VALIDATION FAIL (calculate): 'modeCustomizations' must be an object. Received: {mode_customizations}")
            return jsonify({"error": "'modeCustomizations' must be an object"}), 400
        
        if not population_per_year or not isinstance(population_per_year, list):
            app.logger.warning("VALIDATION FAIL (calculate): 'population_per_year' is missing or not a list.")
            return jsonify({"error": "'population_per_year' is missing or not a list"}), 400

        calculated_num_years = len(population_per_year)
        if num_years != calculated_num_years :
             app.logger.info(f"Num_years mismatch (calculate): passed {num_years}, calculated from pop_per_year {calculated_num_years}. Using calculated.")
        num_years = calculated_num_years 

        if parking_supply_per_year and len(parking_supply_per_year) != num_years: 
            app.logger.warning(f"VALIDATION FAIL (calculate): Data length mismatch: Pop ({num_years}) vs Parking Supply ({len(parking_supply_per_year)}).")
            return jsonify({"error": f"Data length mismatch: Population ({num_years}) vs Parking Supply ({len(parking_supply_per_year)})."}), 400

        if 'AVAILABLE_MODES_DICT' not in globals():
             app.logger.critical("CRITICAL (validation in calculate): AVAILABLE_MODES_DICT not defined.")
             return jsonify({"error": "Server configuration error: Mode dictionary unavailable."}), 500

        unknown_keys = [k for k in active_mode_keys if k not in AVAILABLE_MODES_DICT]
        if unknown_keys:
            app.logger.warning(f"VALIDATION FAIL (calculate): Unknown mode keys: {', '.join(unknown_keys)}. Active: {active_mode_keys}")
            return jsonify({"error": f"Unknown mode keys provided: {', '.join(unknown_keys)}"}), 400
        
        share_keys = list(mode_shares_input.keys())
        if set(share_keys) != set(active_mode_keys):
            app.logger.warning(f"VALIDATION FAIL (calculate): Mismatch between keys in 'activeModeKeys' ({sorted(active_mode_keys)}) and 'modeShares' ({sorted(share_keys)}).")
            return jsonify({"error": "Mismatch between keys in 'activeModeKeys' and 'modeShares'"}), 400

        total_share = 0
        for key in active_mode_keys: 
            share_val = mode_shares_input.get(key) 
            if share_val is None: 
                app.logger.warning(f"VALIDATION FAIL (calculate): Share for '{key}' missing. mode_shares_input: {mode_shares_input}")
                return jsonify({"error": f"Share value for active mode '{key}' is missing from modeShares input."}), 400
            if not isinstance(share_val, (int, float)) or math.isnan(share_val) or share_val < 0 or share_val > 100:
                app.logger.warning(f"VALIDATION FAIL (calculate): Invalid share for '{key}': {share_val}. Payload: {mode_shares_input}")
                return jsonify({"error": f"Invalid share value for mode '{key}': {share_val}"}), 400
            total_share += share_val
        
        if not (99.9 < total_share < 100.1): 
             app.logger.warning(f"VALIDATION FAIL (calculate): 'modeShares' sum is {total_share:.2f}. Active: {active_mode_keys}. Payload: {mode_shares_input}")
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

        # app.logger.debug("Calling calculation functions...") # Optional debug log
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
        # app.logger.debug("Calculation functions completed.") # Optional debug log

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
        app.logger.info("Successful calculation response sent.") # Good to log successful completion
        return jsonify(response), 200

    except ValueError as ve:
         app.logger.warning(f"CALCULATE API - Value Error: {ve}", exc_info=True) # Use warning for client errors, exc_info for traceback
         return jsonify({"error": str(ve)}), 400
    except Exception as e:
         app.logger.exception("CALCULATE API - Unexpected error") # .exception implies ERROR level and exc_info=True
         return jsonify({"error": "Internal server error during calculation."}), 500


if __name__ == '__main__':
    # These print statements are fine for local development and won't run on Render.
    print("[DEV_SERVER_LOG] Running in __main__ (local dev server)")
    if not _startup_failed:
        print("[DEV_SERVER_LOG] Starting Flask Development Server (local dev)...")
        if 'app' in globals() and isinstance(app, Flask):
             app.run(debug=True, port=5001) # debug=True enables Flask's interactive debugger & reloader
        else:
             print("[DEV_SERVER_LOG] !!! Critical Error: 'app' variable not defined. Cannot run server. !!!")
    else:
        print("[DEV_SERVER_LOG] !!! Flask app startup failed (local dev). Server will not run. !!!")
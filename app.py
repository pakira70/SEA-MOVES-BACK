# app.py - COMPLETE, CHECKED, and CORRECTED for Dynamic Modes

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
    # Assumes calculations.py has been updated as per previous steps
    from calculations import (
        # normalize_and_balance_shares, # No longer used
        calculate_daily_trips,
        analyze_parking,
        create_summary_table,
    )
    print("--- Imports from calculations.py successful (assuming refactored) ---")

    # === Initialize Flask App and CORS ===
    print("--- Initializing Flask App ---")
    app = Flask(__name__)
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO)

    CORS(app) # Allow requests from frontend origin
    print("--- Flask App Initialized Successfully ---")


    # =============================================================
    # === Define Available Modes Structure ===
    # =============================================================
    # !! REVIEW and ADJUST defaultBaselineShare values below !!
    # They MUST sum to 100 for all modes where isDefaultActive is True.
    AVAILABLE_MODES = [
      # --- Personal Vehicles ---
      {
        "key": "DRIVE", "defaultName": "Drive (Gas/Other)", "defaultColor": "#D32F2F", "category": "Personal Vehicles",
        "flags": { "affects_parking": True, "affects_emissions": True, "affects_cost": True },
        "parking_factor_per_person": 1.0, "isDefaultActive": True, "defaultBaselineShare": 65.0 # *** ADJUST THIS ***
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
         "parking_factor_per_person": 0.5, "isDefaultActive": True, "defaultBaselineShare": 5.0 # *** ADJUST THIS ***
       },
       {
         "key": "VANPOOL", "defaultName": "Vanpool", "defaultColor": "#4E342E", "category": "Carpool & Vanpool",
         "flags": { "affects_parking": True, "affects_emissions": True, "affects_cost": True },
         "parking_factor_per_person": 0.2, "isDefaultActive": False, "defaultBaselineShare": 0.0
       },
       # --- Micromobility & Active Modes ---
       {
        "key": "BIKE", "defaultName": "Bike", "defaultColor": "#0288D1", "category": "Micromobility & Active",
        "flags": { "affects_parking": False, "affects_emissions": False, "affects_cost": False },
        "parking_factor_per_person": 0.0, "isDefaultActive": True, "defaultBaselineShare": 3.0 # *** ADJUST THIS ***
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
        "parking_factor_per_person": 0.0, "isDefaultActive": True, "defaultBaselineShare": 7.0 # *** ADJUST THIS ***
      },
       {
        "key": "REGIONAL_TRAIL", "defaultName": "Regional Trail (Walk/Bike)", "defaultColor": "#689F38", "category": "Micromobility & Active",
        "flags": { "affects_parking": False, "affects_emissions": False, "affects_cost": False },
        "parking_factor_per_person": 0.0, "isDefaultActive": False, "defaultBaselineShare": 0.0
      },
       # --- Transit ---
       {
        "key": "BUS", "defaultName": "Bus", "defaultColor": "#F57C00", "category": "Transit",
        "flags": { "affects_parking": False, "affects_emissions": True, "affects_cost": True },
        "parking_factor_per_person": 0.0, "isDefaultActive": True, "defaultBaselineShare": 15.0 # *** ADJUST THIS ***
      },
      {
        "key": "TRAIN", "defaultName": "Train (Commuter/Heavy Rail)", "defaultColor": "#5D4037", "category": "Transit",
        "flags": { "affects_parking": False, "affects_emissions": True, "affects_cost": True },
        "parking_factor_per_person": 0.0, "isDefaultActive": False, "defaultBaselineShare": 0.0
      },
      {
        "key": "LIGHT_RAIL", "defaultName": "Light Rail", "defaultColor": "#7E57C2", "category": "Transit",
        "flags": { "affects_parking": False, "affects_emissions": False, "affects_cost": True },
        "parking_factor_per_person": 0.0, "isDefaultActive": True, "defaultBaselineShare": 5.0 # *** ADJUST THIS ***
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
    # Create a dictionary for quick lookups by key
    AVAILABLE_MODES_DICT = {mode['key']: mode for mode in AVAILABLE_MODES}
    # =============================================================

    # === Validate Default Baseline Shares Sum ===
    try:
        default_active_share_sum = sum(
            mode.get('defaultBaselineShare', 0) for mode in AVAILABLE_MODES if mode.get('isDefaultActive')
        )
        # Use a small tolerance for floating point comparison
        if abs(default_active_share_sum - 100.0) > 0.01 and default_active_share_sum > 0:
             print("\n!!! WARNING: Sum of 'defaultBaselineShare' for modes where 'isDefaultActive' is true does not equal 100 !!!")
             print(f"    Calculated Sum: {default_active_share_sum:.2f}")
             print("    Please adjust 'defaultBaselineShare' values in AVAILABLE_MODES definition in app.py.")
             # Consider raising an error if strict enforcement is needed:
             # raise ValueError("Default baseline shares must sum to 100 for default active modes.")
        elif default_active_share_sum == 0 and any(mode.get('isDefaultActive') for mode in AVAILABLE_MODES):
             print("\n!!! WARNING: No default shares assigned for default active modes. Baseline calculation might be incorrect. !!!")
             print("    Please assign non-zero 'defaultBaselineShare' values in AVAILABLE_MODES definition in app.py.")
        else:
            print(f"--- Default baseline shares sum validated ({default_active_share_sum:.1f}%) ---")

    except Exception as share_val_err:
        print(f"\n!!! Error validating default baseline shares: {share_val_err} !!!")
        # Decide how to handle this - warning or raise?

    # =============================================================


    # === Default Input Values ===
    DEFAULT_PARKING_COST = 5000
    DEFAULT_SHOW_RATE = 100
    # Default mode shares are now implicitly defined by AVAILABLE_MODES


# === Handle Startup Errors ===
# Wrap the entire setup in try/except
except Exception as startup_error:
    print("\n!!! AN ERROR OCCURRED DURING APP STARTUP (Possibly during mode definition/validation) !!!")
    print(f"Error Type: {type(startup_error).__name__}")
    print(f"Error Message: {startup_error}")
    print("\n--- Traceback ---")
    print(traceback.format_exc())
    print("-----------------\n")
    _startup_failed = True
    # Define app minimally so routes don't cause secondary errors, but indicate failure
    app = Flask(__name__)
    CORS(app)
else:
    _startup_failed = False


# === Routes ===

@app.route('/')
def home():
    """ Basic route to confirm API is running. """
    if _startup_failed:
         return "Error: Flask app failed to initialize during startup. Check server logs.", 500
    return "SEA MOVES API (v3 - Dynamic Modes) is running."


@app.route('/api/modes/available', methods=['GET'])
def get_available_modes():
    """ Returns the list of predefined modes the backend supports. """
    if _startup_failed:
         return jsonify({"error": "Flask app failed to initialize during startup. Check server logs."}), 500
    try:
        # Ensure AVAILABLE_MODES was defined correctly
        if 'AVAILABLE_MODES' not in globals() or not isinstance(AVAILABLE_MODES, list):
             raise ValueError("AVAILABLE_MODES structure not defined correctly.")
        return jsonify(AVAILABLE_MODES), 200
    except Exception as e:
        # Use app logger if available, otherwise print
        log_target = app.logger if '_startup_failed' in globals() and not _startup_failed else print
        log_target.error(f"Error in /api/modes/available: {e}\n{traceback.format_exc()}")
        return jsonify({"error": "Internal server error fetching available modes."}), 500


@app.route('/api/calculate', methods=['POST'])
def calculate():
    """ Main calculation endpoint - Uses Refactored calculations.py """
    if _startup_failed:
         return jsonify({"error": "Flask app failed to initialize during startup. Check server logs."}), 500

    try:
        data = request.get_json()
        if not data:
            app.logger.warning("Received empty or invalid JSON payload.")
            return jsonify({"error": "Invalid JSON payload"}), 400

        app.logger.info("Received calculation request.")

        # --- Input Extraction ---
        active_mode_keys = data.get('activeModeKeys')
        mode_customizations = data.get('modeCustomizations', {})
        input_parameters = data.get('inputParameters', {})
        # --- Core Params ---
        mode_shares_input = input_parameters.get('modeShares', {})
        population_per_year = input_parameters.get('population_per_year')
        parking_supply_per_year = input_parameters.get('parking_supply_per_year')
        parking_cost_per_space = input_parameters.get('parking_cost_per_space', DEFAULT_PARKING_COST)
        show_rate_percent = input_parameters.get('show_rate_percent', DEFAULT_SHOW_RATE)
        num_years = input_parameters.get('num_years', len(population_per_year) if isinstance(population_per_year, list) else 0)

        # --- Validation ---
        # Basic Type/Existence Checks
        if not isinstance(active_mode_keys, list) or not active_mode_keys: return jsonify({"error": "'activeModeKeys' must be a non-empty list"}), 400
        if not isinstance(mode_customizations, dict): return jsonify({"error": "'modeCustomizations' must be an object"}), 400
        if not isinstance(input_parameters, dict): return jsonify({"error": "'inputParameters' must be an object"}), 400
        if not isinstance(mode_shares_input, dict): return jsonify({"error": "'inputParameters.modeShares' must be an object"}), 400
        if not isinstance(population_per_year, list) or not population_per_year: return jsonify({"error": "'inputParameters.population_per_year' must be a non-empty list"}), 400
        if not isinstance(parking_supply_per_year, list) or not parking_supply_per_year: return jsonify({"error": "'inputParameters.parking_supply_per_year' must be a non-empty list"}), 400
        if not isinstance(parking_cost_per_space, (int, float)) or parking_cost_per_space < 0: return jsonify({"error": "'inputParameters.parking_cost_per_space' must be a non-negative number"}), 400
        if not isinstance(show_rate_percent, (int, float)) or not (0 <= show_rate_percent <= 100): return jsonify({"error": "'inputParameters.show_rate_percent' must be between 0 and 100"}), 400

        # Length Checks
        calculated_num_years = len(population_per_year)
        if num_years != calculated_num_years: app.logger.warning(f"Passed num_years ({num_years}) differs from population length ({calculated_num_years}). Using population length.")
        num_years = calculated_num_years # Use length from actual data
        if len(parking_supply_per_year) != num_years: return jsonify({"error": f"Data length mismatch: Population ({num_years}) vs Parking Supply ({len(parking_supply_per_year)})."}), 400

        # Mode Key / Share Validation
        unknown_keys = [k for k in active_mode_keys if k not in AVAILABLE_MODES_DICT]
        if unknown_keys: return jsonify({"error": f"Unknown mode keys provided: {', '.join(unknown_keys)}"}), 400
        share_keys = list(mode_shares_input.keys())
        if sorted(share_keys) != sorted(active_mode_keys): return jsonify({"error": "Mismatch between keys in 'activeModeKeys' and 'modeShares'"}), 400

        # Share Value and Sum Validation
        total_share = 0
        for key in active_mode_keys:
            share_val = mode_shares_input.get(key)
            if not isinstance(share_val, (int, float)) or math.isnan(share_val) or share_val < 0 or share_val > 100:
                return jsonify({"error": f"Invalid share value for mode '{key}': {share_val}"}), 400
            total_share += share_val
        if not (99.99 < total_share < 100.01): # Use tighter tolerance here
             return jsonify({"error": f"Input 'modeShares' for active modes must sum to 100 (received {total_share:.2f})"}), 400
        # --- End Validation ---


        # --- Create Active Mode Details for Calculation ---
        active_mode_info = {}
        for key in active_mode_keys:
             base_mode = AVAILABLE_MODES_DICT[key]
             custom = mode_customizations.get(key, {})
             active_mode_info[key] = {
                 "key": key,
                 "name": custom.get("name", base_mode["defaultName"]),
                 "color": custom.get("color", base_mode["defaultColor"]),
                 "flags": base_mode["flags"],
                 "parking_factor_per_person": base_mode.get("parking_factor_per_person", 0.0)
             }

        # --- Core Calculations ---
        app.logger.info("Calling calculation functions...")
        processed_mode_shares = mode_shares_input # Use validated input shares

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
            years=years_for_table,
            population_per_year=population_per_year,
            total_daily_trips_per_year=total_daily_trips_per_year,
            parking_demand_per_year=parking_demand_per_year,
            parking_supply_per_year=parking_supply_per_year,
            parking_shortfall_per_year=parking_shortfall_per_year
        )
        app.logger.info("Calculation functions completed.")

        # --- Prepare JSON Response ---
        response = {
            "years": years_for_table,
            "population_per_year": population_per_year,
            "parking": {
                "demand_per_year": parking_demand_per_year,
                "supply_per_year": parking_supply_per_year,
                "shortfall_per_year": parking_shortfall_per_year,
                "cost_per_year": parking_cost_per_year,
                "cost_per_space": parking_cost_per_space
            },
            "trips_per_mode_per_year": trips_per_mode_per_year,
            "processed_mode_shares": processed_mode_shares,
            "mode_details_for_display": active_mode_info,
            "summary_table": summary_table,
            "calculation_parameters": { "show_rate_percent": show_rate_percent }
            # TODO: Add overall results like emissions/cost if calculated
        }
        app.logger.info("Sending successful calculation response.")
        return jsonify(response), 200

    except ValueError as ve:
         app.logger.error(f"Value Error during calculation: {ve}")
         return jsonify({"error": str(ve)}), 400
    except Exception as e:
         app.logger.error(f"Unexpected error in /api/calculate: {e}\n{traceback.format_exc()}")
         return jsonify({"error": "Internal server error during calculation."}), 500


# === Run Instruction ===
if __name__ == '__main__':
    # Only try to run the app if the startup didn't fail
    if not _startup_failed:
        print("--- Starting Flask Development Server (v3 - Dynamic Modes) ---")
        # Check 'app' exists before running
        if 'app' in globals() and isinstance(app, Flask):
             app.run(debug=True, port=5001) # Ensure port doesn't conflict
        else:
             print("!!! Critical Error: 'app' variable not defined or invalid type. Cannot run server. !!!")
    else:
        print("!!! Flask app startup failed due to errors printed above. Server will not run. !!!")
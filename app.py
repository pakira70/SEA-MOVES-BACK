# app.py - Added try/except for startup errors

# === ADD TRY BLOCK HERE ===
try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    import traceback
    import numpy as np # Keep import
    import sys # Needed for sys.exit() in except block

    print("--- Attempting Imports ---") # Debug print

    # === Import calculation functions ===
    # This import might fail if calculations.py has an error
    from calculations import (
        normalize_and_balance_shares,
        calculate_daily_trips,
        analyze_parking,
        create_summary_table,
        BASELINE_MODE_SHARES,
        MODES
    )
    print("--- Imports from calculations.py successful ---") # Debug print

    # === Initialize Flask App and CORS ===
    print("--- Initializing Flask App ---") # Debug print
    app = Flask(__name__)
    CORS(app) # Allow requests from frontend origin
    print("--- Flask App Initialized Successfully ---") # Debug print

    # === Default Input Values ===
    DEFAULT_PARKING_COST = 5000
    DEFAULT_SHOW_RATE = 100

# === ADD EXCEPT BLOCK HERE ===
except Exception as startup_error:
    print("\n!!! AN ERROR OCCURRED DURING APP STARTUP !!!")
    print(f"Error Type: {type(startup_error).__name__}")
    print(f"Error Message: {startup_error}")
    print("\n--- Traceback ---")
    print(traceback.format_exc())
    print("-----------------\n")
    # Exit explicitly so the script doesn't continue if setup failed
    # Set a global flag or variable to indicate failure
    _startup_failed = True
    # Optional: sys.exit(1) # This would terminate the script immediately

else:
    # If try block succeeded without exception, set flag to False
    _startup_failed = False


# === Routes (Defined regardless, but check _startup_failed) ===

@app.route('/')
def home():
    """ Basic route to confirm API is running. """
    if _startup_failed:
         return "Error: Flask app failed to initialize during startup.", 500
    return "SEA MOVES API (v2 - Arrays/ShowRate) is running."

@app.route('/api/calculate', methods=['POST'])
def calculate():
    """ Main endpoint """
    if _startup_failed:
         return jsonify({"error": "Flask app failed to initialize during startup."}), 500

    try:
        data = request.get_json()
        if not data:
            app.logger.warning("Received empty or invalid JSON payload.")
            return jsonify({"error": "Invalid JSON payload"}), 400

        # --- Input Extraction ---
        mode_shares_input_raw = data.get('mode_shares_input', BASELINE_MODE_SHARES.copy())
        population_per_year = data.get('population_per_year')
        parking_supply_per_year = data.get('parking_supply_per_year')
        parking_cost_per_space = data.get('parking_cost_per_space', DEFAULT_PARKING_COST)
        show_rate_percent = data.get('show_rate_percent', DEFAULT_SHOW_RATE)
        changed_mode_key = data.get('changed_mode_key', None)
        new_value_percent_input = data.get('new_value_percent', None)

        # --- Input Validation ---
        if not isinstance(population_per_year, list) or not all(isinstance(p, (int, float)) and p >= 0 for p in population_per_year) or not population_per_year: return jsonify({"error": "Input 'population_per_year' must be a non-empty list of non-negative numbers"}), 400
        if not isinstance(parking_supply_per_year, list) or not all(isinstance(p, (int, float)) and p >= 0 for p in parking_supply_per_year) or not parking_supply_per_year: return jsonify({"error": "Input 'parking_supply_per_year' must be a non-empty list of non-negative numbers"}), 400
        num_years = len(population_per_year)
        if len(parking_supply_per_year) != num_years: return jsonify({"error": f"Data length mismatch: Population ({num_years}) vs Parking Supply ({len(parking_supply_per_year)})."}), 400
        if not isinstance(parking_cost_per_space, (int, float)) or parking_cost_per_space < 0: return jsonify({"error": "Input 'parking_cost_per_space' must be a non-negative number"}), 400
        if not isinstance(show_rate_percent, (int, float)) or not (0 <= show_rate_percent <= 100): return jsonify({"error": "Input 'show_rate_percent' must be a number between 0 and 100"}), 400
        if not isinstance(mode_shares_input_raw, dict): return jsonify({"error": "Input 'mode_shares_input' must be an object (dictionary)"}), 400

        # --- Core Calculations ---
        processed_mode_shares = normalize_and_balance_shares(mode_shares_input_raw, changed_mode_key, new_value_percent_input)
        trips_per_mode_per_year, total_daily_trips_per_year = calculate_daily_trips(population_per_year, processed_mode_shares, show_rate_percent)
        parking_demand_per_year, parking_shortfall_per_year, parking_cost_per_year = analyze_parking(population_per_year, processed_mode_shares, parking_supply_per_year, parking_cost_per_space, show_rate_percent)
        years_for_table = list(range(1, num_years + 1))
        summary_table = create_summary_table(years_for_table, population_per_year, total_daily_trips_per_year, parking_demand_per_year, parking_supply_per_year, parking_shortfall_per_year)

        # --- Prepare JSON Response ---
        response = {
            "processed_mode_shares": processed_mode_shares,
            "population_per_year": population_per_year,
            "years": years_for_table,
            "trips_per_mode_per_year": trips_per_mode_per_year,
            "parking": {
                "demand_per_year": parking_demand_per_year,
                "supply_per_year": parking_supply_per_year,
                "shortfall_per_year": parking_shortfall_per_year,
                "cost_per_year": parking_cost_per_year,
                "cost_per_space": parking_cost_per_space
                },
            "summary_table": summary_table,
            "calculation_parameters": {
                 "show_rate_percent": show_rate_percent
            }
        }
        return jsonify(response), 200

    except ValueError as ve: # Catch specific ValueErrors from calculations
         # Use app logger if app was initialized, otherwise print
         if not _startup_failed and 'app' in globals():
             app.logger.error(f"Value Error during calculation: {ve}")
         else:
             print(f"Value Error during calculation (app not fully initialized): {ve}")
         return jsonify({"error": str(ve)}), 400
    except Exception as e:
        if not _startup_failed and 'app' in globals():
            app.logger.error(f"Unexpected error in /api/calculate: {e}\n{traceback.format_exc()}")
        else:
             print(f"Unexpected error in /api/calculate (app not fully initialized): {e}\n{traceback.format_exc()}")
        return jsonify({"error": "Internal server error during calculation."}), 500

# === Run Instruction ===
if __name__ == '__main__':
    # Only try to run the app if the startup didn't fail
    if not _startup_failed:
        print("--- Starting Flask Development Server ---")
        # Make sure debug=True is suitable for your environment
        # Note: app might still be undefined if error happened between try/except and this block
        # Adding another check for safety
        if 'app' in globals():
             app.run(debug=True, port=5001)
        else:
             print("!!! Critical Error: 'app' variable not defined despite startup success flag. Cannot run server. !!!")

    else:
        print("!!! Flask app startup failed due to errors printed above. Server will not run. !!!")
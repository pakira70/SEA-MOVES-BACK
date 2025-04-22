# app.py

from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback

# === Import calculation functions ===
# NOTE: Ensure 'normalize_and_balance_shares' is defined in calculations.py
from calculations import (
    normalize_and_balance_shares, # <-- Use the new combined function
    calculate_daily_trips,
    analyze_parking,
    create_summary_table,
    BASELINE_MODE_SHARES,
    MODES
)

# === Initialize Flask App and CORS ===
app = Flask(__name__)
CORS(app) # Allow requests from frontend origin

# === Default Input Values ===
DEFAULT_POPULATION = [10000, 10200, 10400, 10600, 10800]
DEFAULT_PARKING_SUPPLY = [5000, 5100, 5100, 5200, 5200]
DEFAULT_PARKING_COST = 5000

# === Routes ===

@app.route('/')
def home():
    """ Basic route to confirm API is running. """
    return "NUC Mobility Model API is running."

@app.route('/api/calculate', methods=['POST'])
def calculate():
    """
    Main endpoint to process mobility model inputs and return calculated outputs.
    Handles mode share balancing using normalize_and_balance_shares.
    """
    try:
        data = request.get_json()
        if not data:
            app.logger.warning("Received empty or invalid JSON payload.")
            return jsonify({"error": "Invalid JSON payload"}), 400

        # --- Input Extraction ---
        mode_shares_input_raw = data.get('mode_shares_input', BASELINE_MODE_SHARES.copy())
        population_per_year = data.get('population_per_year', DEFAULT_POPULATION)
        parking_supply_per_year = data.get('parking_supply_per_year', DEFAULT_PARKING_SUPPLY)
        parking_cost_per_space = data.get('parking_cost_per_space', DEFAULT_PARKING_COST)
        changed_mode_key = data.get('changed_mode_key', None)
        new_value_percent_input = data.get('new_value_percent', None) # Can be number or null from JSON

        # --- Input Validation ---
        if not isinstance(population_per_year, list) or not all(isinstance(p, (int, float)) for p in population_per_year) or not population_per_year:
             return jsonify({"error": "Input 'population_per_year' must be a non-empty list of numbers"}), 400
        if not isinstance(parking_supply_per_year, list) or not all(isinstance(p, (int, float)) for p in parking_supply_per_year):
             return jsonify({"error": "Input 'parking_supply_per_year' must be a list of numbers"}), 400
        if not isinstance(parking_cost_per_space, (int, float)) or parking_cost_per_space < 0:
             return jsonify({"error": "Input 'parking_cost_per_space' must be a non-negative number"}), 400
        num_years = len(population_per_year)
        if len(parking_supply_per_year) != num_years:
             return jsonify({"error": f"Data length mismatch: Population ({num_years}) vs Parking Supply ({len(parking_supply_per_year)})."}), 400
        # --- End Validation ---

        # --- Core Calculations ---

        # === Step 1: Normalize & Balance Shares ===
        # Directly call the primary function, passing necessary info
        processed_mode_shares = normalize_and_balance_shares(
            input_shares=mode_shares_input_raw,
            changed_mode=changed_mode_key,
            new_value=new_value_percent_input
        )
        # === End Step 1 ===

        # === Step 2: Calculate Trips ===
        trips_per_mode_per_year, total_daily_trips_per_year = calculate_daily_trips(
            population_per_year,
            processed_mode_shares # Use final shares
        )
        # === Step 3: Analyze Parking ===
        parking_demand_per_year, parking_shortfall_per_year, parking_cost_per_year = analyze_parking(
            population_per_year,
            processed_mode_shares, # Use final shares
            parking_supply_per_year,
            parking_cost_per_space
        )
        # === Step 4: Prepare Summary Table ===
        years = list(range(1, num_years + 1))
        summary_table = create_summary_table(
            years, population_per_year, total_daily_trips_per_year,
            parking_demand_per_year, parking_supply_per_year, parking_shortfall_per_year
        )

        # --- Prepare JSON Response ---
        response = {
            "processed_mode_shares": processed_mode_shares, # Send final shares
            "years": years, "population_per_year": population_per_year,
            "trips_per_mode_per_year": trips_per_mode_per_year,
            "parking": {"demand_per_year": parking_demand_per_year, "supply_per_year": parking_supply_per_year, "shortfall_per_year": parking_shortfall_per_year, "cost_per_year": parking_cost_per_year, "cost_per_space": parking_cost_per_space},
            "summary_table": summary_table
        }
        return jsonify(response), 200

    except ValueError as ve:
         app.logger.error(f"Value Error: {ve}")
         return jsonify({"error": str(ve)}), 400
    except Exception as e:
        app.logger.error(f"Unexpected error: {e}\n{traceback.format_exc()}")
        return jsonify({"error": "Internal server error during calculation."}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
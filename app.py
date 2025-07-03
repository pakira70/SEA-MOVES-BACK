# app.py - CORRECTED to include processed_mode_shares in the response
import traceback
import logging
import math
from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np

from calculations import (
    calculate_daily_trips,
    analyze_parking,
    create_summary_table,
    analyze_shuttle_costs,
)

# --- Main App Setup ---
try:
    app = Flask(__name__)
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.DEBUG)
    CORS(app)

    # --- Global Constants and Mode Definitions ---
    AVAILABLE_MODES = [
      {"key": "DRIVE", "defaultName": "Drive", "defaultColor": "#D32F2F", "category": "Personal Vehicles", "flags": { "affects_parking": True, "affects_emissions": True, "affects_cost": True }, "parking_factor_per_person": 1.0, "isDefaultActive": True, "defaultBaselineShare": 71.0},
      {"key": "DROPOFF", "defaultName": "Drop-off", "defaultColor": "#455A64", "category": "Personal Transport", "flags": { "affects_parking": False, "affects_emissions": True, "affects_cost": True }, "parking_factor_per_person": 0.0, "isDefaultActive": True, "defaultBaselineShare": 5.0},
      {"key": "CARPOOL", "defaultName": "Carpool", "defaultColor": "#FF6F00", "category": "Carpool & Vanpool", "flags": { "affects_parking": True, "affects_emissions": True, "affects_cost": True }, "parking_factor_per_person": 0.5, "isDefaultActive": True, "defaultBaselineShare": 1.0},
      {"key": "VANPOOL", "defaultName": "Vanpool", "defaultColor": "#4E342E", "category": "Carpool & Vanpool", "flags": { "affects_parking": True, "affects_emissions": True, "affects_cost": True }, "parking_factor_per_person": 0.2, "isDefaultActive": True, "defaultBaselineShare": 1.0},
      {"key": "BIKE", "defaultName": "Bike", "defaultColor": "#0288D1", "category": "Micromobility & Active", "flags": { "affects_parking": False, "affects_emissions": False, "affects_cost": False }, "parking_factor_per_person": 0.0, "isDefaultActive": True, "defaultBaselineShare": 1.0},
      {"key": "WALK", "defaultName": "Walk", "defaultColor": "#388E3C", "category": "Micromobility & Active", "flags": { "affects_parking": False, "affects_emissions": False, "affects_cost": False }, "parking_factor_per_person": 0.0, "isDefaultActive": True, "defaultBaselineShare": 2.0},
      {"key": "TRANSIT", "defaultName": "Transit", "defaultColor": "#F57C00", "category": "Transit", "flags": { "affects_parking": False, "affects_emissions": True, "affects_cost": True }, "parking_factor_per_person": 0.0, "isDefaultActive": True, "defaultBaselineShare": 19.0},
      # (Other non-default modes are here)
    ]
    AVAILABLE_MODES_DICT = {mode['key']: mode for mode in AVAILABLE_MODES}
    _startup_failed = False
except Exception as e:
    print("CRITICAL ERROR DURING INITIAL APP SETUP", e)
    _startup_failed = True

# --- Routes ---
@app.route('/')
def home():
    return "SEA MOVES API is running."

@app.route('/api/modes/available', methods=['GET'])
def get_available_modes():
    return jsonify(AVAILABLE_MODES), 200

# This helper function was missing a return value.
def _run_calculation_logic(params, active_mode_info):
    trips_per_mode, total_trips = calculate_daily_trips(
        params['population_per_year'], params['modeShares'], params['show_rate_percent'])
    
    parking_demand, parking_shortfall, parking_cost = analyze_parking(
        params['population_per_year'], params['modeShares'], params['parking_supply_per_year'],
        params['parking_cost_per_space'], params['show_rate_percent'], active_mode_info)
    
    # THE FIX IS HERE: Add 'processed_mode_shares' back into the returned dictionary.
    return {
        "trips_per_mode_per_year": trips_per_mode,
        "total_daily_trips_per_year": total_trips,
        "processed_mode_shares": params['modeShares'], # <-- THIS LINE WAS MISSING
        "parking": {
            "demand_per_year": parking_demand,
            "supply_per_year": params['parking_supply_per_year'],
            "shortfall_per_year": parking_shortfall,
            "cost_per_year": parking_cost,
            "cost_per_space": params['parking_cost_per_space']
        }
    }

@app.route('/api/calculate', methods=['POST'])
def calculate():
    try:
        data = request.get_json()
        if not data: return jsonify({"error": "Invalid JSON payload"}), 400

        baseline_input_params = data.get('baselineInputParameters', {})
        scenario_input_params = data.get('scenarioInputParameters', {})
        shuttle_parameters = data.get('shuttleParameters', {})
        mode_customizations = data.get('modeCustomizations', {})
        
        active_mode_keys = list(scenario_input_params.get('modeShares', {}).keys())
        active_mode_info = {
            key: {
                "key": key,
                "name": mode_customizations.get(key, {}).get("name", AVAILABLE_MODES_DICT.get(key, {}).get("defaultName", key)),
                "color": mode_customizations.get(key, {}).get("color", AVAILABLE_MODES_DICT.get(key, {}).get("defaultColor", "#cccccc")),
                "flags": AVAILABLE_MODES_DICT.get(key, {}).get("flags", {}),
                "parking_factor_per_person": AVAILABLE_MODES_DICT.get(key, {}).get("parking_factor_per_person", 0.0)
            } for key in active_mode_keys
        }

        baseline_results = _run_calculation_logic(baseline_input_params, active_mode_info)
        scenario_results = _run_calculation_logic(scenario_input_params, active_mode_info)

        shuttle_results = analyze_shuttle_costs(
            baseline_drive_trips_per_year=baseline_results["trips_per_mode_per_year"].get("DRIVE", []),
            scenario_drive_trips_per_year=scenario_results["trips_per_mode_per_year"].get("DRIVE", []),
            shuttle_params=shuttle_parameters
        )

        response = {
            "baselineResults": baseline_results,
            "scenarioResults": scenario_results,
            "shuttleResults": shuttle_results,
            "mode_details_for_display": active_mode_info,
            "years": list(range(1, scenario_input_params.get('num_years', 0) + 1))
        }
        
        return jsonify(response), 200

    except Exception as e:
        app.logger.exception("CALCULATE API - Unexpected error")
        return jsonify({"error": "Internal server error during calculation."}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
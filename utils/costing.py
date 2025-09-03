def machine_cost_per_hour(capex_eur, lifetime_yrs, utilization_pct, maintenance_pct, energy_eur_per_kwh, kwh_per_hour):
    hrs_per_year = 2000.0
    depreciation = capex_eur / (lifetime_yrs * hrs_per_year)
    maintenance  = (capex_eur * maintenance_pct) / (lifetime_yrs * hrs_per_year)
    energy = energy_eur_per_kwh * kwh_per_hour
    return (depreciation + maintenance + energy) / max(utilization_pct, 0.01)

def labor_cost_per_hour(hourly_rate, overhead_pct, margin_pct):
    return hourly_rate * (1.0 + overhead_pct) * (1.0 + margin_pct)

def part_cost(material_kg, price_eur_per_kg, process_time_h, machine_rate_eur_h, labor_time_h, labor_rate_eur_h):
    return (material_kg * price_eur_per_kg) + (process_time_h * machine_rate_eur_h) + (labor_time_h * labor_rate_eur_h)

def apply_scenario(rate, multiplier):
    return rate * multiplier

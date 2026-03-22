from datetime import datetime
from typing import List
from models import Vehicle, TcoParams, CalculationResult

class TCOEngine:
    @staticmethod
    def powertrain_from_fuel(fuel_type: str) -> str:
        return "EV" if fuel_type == "Elétrico" else "ICE"

    @staticmethod
    def calculate_isv(v: Vehicle) -> float:
        if not v.is_imported or v.fuel_type == "Elétrico":
            return 0.0
        age = max(0, datetime.now().year - v.year)
        base_cc = (v.engine_cc or 0) * 0.12
        base_co2 = (v.co2 or 0) * 60
        discount = 0.10 if age <= 1 else 0.52 if age <= 6 else 0.80
        isv = (base_cc + base_co2) * (1 - discount)
        return max(isv, 100.0)

    @staticmethod
    def default_depreciation_schedule_pct(hold_years: int) -> List[float]:
        base_15 = [10, 9, 8, 8, 8, 7, 7, 7, 6, 6, 5, 5, 5, 5, 4]
        if hold_years <= 15:
            return base_15[:hold_years]
        return base_15 + [4.0] * (hold_years - 15)

    @staticmethod
    def depreciation_resale_value(acquisition_cost: float, schedule_pct: List[float]) -> float:
        value = float(acquisition_cost)
        for pct in schedule_pct:
            rate = max(0.0, float(pct)) / 100.0
            annual_depr = float(acquisition_cost) * rate
            value = max(0.0, value - annual_depr)
        return max(0.0, value)

    @staticmethod
    def calculate_iuc(v: Vehicle) -> float:
        if v.fuel_type == "Elétrico":
            return 0.0
        cc_cost = 0.0
        cc = v.engine_cc or 0
        if v.year < 2007:
            if v.fuel_type == "Gasolina":
                if cc <= 1250: cc_cost = 32.0
                elif cc <= 1750: cc_cost = 64.0
                elif cc <= 2500: cc_cost = 158.0
                else: cc_cost = 400.0
            else:
                if cc <= 1500: cc_cost = 25.0
                elif cc <= 2000: cc_cost = 55.0
                elif cc <= 3000: cc_cost = 130.0
                else: cc_cost = 300.0
        else:
            if v.fuel_type == "Gasolina":
                if cc <= 1250: cc_cost = 30.0
                elif cc <= 1750: cc_cost = 60.0
                elif cc <= 2500: cc_cost = 120.0
                else: cc_cost = 400.0
            else:
                if cc <= 1500: cc_cost = 25.0
                elif cc <= 2000: cc_cost = 50.0
                elif cc <= 2500: cc_cost = 100.0
                else: cc_cost = 400.0
        co2_cost = 0.0
        if v.year >= 2007:
            co2 = (v.co2 or 0) * (0.9 if v.year > 2017 else 1.0)
            if co2 <= 120: co2_cost = 60.0
            elif co2 <= 180: co2_cost = 150.0
            elif co2 <= 250: co2_cost = 250.0
            else: co2_cost = 350.0
            if v.fuel_type == "Diesel":
                cc_cost += 20.0
        return cc_cost + co2_cost

    @staticmethod
    def calculate_insurance(v_value: float) -> float:
        return 150.0 + (v_value * 0.015)

    @staticmethod
    def maintenance_cost_year(v: Vehicle, age: int, km_accumulated: int, p: TcoParams) -> float:
        powertrain = TCOEngine.powertrain_from_fuel(v.fuel_type)
        annual_base = (100.0 if powertrain == "EV" else 180.0)
        age_factor = 1.0 + max(0, age - 3) * 0.10
        base_per_km = 0.015 if powertrain == "EV" else 0.025
        km_factor = 1.0 + max(0, km_accumulated - 100000) / 100000.0 * 0.50
        annual_variable = p.annual_km * base_per_km * km_factor
        return (annual_base * age_factor) + annual_variable

    @classmethod
    def run(cls, v: Vehicle, p: TcoParams) -> CalculationResult:
        v.validate()
        km_total_period = int(p.annual_km) * int(p.hold_years)
        km_end = int(v.km_current) + km_total_period
        isv = cls.calculate_isv(v)
        import_fees = (isv + 1000) if v.is_imported else 0.0
        acquisition_cost = float(v.price) + float(import_fees)
        current_value = acquisition_cost
        accumulated_costs = {"energy": 0.0, "maintenance": 0.0, "insurance_fiscality": 0.0, "tolls_parking": 0.0}
        base_depr_schedule = cls.default_depreciation_schedule_pct(int(p.hold_years))
        if p.depreciation_schedule_pct:
            custom = p.depreciation_schedule_pct[:int(p.hold_years)]
            full_schedule = custom + base_depr_schedule[len(custom):]
        else:
            full_schedule = base_depr_schedule
        full_schedule = [max(0.0, s + p.depreciation_schedule_bias_pct) for s in full_schedule]
        for year_idx in range(int(p.hold_years)):
            car_age = (datetime.now().year - v.year) + (year_idx + 1)
            km_accumulated = v.km_current + (p.annual_km * (year_idx + 1))
            rate_pct = full_schedule[year_idx] if year_idx < len(full_schedule) else 5.0
            value_start_of_year = current_value
            annual_depr = float(acquisition_cost) * (max(0.0, float(rate_pct)) / 100.0)
            current_value = max(0.0, current_value - annual_depr)
            insurance = cls.calculate_insurance(value_start_of_year)
            iuc = cls.calculate_iuc(v)
            inspection = p.fixed_costs.get("inspection", 30.0)
            accumulated_costs["insurance_fiscality"] += (insurance + iuc + inspection)
            maint = cls.maintenance_cost_year(v, car_age, km_accumulated, p)
            accumulated_costs["maintenance"] += maint
            real_cons = float(v.consumption) * (1.0 + float(p.real_cons_adj))
            fuel_price = float(p.fuel_prices.get(v.fuel_type, 1.70))
            qty = (real_cons / 100.0) * p.annual_km
            accumulated_costs["energy"] += (qty * fuel_price)
            accumulated_costs["tolls_parking"] += float(p.fixed_costs.get("tolls_parking", 0.0))
        resale_value = max(0.0, current_value)
        km_total = int(p.annual_km) * int(p.hold_years)
        real_cons_avg = float(v.consumption) * (1.0 + float(p.real_cons_adj))
        energy_qty_total = (real_cons_avg / 100.0) * km_total
        energy_unit = "kWh" if v.fuel_type == "Elétrico" else "L"
        total_cost = (acquisition_cost + accumulated_costs["energy"] + accumulated_costs["maintenance"] +
                      accumulated_costs["insurance_fiscality"] + accumulated_costs["tolls_parking"] - resale_value)
        cost_per_km = total_cost / km_total if km_total > 0 else 0.0
        breakdown = {
            "Aquisição": acquisition_cost, "Revenda (−)": -resale_value,
            "Energia/Combustível": accumulated_costs["energy"],
            "Portagens+Parqueamento": accumulated_costs["tolls_parking"],
            "Seguro+Fiscalidade": accumulated_costs["insurance_fiscality"],
            "Reparações+Manutenção": accumulated_costs["maintenance"],
        }
        return CalculationResult(
            vehicle_name=v.name, total_cost=float(total_cost), cost_per_km=float(cost_per_km),
            km_at_end=int(km_end), acquisition_cost=float(acquisition_cost), resale_value=float(resale_value),
            energy_cost=float(accumulated_costs["energy"]), energy_qty=float(energy_qty_total),
            energy_unit=energy_unit, tolls_parking_cost=float(accumulated_costs["tolls_parking"]),
            insurance_fiscality_cost=float(accumulated_costs["insurance_fiscality"]),
            maint_cost=float(accumulated_costs["maintenance"]), breakdown=breakdown
        )

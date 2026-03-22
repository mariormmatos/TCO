from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class Vehicle:
    id: str
    name: str
    price: float
    year: int
    km_current: int
    consumption: float
    fuel_type: str
    is_imported: bool
    co2: Optional[float] = 0.0
    engine_cc: Optional[int] = 0
    
    def validate(self):
        current_year = datetime.now().year
        if self.price < 0:
            raise ValueError("Preço inválido.")
        if self.year < 1900 or self.year > current_year:
            raise ValueError("Ano inválido.")
        if self.km_current < 0:
            raise ValueError("Kms atuais inválidos.")
        if self.consumption <= 0:
            raise ValueError("Consumo inválido.")
        if self.is_imported and self.fuel_type != "Elétrico":
            if (self.co2 or 0) <= 0:
                raise ValueError("CO2 obrigatório para importados (não elétrico).")
            if (self.engine_cc or 0) <= 0:
                raise ValueError("Cilindrada obrigatória para importados (não elétrico).")

@dataclass
class TcoParams:
    hold_years: int
    annual_km: int
    fuel_prices: Dict[str, float]
    real_cons_adj: float = 0.20
    depreciation_schedule_pct: List[float] = field(default_factory=list)
    depreciation_schedule_bias_pct: float = 0.0
    fixed_costs: Dict[str, float] = field(default_factory=lambda: {
        "insurance": 400.0,
        "iuc_base": 150.0,
        "inspection": 35.0,
        "tolls_parking": 0.0
    })

@dataclass
class CalculationResult:
    vehicle_name: str
    total_cost: float
    cost_per_km: float
    km_at_end: int
    acquisition_cost: float
    resale_value: float
    energy_cost: float
    energy_qty: float
    energy_unit: str
    tolls_parking_cost: float
    insurance_fiscality_cost: float
    maint_cost: float
    breakdown: Dict[str, float]
    delta_total: float = 0.0
    delta_km: float = 0.0

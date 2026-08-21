#!/usr/bin/env python3
"""
AUSHADHI — Firestore Seed Data Script
Seeds realistic health center, medicine, and inventory data for
East Godavari and Krishna districts, Andhra Pradesh.

Run: python3 scripts/seed_firestore.py
"""
from google.cloud import firestore
from datetime import datetime, timezone, timedelta
import random

db = firestore.Client()
now = datetime.now(timezone.utc)


# ─── MEDICINES ──────────────────────────────────────────────────────────────
MEDICINES = [
    {
        "id": "med_ors_001",
        "name": "ORS Packets (WHO Formula)",
        "generic_name": "Oral Rehydration Salt",
        "category": "ORS_ELECTROLYTE",
        "unit": "packets",
        "essential": True,
        "outbreak_indicators": [
            {"disease": "CHOLERA", "significance": "PRIMARY", "baseline_ratio_threshold": 2.0},
            {"disease": "GASTROENTERITIS", "significance": "PRIMARY", "baseline_ratio_threshold": 1.8}
        ],
        "default_minimum_threshold_units": 200,
        "default_maximum_capacity_units": 600,
        "unit_cost_inr": 3.50
    },
    {
        "id": "med_zinc_001",
        "name": "Zinc Tablets 20mg",
        "generic_name": "Zinc Sulfate",
        "category": "VITAMIN",
        "unit": "tablets",
        "essential": True,
        "outbreak_indicators": [
            {"disease": "CHOLERA", "significance": "PRIMARY", "baseline_ratio_threshold": 1.8},
            {"disease": "GASTROENTERITIS", "significance": "SECONDARY", "baseline_ratio_threshold": 1.5}
        ],
        "default_minimum_threshold_units": 500,
        "default_maximum_capacity_units": 2000,
        "unit_cost_inr": 0.80
    },
    {
        "id": "med_ivns_001",
        "name": "IV Normal Saline 500ml",
        "generic_name": "Sodium Chloride 0.9%",
        "category": "IV_FLUID",
        "unit": "bottles",
        "essential": True,
        "outbreak_indicators": [
            {"disease": "CHOLERA", "significance": "PRIMARY", "baseline_ratio_threshold": 2.5},
            {"disease": "DENGUE", "significance": "PRIMARY", "baseline_ratio_threshold": 2.0}
        ],
        "default_minimum_threshold_units": 50,
        "default_maximum_capacity_units": 200,
        "unit_cost_inr": 45.00
    },
    {
        "id": "med_paracetamol_001",
        "name": "Paracetamol 500mg Tablets",
        "generic_name": "Acetaminophen",
        "category": "ANALGESIC",
        "unit": "tablets",
        "essential": True,
        "outbreak_indicators": [
            {"disease": "INFLUENZA", "significance": "PRIMARY", "baseline_ratio_threshold": 2.0},
            {"disease": "MALARIA", "significance": "SECONDARY", "baseline_ratio_threshold": 1.5},
            {"disease": "DENGUE", "significance": "PRIMARY", "baseline_ratio_threshold": 2.0}
        ],
        "default_minimum_threshold_units": 2000,
        "default_maximum_capacity_units": 10000,
        "unit_cost_inr": 0.15
    },
    {
        "id": "med_metronidazole_001",
        "name": "Metronidazole 400mg Tablets",
        "generic_name": "Metronidazole",
        "category": "ANTIBIOTIC",
        "unit": "tablets",
        "essential": True,
        "outbreak_indicators": [
            {"disease": "GASTROENTERITIS", "significance": "PRIMARY", "baseline_ratio_threshold": 1.8},
            {"disease": "CHOLERA", "significance": "SECONDARY", "baseline_ratio_threshold": 1.5}
        ],
        "default_minimum_threshold_units": 500,
        "default_maximum_capacity_units": 3000,
        "unit_cost_inr": 0.60
    },
    {
        "id": "med_chloroquine_001",
        "name": "Chloroquine 250mg Tablets",
        "generic_name": "Chloroquine Phosphate",
        "category": "ANTIMALARIA",
        "unit": "tablets",
        "essential": True,
        "outbreak_indicators": [
            {"disease": "MALARIA", "significance": "PRIMARY", "baseline_ratio_threshold": 1.5}
        ],
        "default_minimum_threshold_units": 200,
        "default_maximum_capacity_units": 2000,
        "unit_cost_inr": 1.20
    },
    {
        "id": "med_amoxicillin_001",
        "name": "Amoxicillin 500mg Capsules",
        "generic_name": "Amoxicillin Trihydrate",
        "category": "ANTIBIOTIC",
        "unit": "capsules",
        "essential": True,
        "outbreak_indicators": [
            {"disease": "INFLUENZA", "significance": "SECONDARY", "baseline_ratio_threshold": 1.3}
        ],
        "default_minimum_threshold_units": 500,
        "default_maximum_capacity_units": 3000,
        "unit_cost_inr": 2.50
    },
    {
        "id": "med_cotrimoxazole_001",
        "name": "Cotrimoxazole (480mg) Tablets",
        "generic_name": "Sulfamethoxazole + Trimethoprim",
        "category": "ANTIBIOTIC",
        "unit": "tablets",
        "essential": True,
        "outbreak_indicators": [
            {"disease": "CHOLERA", "significance": "SECONDARY", "baseline_ratio_threshold": 1.2}
        ],
        "default_minimum_threshold_units": 300,
        "default_maximum_capacity_units": 2000,
        "unit_cost_inr": 0.80
    },
    {
        "id": "med_artesunate_001",
        "name": "Artesunate + Amodiaquine (ACT)",
        "generic_name": "Artemisinin Combination Therapy",
        "category": "ANTIMALARIA",
        "unit": "courses",
        "essential": True,
        "outbreak_indicators": [
            {"disease": "MALARIA", "significance": "PRIMARY", "baseline_ratio_threshold": 2.0}
        ],
        "default_minimum_threshold_units": 50,
        "default_maximum_capacity_units": 300,
        "unit_cost_inr": 45.00
    },
    {
        "id": "med_iron_folic_001",
        "name": "Iron Folic Acid Tablets",
        "generic_name": "Ferrous Sulfate + Folic Acid",
        "category": "VITAMIN",
        "unit": "tablets",
        "essential": True,
        "outbreak_indicators": [],
        "default_minimum_threshold_units": 1000,
        "default_maximum_capacity_units": 5000,
        "unit_cost_inr": 0.30
    }
]


# ─── HEALTH CENTERS ─────────────────────────────────────────────────────────
# East Godavari and Krishna districts, Andhra Pradesh
HEALTH_CENTERS = [
    # East Godavari District (user's home district — Mandapeta area)
    {
        "id": "phc_razole_001",
        "name": "PHC Razole",
        "type": "PHC",
        "district": "East Godavari",
        "subdistrict": "Razole",
        "address": "Razole, East Godavari, Andhra Pradesh 533242",
        "location": {"lat": 16.4797, "lng": 81.6958},
        "catchment_population": 28000,
        "medical_officer": "Dr. Suresh Babu",
        "contact_phone": "+91-8856-222444",
        "contact_email": "phc.razole@ap.gov.in",
        "nearest_warehouse_id": "wh_rajahmundry_001",
        "nearest_warehouse_distance_km": 78,
        # Demo scenario: This center has outbreak + critical stockouts
        "_demo_scenario": "CHOLERA_OUTBREAK"
    },
    {
        "id": "phc_amalapuram_002",
        "name": "PHC Amalapuram",
        "type": "PHC",
        "district": "East Godavari",
        "subdistrict": "Amalapuram",
        "address": "Amalapuram, East Godavari, Andhra Pradesh 533201",
        "location": {"lat": 16.5764, "lng": 82.0097},
        "catchment_population": 32000,
        "medical_officer": "Dr. Padmavathi Rao",
        "contact_phone": "+91-8856-234567",
        "contact_email": "phc.amalapuram@ap.gov.in",
        "nearest_warehouse_id": "wh_rajahmundry_001",
        "nearest_warehouse_distance_km": 52,
        "_demo_scenario": "CHOLERA_OUTBREAK"  # Same cluster as Razole
    },
    {
        "id": "phc_mandapeta_003",
        "name": "PHC Mandapeta",
        "type": "PHC",
        "district": "East Godavari",
        "subdistrict": "Mandapeta",
        "address": "Mandapeta, East Godavari, Andhra Pradesh 533308",
        "location": {"lat": 16.8666, "lng": 81.9333},
        "catchment_population": 35000,
        "medical_officer": "Dr. Ramakrishna Naidu",
        "contact_phone": "+91-8855-254321",
        "contact_email": "phc.mandapeta@ap.gov.in",
        "nearest_warehouse_id": "wh_rajahmundry_001",
        "nearest_warehouse_distance_km": 30,
        "_demo_scenario": "LOW_STOCK_ONLY"  # Stock low but no outbreak yet
    },
    {
        "id": "chc_rajahmundry_004",
        "name": "CHC Rajahmundry Urban",
        "type": "CHC",
        "district": "East Godavari",
        "subdistrict": "Rajahmundry",
        "address": "Rajahmundry, East Godavari, Andhra Pradesh 533101",
        "location": {"lat": 17.0005, "lng": 81.8040},
        "catchment_population": 85000,
        "medical_officer": "Dr. Venkateswara Rao",
        "contact_phone": "+91-883-2454444",
        "contact_email": "chc.rajahmundry@ap.gov.in",
        "nearest_warehouse_id": "wh_rajahmundry_001",
        "nearest_warehouse_distance_km": 2,
        "_demo_scenario": "NORMAL"  # Good stock, for contrast
    },
    # Krishna District
    {
        "id": "phc_gudivada_005",
        "name": "PHC Gudivada Rural",
        "type": "PHC",
        "district": "Krishna",
        "subdistrict": "Gudivada",
        "address": "Gudivada, Krishna District, Andhra Pradesh 521301",
        "location": {"lat": 16.4345, "lng": 80.9969},
        "catchment_population": 24000,
        "medical_officer": "Dr. Srinivasa Murthy",
        "contact_phone": "+91-8674-242222",
        "contact_email": "phc.gudivada@ap.gov.in",
        "nearest_warehouse_id": "wh_vijayawada_002",
        "nearest_warehouse_distance_km": 43,
        "_demo_scenario": "NORMAL"
    },
    {
        "id": "phc_machilipatnam_006",
        "name": "PHC Machilipatnam",
        "type": "PHC",
        "district": "Krishna",
        "subdistrict": "Machilipatnam",
        "address": "Machilipatnam, Krishna District, Andhra Pradesh 521001",
        "location": {"lat": 16.1875, "lng": 81.1376},
        "catchment_population": 29000,
        "medical_officer": "Dr. Annapurna Devi",
        "contact_phone": "+91-8672-222888",
        "contact_email": "phc.machilipatnam@ap.gov.in",
        "nearest_warehouse_id": "wh_vijayawada_002",
        "nearest_warehouse_distance_km": 68,
        "_demo_scenario": "MALARIA_RISK"  # Seasonal malaria risk
    },
    {
        "id": "chc_vijayawada_007",
        "name": "CHC Vijayawada North",
        "type": "CHC",
        "district": "Krishna",
        "subdistrict": "Vijayawada",
        "address": "Vijayawada North, Krishna District, Andhra Pradesh 520001",
        "location": {"lat": 16.5062, "lng": 80.6480},
        "catchment_population": 110000,
        "medical_officer": "Dr. Chakravarthy Reddy",
        "contact_phone": "+91-866-2571234",
        "contact_email": "chc.vijayawada.north@ap.gov.in",
        "nearest_warehouse_id": "wh_vijayawada_002",
        "nearest_warehouse_distance_km": 5,
        "_demo_scenario": "NORMAL"
    },
    {
        "id": "dh_kakinada_008",
        "name": "District Hospital Kakinada",
        "type": "DH",
        "district": "East Godavari",
        "subdistrict": "Kakinada",
        "address": "Main Road, Kakinada, East Godavari, AP 533001",
        "location": {"lat": 16.9891, "lng": 82.2475},
        "catchment_population": 350000,
        "medical_officer": "Dr. Lalitha Prasad (Superintendent)",
        "contact_phone": "+91-884-2362225",
        "contact_email": "dh.kakinada@ap.gov.in",
        "nearest_warehouse_id": "wh_rajahmundry_001",
        "nearest_warehouse_distance_km": 55,
        "_demo_scenario": "NORMAL"
    }
]


# ─── WAREHOUSES ─────────────────────────────────────────────────────────────
WAREHOUSES = [
    {
        "id": "wh_rajahmundry_001",
        "name": "District Medical Stores, Rajahmundry",
        "district": "East Godavari",
        "location": {
            "lat": 17.0005, "lng": 81.8040,
            "address": "Near RTC Complex, Rajahmundry, AP 533101"
        },
        "contact": {"phone": "+91-883-2460000", "email": "dms.rajahmundry@ap.gov.in"},
        "operating_hours": "Mon-Sat 8AM-6PM, Emergency: 24x7",
        "available_medicines": [
            {"medicine_id": "med_ors_001", "medicine_name": "ORS Packets", "available_quantity": 5000},
            {"medicine_id": "med_zinc_001", "medicine_name": "Zinc Tablets 20mg", "available_quantity": 20000},
            {"medicine_id": "med_ivns_001", "medicine_name": "IV Normal Saline 500ml", "available_quantity": 800},
            {"medicine_id": "med_paracetamol_001", "medicine_name": "Paracetamol 500mg", "available_quantity": 100000},
            {"medicine_id": "med_metronidazole_001", "medicine_name": "Metronidazole 400mg", "available_quantity": 30000},
            {"medicine_id": "med_chloroquine_001", "medicine_name": "Chloroquine 250mg", "available_quantity": 10000},
            {"medicine_id": "med_amoxicillin_001", "medicine_name": "Amoxicillin 500mg", "available_quantity": 25000},
            {"medicine_id": "med_artesunate_001", "medicine_name": "ACT Courses", "available_quantity": 500},
        ]
    },
    {
        "id": "wh_vijayawada_002",
        "name": "District Medical Stores, Vijayawada",
        "district": "Krishna",
        "location": {
            "lat": 16.5062, "lng": 80.6480,
            "address": "Bandar Road, Vijayawada, AP 520001"
        },
        "contact": {"phone": "+91-866-2570000", "email": "dms.vijayawada@ap.gov.in"},
        "operating_hours": "Mon-Sat 8AM-6PM, Emergency: 24x7",
        "available_medicines": [
            {"medicine_id": "med_ors_001", "medicine_name": "ORS Packets", "available_quantity": 8000},
            {"medicine_id": "med_zinc_001", "medicine_name": "Zinc Tablets 20mg", "available_quantity": 35000},
            {"medicine_id": "med_ivns_001", "medicine_name": "IV Normal Saline 500ml", "available_quantity": 1200},
            {"medicine_id": "med_paracetamol_001", "medicine_name": "Paracetamol 500mg", "available_quantity": 150000},
            {"medicine_id": "med_chloroquine_001", "medicine_name": "Chloroquine 250mg", "available_quantity": 15000},
            {"medicine_id": "med_artesunate_001", "medicine_name": "ACT Courses", "available_quantity": 800},
        ]
    }
]


# ─── INVENTORY SCENARIOS ─────────────────────────────────────────────────────
def get_inventory_for_center(center: dict) -> list:
    """Generate inventory based on center's demo scenario."""
    scenario = center.get("_demo_scenario", "NORMAL")
    items = []

    for med in MEDICINES:
        max_cap = med["default_maximum_capacity_units"]
        min_thresh = med["default_minimum_threshold_units"]

        if scenario == "CHOLERA_OUTBREAK":
            # ORS, Zinc, IV Saline are critically low (demand spike consuming them)
            if med["id"] in ["med_ors_001", "med_zinc_001", "med_ivns_001"]:
                current = int(max_cap * 0.07)  # 7% stock = CRITICAL
                daily_consumption = int(med.get("default_minimum_threshold_units", 50) * 0.38)
                seven_day_avg = int(daily_consumption / 3.8)
                anomaly_flag = True
                anomaly_ratio = 3.8
            else:
                current = int(max_cap * 0.55)
                daily_consumption = int(max_cap * 0.008)
                seven_day_avg = daily_consumption
                anomaly_flag = False
                anomaly_ratio = None

        elif scenario == "LOW_STOCK_ONLY":
            if med["id"] in ["med_paracetamol_001", "med_amoxicillin_001"]:
                current = int(max_cap * 0.22)  # 22% = LOW
                daily_consumption = int(max_cap * 0.01)
                seven_day_avg = daily_consumption
                anomaly_flag = False
                anomaly_ratio = None
            else:
                current = int(max_cap * 0.60)
                daily_consumption = int(max_cap * 0.008)
                seven_day_avg = daily_consumption
                anomaly_flag = False
                anomaly_ratio = None

        elif scenario == "MALARIA_RISK":
            if med["id"] in ["med_chloroquine_001", "med_artesunate_001"]:
                current = int(max_cap * 0.25)
                daily_consumption = int(min_thresh * 0.24)
                seven_day_avg = int(daily_consumption / 1.7)
                anomaly_flag = True
                anomaly_ratio = 1.7
            else:
                current = int(max_cap * 0.55)
                daily_consumption = int(max_cap * 0.008)
                seven_day_avg = daily_consumption
                anomaly_flag = False
                anomaly_ratio = None

        else:  # NORMAL
            current = int(max_cap * random.uniform(0.55, 0.85))
            daily_consumption = int(max_cap * random.uniform(0.006, 0.012))
            seven_day_avg = daily_consumption
            anomaly_flag = False
            anomaly_ratio = None

        stock_pct = (current / max_cap) * 100

        if stock_pct < 15:
            urgency = "CRITICAL"
        elif stock_pct < 30:
            urgency = "LOW"
        elif stock_pct < 50:
            urgency = "MONITOR"
        else:
            urgency = "OK"

        days_until = int(current / daily_consumption) if daily_consumption > 0 else 999

        items.append({
            "center_id": center["id"],
            "medicine_id": med["id"],
            "medicine_name": med["name"],
            "current_stock": current,
            "minimum_threshold": min_thresh,
            "maximum_capacity": max_cap,
            "stock_percentage": round(stock_pct, 1),
            "urgency": urgency,
            "days_until_stockout": days_until if urgency != "OK" else None,
            "opening_stock_today": current + daily_consumption,
            "daily_consumption_today": daily_consumption,
            "seven_day_avg_consumption": seven_day_avg,
            "thirty_day_avg_consumption": int(seven_day_avg * 1.05),
            "consumption_ratio": round(daily_consumption / seven_day_avg, 2) if seven_day_avg > 0 else 1.0,
            "anomaly_flag": anomaly_flag,
            "anomaly_ratio": anomaly_ratio,
            "pending_order_quantity": 0,
            "expected_stock_date": None,
            "last_updated": now.isoformat(),
            "last_reported_by": "ASHA Worker (Simulated)",
            "updated_at": now.isoformat()
        })

    return items


# ─── SEED FUNCTIONS ──────────────────────────────────────────────────────────
def seed_medicines():
    print("\n📦 Seeding medicines...")
    for med in MEDICINES:
        med_data = {**med, "created_at": now.isoformat()}
        db.collection("medicines").document(med["id"]).set(med_data)
        print(f"  ✅ {med['name']}")


def seed_warehouses():
    print("\n🏭 Seeding warehouses...")
    for wh in WAREHOUSES:
        wh_data = {**wh, "created_at": now.isoformat(), "updated_at": now.isoformat()}
        db.collection("warehouses").document(wh["id"]).set(wh_data)
        print(f"  ✅ {wh['name']}")


def seed_health_centers():
    print("\n🏥 Seeding health centers...")
    for center in HEALTH_CENTERS:
        center_data = {
            **{k: v for k, v in center.items() if not k.startswith("_")},
            "status": {
                "last_checked": now.isoformat(),
                "overall_stock_status": "CRITICAL" if center.get("_demo_scenario") == "CHOLERA_OUTBREAK" else "MODERATE",
                "critical_items_count": 3 if center.get("_demo_scenario") == "CHOLERA_OUTBREAK" else 0,
                "low_items_count": 2 if center.get("_demo_scenario") in ["CHOLERA_OUTBREAK", "LOW_STOCK_ONLY"] else 0,
                "data_quality_score": round(random.uniform(0.78, 0.95), 2),
                "last_report_date": (now - timedelta(hours=random.randint(2, 18))).isoformat(),
                "reporting_status": "ON_TIME"
            },
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        db.collection("health_centers").document(center["id"]).set(center_data)
        print(f"  ✅ {center['name']} ({center.get('_demo_scenario', 'NORMAL')})")


def seed_inventory():
    print("\n💊 Seeding inventory (per center)...")
    for center in HEALTH_CENTERS:
        items = get_inventory_for_center(center)
        for item in items:
            doc_id = f"{center['id']}_{item['medicine_id']}"
            db.collection("inventory").document(doc_id).set(item)
        critical = sum(1 for i in items if i["urgency"] == "CRITICAL")
        print(f"  ✅ {center['name']}: {len(items)} medicines ({critical} CRITICAL)")


def seed_consumption_history():
    """Seed 7 days of consumption history for outbreak scenario."""
    print("\n📊 Seeding consumption history (last 7 days)...")
    outbreak_centers = ["phc_razole_001", "phc_amalapuram_002"]
    outbreak_meds = ["med_ors_001", "med_zinc_001", "med_ivns_001"]

    for center_id in [c["id"] for c in HEALTH_CENTERS]:
        for med in MEDICINES:
            for days_ago in range(7, 0, -1):
                report_date = (now - timedelta(days=days_ago)).strftime("%Y-%m-%d")
                is_outbreak = center_id in outbreak_centers and med["id"] in outbreak_meds
                base_consumption = int(med["default_maximum_capacity_units"] * 0.008)

                if is_outbreak:
                    multiplier = 1.0 + (days_ago * 0.4)
                    daily_consumption = int(base_consumption * multiplier)
                else:
                    daily_consumption = int(base_consumption * random.uniform(0.8, 1.2))

                record = {
                    "center_id": center_id,
                    "medicine_id": med["id"],
                    "report_date": report_date,
                    "opening_stock": med["default_maximum_capacity_units"] // 2,
                    "received_stock": 0,
                    "closing_stock": (med["default_maximum_capacity_units"] // 2) - daily_consumption,
                    "daily_consumption": daily_consumption,
                    "is_valid": True,
                    "validation_errors": [],
                    "validation_warnings": [],
                    "quality_score": 1.0,
                    "reported_by": "ASHA Worker (Simulated)",
                    "report_source": "SIMULATED",
                    "created_at": (now - timedelta(days=days_ago)).isoformat()
                }
                doc_id = f"{center_id}_{med['id']}_{report_date}"
                db.collection("consumption_records").document(doc_id).set(record)

    print("  ✅ 7-day consumption history seeded (outbreak escalation pattern for Razole/Amalapuram)")


def seed_system_config():
    print("\n⚙️  Seeding system config...")
    db.collection("system_config").document("main_config").set({
        "id": "main_config",
        "sentinel_poll_interval_minutes": 30,
        "critical_threshold_percentage": 15,
        "low_threshold_percentage": 30,
        "outbreak_detection_window_days": 7,
        "procurement_auto_approve_below_inr": 5000,
        "use_gemma_fallback": False,
        "districts_monitored": ["East Godavari", "Krishna"],
        "updated_at": now.isoformat()
    })
    print("  ✅ system_config")


# ─── MAIN ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🌿 AUSHADHI — Firestore Seed Script")
    print("=" * 50)
    print(f"Project: {db.project}")
    print(f"Seeding data for East Godavari + Krishna districts, Andhra Pradesh")
    print(f"Demo scenario: PHC Razole + PHC Amalapuram have active cholera cluster")
    print("=" * 50)

    seed_medicines()
    seed_warehouses()
    seed_health_centers()
    seed_inventory()
    seed_consumption_history()
    seed_system_config()

    print("\n" + "=" * 50)
    print("🎉 AUSHADHI seed complete!")
    print(f"\nDemo scenario ready:")
    print(f"  🚨 PHC Razole + PHC Amalapuram: ORS/Zinc/IV Saline at CRITICAL level")
    print(f"  🦠 Cholera outbreak pattern detectable from 7-day consumption data")
    print(f"  ⚠️  PHC Mandapeta: Paracetamol/Amoxicillin at LOW level")
    print(f"  ✅  CHC Rajahmundry + Vijayawada: Normal stock for contrast")
    print(f"\nTrigger the pipeline:")
    print(f"  curl -X POST $API_URL/api/v1/internal/run-sentinel \\")
    print(f"       -H 'X-API-Key: $AUSHADHI_API_KEY'")

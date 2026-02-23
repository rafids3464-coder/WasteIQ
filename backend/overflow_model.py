"""
WASTE IQ – Overflow Prediction Model
RandomForest-based bin overflow probability predictor.
Trains on synthetic historical data if model file doesn't exist.
"""

import os
import pickle
import numpy as np
from datetime import datetime, timezone

MODEL_PATH = os.path.join(os.path.dirname(__file__), "overflow_model.pkl")

# ── Synthetic Training Data Generator ────────────────────────────────────────
def _generate_training_data(n_samples: int = 5000):
    """
    Generate realistic synthetic bin overflow training data.
    Features: [fill_level, hours_since_last, population_density, avg_daily_waste_kg]
    Labels:   1 = will overflow within 12 hours, 0 = safe
    """
    rng = np.random.default_rng(42)

    fill_levels         = rng.uniform(0, 100, n_samples)
    hours_since_last    = rng.uniform(0, 168, n_samples)   # up to 1 week
    population_density  = rng.uniform(500, 50000, n_samples)
    avg_daily_waste_kg  = rng.uniform(0.5, 10, n_samples)

    X = np.column_stack([fill_levels, hours_since_last, population_density, avg_daily_waste_kg])

    # Overflow probability heuristic for labeling
    overflow_score = (
        (fill_levels / 100) * 0.55 +
        np.clip(hours_since_last / 48, 0, 1) * 0.25 +
        np.clip(population_density / 50000, 0, 1) * 0.12 +
        np.clip(avg_daily_waste_kg / 10, 0, 1) * 0.08
    )
    # Add noise
    overflow_score += rng.normal(0, 0.05, n_samples)
    overflow_score = np.clip(overflow_score, 0, 1)
    y = (overflow_score > 0.65).astype(int)

    return X, y, overflow_score


# ── Model Class ───────────────────────────────────────────────────────────────
class OverflowModel:
    def __init__(self):
        if os.path.exists(MODEL_PATH):
            print("⏳ Loading overflow model from disk...")
            with open(MODEL_PATH, "rb") as f:
                self.model = pickle.load(f)
            print("✅ Overflow model loaded")
        else:
            print("⏳ Training overflow prediction model (first run)...")
            self._train_and_save()
            print("✅ Overflow model trained and saved")

    def _train_and_save(self):
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import Pipeline

        X, y, _ = _generate_training_data(n_samples=8000)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("rf", RandomForestClassifier(
                n_estimators=200,
                max_depth=12,
                min_samples_split=5,
                min_samples_leaf=2,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            ))
        ])

        pipeline.fit(X_train, y_train)
        accuracy = pipeline.score(X_test, y_test)
        print(f"   Model accuracy: {accuracy:.3f}")

        self.model = pipeline
        with open(MODEL_PATH, "wb") as f:
            pickle.dump(pipeline, f)

    def predict(self, fill_level: float, hours_since_last: float,
                population_density: float, avg_daily_waste_kg: float = 2.5) -> dict:
        """
        Predict overflow probability for a single bin.
        Returns: overflow_probability (0-1), risk_level, hours_to_overflow
        """
        X = np.array([[fill_level, hours_since_last, population_density, avg_daily_waste_kg]])
        prob = float(self.model.predict_proba(X)[0][1])

        # Risk levels
        if prob < 0.35:
            risk_level = "Low"
        elif prob < 0.65:
            risk_level = "Medium"
        else:
            risk_level = "High"

        # Estimate hours to overflow
        fill_rate_per_hour = avg_daily_waste_kg / 24  # kg/hour
        remaining_capacity_pct = max(0, 100 - fill_level)
        if fill_rate_per_hour > 0 and remaining_capacity_pct > 0:
            hours_to_overflow = remaining_capacity_pct / (fill_rate_per_hour * 5)  # normalize
        else:
            hours_to_overflow = None

        return {
            "overflow_probability": round(prob, 4),
            "risk_level":          risk_level,
            "hours_to_overflow":   round(hours_to_overflow, 1) if hours_to_overflow else None,
        }

    def predict_and_save(
        self,
        bin_id: str,
        fill_level: float,
        hours_since_last: float,
        population_density: float,
        avg_daily_waste_kg: float,
        firestore_client,
    ) -> dict:
        """Predict and persist to Firestore overflow_predictions collection."""
        result = self.predict(fill_level, hours_since_last, population_density, avg_daily_waste_kg)

        doc = {
            "bin_id":               bin_id,
            "overflow_probability": result["overflow_probability"],
            "risk_level":           result["risk_level"],
            "hours_to_overflow":    result["hours_to_overflow"],
            "input_features": {
                "fill_level":         fill_level,
                "hours_since_last":   hours_since_last,
                "population_density": population_density,
                "avg_daily_waste_kg": avg_daily_waste_kg,
            },
            "predicted_at": datetime.now(timezone.utc).isoformat(),
        }

        pred_id = firestore_client.add_doc("overflow_predictions", doc)
        doc["prediction_id"] = pred_id

        # Update the bin's risk status in Firestore
        status_update = {}
        if result["risk_level"] == "High":
            status_update["status"] = "overflow"
        elif result["risk_level"] == "Medium":
            status_update["status"] = "active"
        if status_update:
            try:
                firestore_client.update_doc("bins", bin_id, status_update)
            except Exception:
                pass

        return doc

    def batch_predict(self, bins: list, firestore_client) -> list:
        """Run predictions for a list of bin dicts (from Firestore)."""
        results = []
        for b in bins:
            bid = b.get("_id") or b.get("bin_id", "unknown")
            fill_level = b.get("fill_level", 0.0)

            # Hours since last collection
            last_collected = b.get("last_collected")
            if last_collected:
                try:
                    last_dt = datetime.fromisoformat(last_collected)
                    now = datetime.now(timezone.utc)
                    hours_since = (now - last_dt).total_seconds() / 3600
                except Exception:
                    hours_since = 24.0
            else:
                hours_since = 72.0  # No collection data = assume 3 days

            pop_density = b.get("population_density", 10000.0)
            daily_waste = b.get("avg_daily_waste_kg", 2.5)

            pred = self.predict_and_save(
                bin_id=bid,
                fill_level=fill_level,
                hours_since_last=hours_since,
                population_density=pop_density,
                avg_daily_waste_kg=daily_waste,
                firestore_client=firestore_client,
            )
            pred["bin_id"] = bid
            results.append(pred)
        return results

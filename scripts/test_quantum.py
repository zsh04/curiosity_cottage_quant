import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.services.physics import PhysicsService
import numpy as np


def test_quantum_tunneling():
    print("🧪 QUANTUM PHYSICS VERIFICATION")
    print("==============================")
    physics = PhysicsService()

    # 1. Classical Breakout Case (High Energy)
    # Price close to resistance, High Volatility
    price = 100.0
    resistance = 102.0
    volatility = 20.0  # E = 0.5 * 400 = 200. V=102. E > V.

    prob = physics.calculate_tunneling_probability(price, resistance, volatility)
    print(f"CASE 1 (Classical Breakout): P={price}, R={resistance}, Vol={volatility}")
    print(f" -> Probability: {prob:.4f} (Expected: 1.0)")
    assert prob == 1.0, "Classical breakout should be 1.0"

    # 2. Impossible Wall (Low Energy, Wide Barrier)
    # Price far from resistance, Low Volatility
    price = 100.0
    resistance = 110.0  # Width = 10
    volatility = 2.0  # E = 0.5 * 4 = 2. V=110. E << V.

    prob = physics.calculate_tunneling_probability(price, resistance, volatility)
    print(f"\nCASE 2 (Impossible Wall): P={price}, R={resistance}, Vol={volatility}")
    print(f" -> Probability: {prob:.8f} (Expected: ~0.0)")
    assert prob < 0.0001, "Impossible wall should be near 0"

    # 3. Quantum Tunneling (Near Barrier, Medium Energy)
    # Price very close, Volatility moderate but E < V
    price = 100.0
    resistance = 100.5  # Width = 0.5
    volatility = 10.0  # E = 0.5 * 100 = 50. V=100.5.
    # V-E = 50.5. 2*m*(V-E) = 101. Sqrt(101) ~ 10.
    # Integral = 10 * 0.5 = 5.
    # Prob = exp(-10) ~ 4.5e-5.

    prob = physics.calculate_tunneling_probability(price, resistance, volatility)
    print(f"\nCASE 3 (Tunneling): P={price}, R={resistance}, Vol={volatility}")
    print(f" -> Probability: {prob:.8f}")
    assert 0.0 < prob < 0.1, f"Should be small but non-zero: {prob}"

    print("\n✅ Physics Service Tunneling Logic Verified.")


def test_integration():
    print("\n🔗 INTEGRATION TEST (calculate_kinematics)")
    physics = PhysicsService()

    # Warmup
    prices = [100 + np.sin(i / 10) for i in range(50)]  # Oscillation
    # Resistance will be around 101.0

    res = physics.calculate_kinematics(prices=prices)
    print(f"Warmup Result keys: {res.keys()}")

    # Push new price near max
    new_price = 101.5  # Breakout?
    res = physics.calculate_kinematics(new_price=new_price)
    print(f"Update Result: {res}")

    assert "tunneling_prob" in res, "Missing tunneling_prob in result"
    print(f"Tunneling Prob: {res['tunneling_prob']}")


if __name__ == "__main__":
    test_quantum_tunneling()
    test_integration()

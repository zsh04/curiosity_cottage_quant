import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.generated import brain_pb2 as pb2

print("PB2 File:", pb2.__file__)
print("Fields:", [f.name for f in pb2.ForecastResponse.DESCRIPTOR.fields])

try:
    resp = pb2.ForecastResponse(
        signal="BUY",
        confidence=0.9,
        reasoning="Test",
        p10=1.0,
        p50=2.0,
        p90=3.0,
        trend=0.1,
        chronos_json="{}",
        raf_json="{}",
        meta_json="{}",
    )
    print("✅ Instantiation Success:", resp)
except Exception as e:
    print("❌ Instantiation Failed:", e)
    import traceback

    traceback.print_exc()

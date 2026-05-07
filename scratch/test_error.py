
import sys
print(f"Python Version: {sys.version}")

try:
    # Test pipe operator for types (Python 3.10+)
    x = int | None
    print("int | None is supported")
except Exception as e:
    print(f"int | None failed: {e}")

try:
    # Test bitwise OR on types (should fail with this specific error on older versions)
    y = type | None
except Exception as e:
    print(f"Caught expected error for type | None: {e}")

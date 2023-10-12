# Available base types
UNSIGNED_INTEGER_TYPES = {f"uint{8*(i+1)}" for i in range(32)}
SIGNED_INTEGER_TYPES = {f"int{8*(i+1)}" for i in range(32)}
INTEGER_TYPES = UNSIGNED_INTEGER_TYPES | SIGNED_INTEGER_TYPES

BYTES_M_TYPES = {f"bytes{i+1}" for i in range(32)}
DECIMAL_TYPES = {"decimal"}


BASE_TYPES = INTEGER_TYPES | BYTES_M_TYPES | DECIMAL_TYPES | {"bool", "address"}

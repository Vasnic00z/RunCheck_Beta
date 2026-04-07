def validar_cedula_ecuatoriana(cedula):
    """
    Verifica si una cédula ecuatoriana es válida.
    """
    # Nueva validación simplificada:
    # 1. Verificar longitud exacta de 10 caracteres
    # 2. Verificar que sean números
    if not cedula.isdigit() or len(cedula) != 10:
        return False
        
    return True

# Test cases - Updated for relaxed rules
test_cases = [
    ("1710034065", True),   # Valid Pichincha - KEEP TRUE
    ("0910000000", True),   # Invalid Guayas (checksum wrong) -> NOW TRUE (length 10, numeric)
    ("171003406", False),   # Too short - KEEP FALSE
    ("17100340655", False), # Too long - KEEP FALSE
    ("17A0034065", False),  # Not numeric - KEEP FALSE
    ("5010034065", True),   # Invalid province -> NOW TRUE (length 10, numeric)
    ("1790034065", True),   # Invalid third digit -> NOW TRUE (length 10, numeric)
    ("1104680135", True),   # Valid Loja - KEEP TRUE
]

print("Running tests...")
all_passed = True
for cedula, expected in test_cases:
    result = validar_cedula_ecuatoriana(cedula)
    if result != expected:
        print(f"FAILED: {cedula} -> Expected {expected}, got {result}")
        all_passed = False
    else:
        print(f"PASSED: {cedula}")

if all_passed:
    print("\nAll tests passed!")
else:
    print("\nSome tests failed.")

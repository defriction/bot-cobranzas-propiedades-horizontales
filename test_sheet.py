from services.cobro_service import obtener_datos_sheet

rows = obtener_datos_sheet()
for i, row in enumerate(rows[:5]):
    print(f"Row {i+2} len={len(row)}:")
    for j, val in enumerate(row):
        print(f"  Col {j} ({chr(65+j)}): {val}")

import pyvisa

rm = pyvisa.ResourceManager()

for res in rm.list_resources():
    try:
        inst = rm.open_resource(res)
        inst.timeout = 3000

        idn = inst.query("*IDN?").strip()
        print(f"{res}: {idn}")

    except Exception as e:
        print(f"{res}: {e}")
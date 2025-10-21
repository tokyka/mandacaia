from pymodbus.client import ModbusSerialClient
import sys

print(f"--- Pymodbus API Test using Python from: {sys.executable} ---")
client = ModbusSerialClient(port='dummy')

print("\n--- [1] Testing 'unit' keyword argument ---")
try:
    # Não precisamos conectar, apenas testar a assinatura do método
    client.read_holding_registers(address=1, count=1, unit=1)
    print("    SUCCESS: 'unit' é um argumento válido.")
except TypeError as e:
    print(f"    FAILURE: Ocorreu o mesmo TypeError do script principal.")
    print(f"    Mensagem de erro: {e}")
except Exception as e:
    print(f"    ERRO INESPERADO: {e}")

print("\n--- [2] Testing 'slave' keyword argument ---")
try:
    client.read_holding_registers(address=1, count=1, slave=1)
    print("    SUCCESS: 'slave' é um argumento válido.")
except TypeError as e:
    print(f"    FAILURE: Ocorreu um TypeError como esperado.")
    print(f"    Mensagem de erro: {e}")
except Exception as e:
    print(f"    ERRO INESPERADO: {e}")


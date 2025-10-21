from pymodbus.client.sync import ModbusSerialClient
from ..models.modbus_model import ModbusRegister # Importar ModbusRegister

# Configuração da porta única
PORTA_SERIAL = "/dev/ttyUSB0"

def read_slave_status(slave):
    client = ModbusSerialClient(
        method='rtu',
        port=PORTA_SERIAL,
        baudrate=9600,
        timeout=1,
        stopbits=1,
        bytesize=8,
        parity='N'
    )
    if not client.connect():
        return {"id": slave.slave_id, "nome": slave.nome, "status": "Erro de conexão", "registradores": []}

    slave_data = {"id": slave.slave_id, "nome": slave.nome, "status": "Online", "registradores": []}

    for register in slave.registradores:
        try:
            if register.tipo == 'coil':
                result = client.read_coils(register.endereco, 1, unit=slave.slave_id)
            elif register.tipo == 'holding_register':
                result = client.read_holding_registers(register.endereco, 1, unit=slave.slave_id)
            else:
                slave_data["registradores"].append({
                    "endereco": register.endereco,
                    "tipo": register.tipo,
                    "descricao": register.descricao,
                    "valor": f"Tipo não suportado: {register.tipo}"
                })
                continue

            if result.isError():
                valor = "Erro na leitura"
            else:
                if register.tipo == 'coil':
                    valor = "Ativo" if result.bits[0] else "Inativo"
                else:
                    valor = str(result.registers[0])
        except Exception as e:
            valor = f"Falha: {str(e)}"
        
        slave_data["registradores"].append({
            "endereco": register.endereco,
            "tipo": register.tipo,
            "descricao": register.descricao,
            "valor": valor
        })
    
    client.close()
    return slave_data

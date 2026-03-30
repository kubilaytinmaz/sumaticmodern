"""
Decode MQTT payload to understand why data is not written.
Run: python decode_mqtt_payload.py
"""
import struct


def u32be(b): return struct.unpack('>I', b)[0]
def u16be(b): return struct.unpack('>H', b)[0]
def u16le(b): return struct.unpack('<H', b)[0]


def crc16(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def decode_payload(hex_str, label=""):
    payload = bytes.fromhex(hex_str)
    print(f"\n{'='*60}")
    print(f"Payload: {label} ({len(payload)} bytes)")
    print(f"Hex: {payload.hex()}")

    if len(payload) < 16:
        print("Too short!")
        return

    modem_id = payload[0:8].decode('ascii', errors='replace').strip()
    device_id = u32be(payload[8:12])
    slave_id = u32be(payload[12:16])

    print(f"  modem_id  : '{modem_id}'")
    print(f"  device_id : {device_id}")
    print(f"  slave_id  : {slave_id} (0x{slave_id:04x}) = register address")

    known = {
        2000: 'Sayac 1 (fc=4)', 2001: 'Sayac 2 (fc=4)',
        2002: 'Cikis-1 Durum', 2003: 'Cikis-2 Durum',
        2004: 'Acil Ariza Durumu', 2005: 'Sayac Toplam Low16',
        2006: 'Sayac Toplam High16',
        1000: 'Program 1 Cikis', 1007: 'Modbus Adresi (fc=3)',
        1453: 'Acilis Mesaji (fc=3)',
    }
    print(f"  -> Register Name: {known.get(slave_id, 'UNKNOWN')}")

    if len(payload) >= 23:
        length = payload[16]
        sec, minute, hour, day, year_off, month = payload[17:23]
        year = 2000 + year_off
        print(f"  length    : {length}")
        print(f"  timestamp : {year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{sec:02d}")

    if len(payload) >= 25:
        padding = payload[23:25]
        print(f"  padding   : {padding.hex()}")
        data = payload[25:]
        print(f"  data      : {data.hex()} ({len(data)} bytes)")

        if len(data) >= 5:
            slave_addr = data[0]
            fc = data[1]
            byte_count = data[2]
            print(f"\n  Modbus RTU analysis:")
            print(f"    slave_addr: {slave_addr}")
            print(f"    fc        : {fc} (0x{fc:02x})")
            print(f"    byte_count: {byte_count}")

            if fc in (3, 4):
                expected_len = 3 + byte_count + 2
                print(f"    expected_total_len: {expected_len}, actual_data_len: {len(data)}")
                if len(data) >= expected_len:
                    data_bytes = data[3:3+byte_count]
                    crc_recv = u16le(data[expected_len-2:expected_len])
                    crc_calc = crc16(data[:expected_len-2])
                    print(f"    data_bytes: {data_bytes.hex()}")
                    print(f"    crc_recv  : 0x{crc_recv:04x}")
                    print(f"    crc_calc  : 0x{crc_calc:04x}")
                    print(f"    crc_ok    : {crc_recv == crc_calc}")

                    regs = []
                    for i in range(0, len(data_bytes), 2):
                        if i + 1 < len(data_bytes):
                            v = u16be(data_bytes[i:i+2])
                            regs.append(v)
                    print(f"    registers : {regs}")

                    if regs:
                        print(f"\n  ✅ Method 1 result: fc={fc}, reg={slave_id}, value={regs[0]}")
                        print(f"     -> This SHOULD write to register '{known.get(slave_id, 'UNKNOWN')}'")
                    else:
                        print(f"\n  ❌ No register values parsed!")
                else:
                    print(f"  ❌ data too short for Modbus RTU (need {expected_len}, have {len(data)})")
            else:
                print(f"  ❌ Unknown FC {fc} (not 3 or 4) - Modbus RTU parse will return None!")
        else:
            print(f"  ❌ data too short for Modbus RTU (< 5 bytes)")


# Payloads from logs (first 16 bytes shown in hex_preview)
# Need full 32 bytes - but we only have first 16 from logs
# Let's construct what we expect based on the pattern

print("Analyzing observed hex_previews (first 16 bytes of each payload):")
payloads_partial = [
    ('303030303131383600000001000007d6', 'M3 - slave=2006'),
    ('303030303131383600000001000007d5', 'M3 - slave=2005'),
    ('303030303131383600000001000007d4', 'M3 - slave=2004'),
    ('303030303131383600000001000007d3', 'M3 - slave=2003'),
    ('303030303131383600000001000007d2', 'M3 - slave=2002'),
    ('303030303131383600000001000007d1', 'M3 - slave=2001=Sayac2'),
    ('303030303131383600000001000007d0', 'M3 - slave=2000=Sayac1'),
    ('303030303131383600000001000005ad', 'M3 - slave=1453 (fc=3)'),
    ('303030303131383600000001000003ef', 'M3 - slave=1007 (fc=3)'),
]

for hex_str, label in payloads_partial:
    payload = bytes.fromhex(hex_str)
    slave_id = int.from_bytes(payload[12:16], 'big')
    known = {
        2000: 'Sayac 1 (fc=4)', 2001: 'Sayac 2 (fc=4)',
        2002: 'Cikis-1 Durum', 2003: 'Cikis-2 Durum',
        2004: 'Acil Ariza Durumu', 2005: 'Sayac Toplam Low16',
        2006: 'Sayac Toplam High16',
        1000: 'Program 1 Cikis', 1007: 'Modbus Adresi (fc=3)',
        1453: 'Acilis Mesaji (fc=3)',
    }
    print(f"  slave={slave_id:5d} -> {known.get(slave_id, 'UNKNOWN'):35s} [{label}]")

print("""
CONCLUSION:
  - slave_id=2000 and slave_id=2001 are present in the stream
  - These map to 'Sayac 1' and 'Sayac 2' in register_definitions
  - The issue must be in Modbus RTU parsing of the data bytes (payload[25:])
  
  Most likely causes:
  1. CRC mismatch (but code continues anyway)
  2. fc byte is not 3 or 4 (code returns None)
  3. byte_count is wrong -> data too short check fails
  4. data portion (payload[25:]) has 0 bytes or wrong format
  
  Deploy the debug update and check 'No data written' warning data for:
  - slave_id
  - data_hex (the raw bytes[25:])
  - data_len
""")

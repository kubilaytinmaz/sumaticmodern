"""
Sumatic Modern IoT - Modbus Parser
Parses Modbus RTU responses from MQTT messages.
Ported from original program.py Modbus parsing logic.
"""
import struct
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List
from pytz import timezone

from app.core.logging import get_logger

logger = get_logger(__name__)

# Istanbul timezone
IST_TIMEZONE = timezone("Europe/Istanbul")


# Modbus function codes
FC_READ_HOLDING_REGISTERS = 0x03
FC_READ_INPUT_REGISTERS = 0x04


def u16be(data: bytes) -> int:
    """Convert 2 bytes big-endian to unsigned int."""
    return struct.unpack(">H", data)[0]


def u16le(data: bytes) -> int:
    """Convert 2 bytes little-endian to unsigned int."""
    return struct.unpack("<H", data)[0]


def u32be(data: bytes) -> int:
    """Convert 4 bytes big-endian to unsigned int."""
    return struct.unpack(">I", data)[0]


def crc16_modbus(data: bytes) -> int:
    """
    Calculate Modbus CRC16 checksum.
    
    Args:
        data: Bytes to calculate CRC for
        
    Returns:
        CRC16 value
    """
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


class ModbusParser:
    """
    Parser for Modbus RTU responses from MQTT messages.
    Handles the Alldatas topic format and Modbus RTU response parsing.
    """

    @staticmethod
    def parse_alldatas(payload: bytes) -> Optional[Dict[str, Any]]:
        """
        Parse MQTT Alldatas topic payload.
        
        Payload format (based on actual data analysis):
        [0-7]   : modem_id (8 bytes ASCII)
        [8-11]  : device_id (u32 big-endian) - actual format
        [12-15] : slave_id/register (u32 big-endian)
        [16]    : length (1 byte)
        [17-22] : timestamp (sec, min, hour, day, month, year)
        [23-24] : padding (2 bytes)
        [25]    : data starts
        
        Args:
            payload: Raw MQTT payload bytes
            
        Returns:
            Parsed data dict or None if invalid
        """
        if len(payload) < 25:
            logger.warning(f"Alldatas payload too short: {len(payload)} bytes")
            return None
        
        try:
            # Debug: log first 30 bytes of payload
            if len(payload) >= 30:
                logger.debug(
                    f"Payload hex (first 30 bytes): {payload[:30].hex()}, "
                    f"modem_raw={payload[0:8]}, "
                    f"bytes[8-12]={payload[8:12].hex()}, "
                    f"bytes[12-16]={payload[12:16].hex()}, "
                    f"bytes[16-22]={payload[16:22].hex()}"
                )
            
            # Parse modem ID (8 bytes ASCII)
            modem_id = payload[0:8].decode("ascii", errors="replace").strip()
            
            # Parse device ID (u32 big-endian at index 8-11)
            device_id = u32be(payload[8:12])
            
            # Parse slave ID (register address - u32 big-endian at index 12-15)
            slave_id = u32be(payload[12:16])
            
            # Parse timestamp (byte 16 is length, timestamp is bytes 17-22)
            # Format: sec, min, hour, day, year_offset, month
            if len(payload) >= 23:
                sec, minute, hour, day, year_offset, month = payload[17:23]
                year = 2000 + year_offset
                
                # Handle hour=24 bug (some devices send 24 instead of 0 for midnight)
                if hour == 24:
                    hour = 0
                    day += 1  # Next day
                
                # Validate and create timestamp
                try:
                    timestamp = datetime(year, month, day, hour, minute, sec)
                    # Sanity check: if year is in far past or future, use server time
                    now_year = datetime.now().year
                    if abs(timestamp.year - now_year) > 5:
                        logger.debug(
                            f"Timestamp year {timestamp.year} too far from current year {now_year}, "
                            f"using server time."
                        )
                        timestamp = datetime.now()
                except ValueError as e:
                    logger.debug(
                        f"Invalid timestamp in payload: year={year}, month={month}, "
                        f"day={day}, hour={hour}, minute={minute}, sec={sec} - {e}. Using server time."
                    )
                    timestamp = datetime.now()
            else:
                logger.warning(f"Payload too short for timestamp: {len(payload)} bytes")
                timestamp = datetime.now()
            
            # Data starts at byte 25
            data = payload[25:]
            
            return {
                "modem_id": modem_id,
                "device_id": device_id,
                "slave_id": slave_id,
                "timestamp": timestamp,
                "data": data,
                "raw_payload": payload.hex(),
            }
            
        except Exception as e:
            logger.error(f"Error parsing Alldatas payload: {e}")
            return None

    @staticmethod
    def try_parse_modbus_rtu_response(rtu: bytes) -> Optional[Dict[str, Any]]:
        """
        Try to parse a Modbus RTU response.
        
        RTU Response format:
        [0]     : slave address
        [1]     : function code
        [2]     : byte count (for FC 3/4)
        [3...]  : data bytes
        [n-1:n] : CRC (little-endian)
        
        Args:
            rtu: Modbus RTU response bytes
            
        Returns:
            Parsed data dict or None if invalid
        """
        if len(rtu) < 5:
            return None
        
        slave_addr = rtu[0]
        fc = rtu[1]
        
        # Check for exception response
        if fc & 0x80:
            logger.warning(f"Modbus exception: slave={slave_addr}, fc={fc & 0x7F}, code={rtu[2]}")
            return None
        
        # Only handle FC 3 and 4
        if fc not in (FC_READ_HOLDING_REGISTERS, FC_READ_INPUT_REGISTERS):
            return None
        
        # Validate byte count
        byte_count = rtu[2]
        expected_length = 3 + byte_count + 2  # addr + fc + count + data + crc
        
        if len(rtu) < expected_length:
            return None
        
        # Verify CRC (Modbus CRC is little-endian)
        crc_received = u16le(rtu[-2:])
        crc_calculated = crc16_modbus(rtu[:-2])
        
        if crc_received != crc_calculated:
            logger.warning(
                f"CRC mismatch: received={crc_received:04X}, calculated={crc_calculated:04X}"
            )
            # Continue anyway - some devices may have different CRC implementation
        
        # Parse register values
        data_bytes = rtu[3:3 + byte_count]
        registers = []
        
        for i in range(0, len(data_bytes), 2):
            if i + 1 < len(data_bytes):
                reg_value = u16be(data_bytes[i:i+2])
                registers.append(reg_value)
        
        return {
            "slave_addr": slave_addr,
            "fc": fc,
            "byte_count": byte_count,
            "registers": registers,
            "crc": crc_received,
        }

    @staticmethod
    def method_1(parsed: Dict[str, Any]) -> Optional[Tuple[int, int, int]]:
        """
        Method 1 parsing: Single register value.
        
        Returns:
            (fc, reg, value) or None
        """
        mb = ModbusParser.try_parse_modbus_rtu_response(parsed.get("data", b""))
        if not mb or not mb.get("registers"):
            return None
        
        fc = mb["fc"]
        value = mb["registers"][0]
        reg = int(parsed.get("slave_id", 0))
        
        return (fc, reg, value)

    @staticmethod
    def method_2(parsed: Dict[str, Any]) -> List[Tuple[int, int, int]]:
        """
        Method 2 parsing: Multiple register values.
        Reads multiple consecutive registers from a single Modbus response.
        
        Returns:
            List of (fc, reg, value) tuples where reg increments for each value
        """
        result = []
        mb = ModbusParser.try_parse_modbus_rtu_response(parsed.get("data", b""))
        if not mb or not mb.get("registers"):
            return result
        
        fc = mb["fc"]
        reg = int(parsed.get("slave_id", 0))
        
        # Increment register address for each value in the response
        for i, value in enumerate(mb["registers"]):
            result.append((fc, reg + i, value))
        
        return result

    @staticmethod
    def autodetect_method(parsed: Dict[str, Any]) -> Tuple[int, List[Tuple[int, int, int]]]:
        """
        Auto-detect parsing method.
        
        Returns:
            (method_no, triples) where triples is list of (fc, reg, value)
        """
        # Try method 1 first
        r1 = ModbusParser.method_1(parsed)
        if r1:
            return (1, [r1])
        
        # Try method 2
        r2 = ModbusParser.method_2(parsed)
        if r2:
            return (2, r2)
        
        return (0, [])

    @staticmethod
    def build_modbus_read(slave_addr: int, func: int, start_addr: int, count: int) -> bytes:
        """
        Build a Modbus read request PDU.
        
        Args:
            slave_addr: Slave address
            func: Function code (3 or 4)
            start_addr: Starting register address
            count: Number of registers to read
            
        Returns:
            Complete Modbus RTU frame with CRC
        """
        pdu = struct.pack(">BBHH", slave_addr, func, start_addr, count)
        crc = crc16_modbus(pdu)
        return pdu + struct.pack("<H", crc)

    @staticmethod
    def parse_command_payload(payload: bytes) -> Optional[Dict[str, Any]]:
        """
        Parse MQTT Commands topic payload.
        
        Args:
            payload: Raw MQTT payload bytes
            
        Returns:
            Parsed command dict or None if invalid
        """
        if len(payload) < 10:
            return None
        
        try:
            # Parse modem ID
            modem_id = payload[0:8].decode("ascii", errors="replace").strip()
            
            # Parse command
            cmd = u16be(payload[8:10])
            
            result = {
                "modem_id": modem_id,
                "command": cmd,
            }
            
            # Parse additional data based on command
            if len(payload) >= 12 and cmd == 11001:  # SLAVE_LIST
                idx = u16be(payload[10:12])
                result["index"] = idx
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing command payload: {e}")
            return None

    @staticmethod
    def normalize_reading(
        fc: int,
        reg: int,
        value: int,
        reg_offset: int = 0,
    ) -> Tuple[int, int, int]:
        """
        Normalize a reading with register offset.
        
        Args:
            fc: Function code
            reg: Original register address
            value: Register value
            reg_offset: Register offset to apply
            
        Returns:
            (fc, normalized_reg, value)
        """
        return (fc, reg + reg_offset, value)

    @staticmethod
    def apply_alias(
        fc: int,
        reg: int,
        alias_map: Dict[Tuple[int, int], Tuple[int, int]],
    ) -> List[Tuple[int, int]]:
        """
        Apply register alias mapping.
        
        Args:
            fc: Function code
            reg: Register address
            alias_map: Mapping of (fc, reg) -> (fc, reg)
            
        Returns:
            List of (fc, reg) tuples (original + aliases)
        """
        pairs = [(fc, reg)]
        
        key = (fc, reg)
        if key in alias_map:
            pairs.append(alias_map[key])
        
        return pairs


class RegisterMap:
    """
    Maps (fc, reg) tuples to column names.
    Loaded from database register_definitions table.
    """

    def __init__(self):
        self._map: Dict[Tuple[int, int], str] = {}

    def load_from_db(self, db_records: List[Dict[str, Any]]) -> None:
        """
        Load register mappings from database records.
        
        Args:
            db_records: List of dicts with 'fc', 'reg', 'name' keys
        """
        self._map.clear()
        for record in db_records:
            fc = int(record.get("fc", 0))
            reg = int(record.get("reg", 0))
            name = str(record.get("name", ""))
            self._map[(fc, reg)] = name
        
        logger.info(f"Loaded {len(self._map)} register mappings")

    def get_name(self, fc: int, reg: int) -> Optional[str]:
        """Get column name for a register."""
        return self._map.get((fc, reg))

    def has_register(self, fc: int, reg: int) -> bool:
        """Check if register is mapped."""
        return (fc, reg) in self._map


# Global register map instance
register_map = RegisterMap()


def get_register_map() -> RegisterMap:
    """Get the global register map instance."""
    return register_map

"""
Sumatic Modern IoT - MQTT Consumer
Async MQTT client that subscribes to device topics and processes messages.
Ported from original program.py MQTT logic to async architecture.
"""
import asyncio
import json
import struct
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, Set, Callable

import paho.mqtt.client as mqtt
from pytz import timezone
from sqlalchemy import select, and_

from app.config import get_settings
from app.database import async_session_maker
from app.models.device import Device
from app.models.reading import DeviceReading
from app.models.register_definition import RegisterDefinition
from app.services.modbus_parser import ModbusParser, get_register_map
from app.services.spike_filter import get_spike_filter
from app.services.websocket_manager import get_websocket_manager
from app.core.logging import get_logger
from app.api.v1.mqtt_logs import add_mqtt_log
from app.services.insertion_log import add_insertion_log

settings = get_settings()
logger = get_logger(__name__)

# Istanbul timezone
IST_TIMEZONE = timezone("Europe/Istanbul")

# Command constants
CMD_TIME_SYNC = 12790


class MQTTConsumer:
    """
    Async MQTT consumer that processes device messages.
    Runs as a background task in the FastAPI application.
    """

    def __init__(self):
        self._client: Optional[mqtt.Client] = None
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Device configuration cache: {(modem_id, device_addr): config}
        self._device_cfg: Dict[Tuple[str, int], Dict[str, Any]] = {}
        self._known_modems: Set[str] = set()
        
        # Runtime state per device_code
        self._cache: Dict[str, Dict[str, int]] = {}
        self._last_seen: Dict[str, float] = {}
        self._retry_count: Dict[str, int] = {}
        self._next_retry_at: Dict[str, float] = {}
        self._offline_reported: Dict[str, bool] = {}
        self._active_row_id: Dict[str, Optional[int]] = {}
        # DB kayıt throttle: her cihaz için son DB yazım zamanı
        self._last_saved: Dict[str, float] = {}
        # Kayıt aralığı (saniye) - 10 dakika
        self._save_interval: float = 10 * 60.0
        
        # Debounce mekanizması: iki register mesajı yakınsa tek bir DB yazma işlemi
        # Dict[device_code] -> pending asyncio.Task
        self._pending_saves: Dict[str, asyncio.Task] = {}
        # Debounce gecikme (saniye) - 2 register mesajının arasındaki maksimum süre
        self._debounce_delay: float = 2.0
        
        # Config reload cooldown to prevent excessive DB queries
        self._last_config_reload: float = 0.0
        
        # Callback for processing readings
        self._on_reading_callback: Optional[Callable] = None
        
        # Hourly status tracking
        # Dict[device_code] -> {"hour_start": datetime, "online_minutes": int, "offline_minutes": int, "data_points": int}
        self._hourly_tracking: Dict[str, Dict[str, Any]] = {}
        self._last_hourly_check: float = 0.0
        
        # 10-minute snapshot tracking
        # Dict[device_code] -> {"snapshot_time": datetime, "data_received": bool, "null_count": int}
        self._snapshot_tracking: Dict[str, Dict[str, Any]] = {}
        self._last_snapshot_check: float = 0.0
        self._snapshot_interval: float = 10 * 60.0  # 10 minutes
        
        # RAM optimizması: cache boyutunu sınırla
        self._max_cache_entries_per_device: int = 100  # Her cihaz için max 100 register
        self._last_cleanup_time: float = 0.0
        self._cleanup_interval: float = 3600.0  # 1 saatte bir temizlik

    async def start(self) -> None:
        """Start the MQTT consumer."""
        if self._running:
            logger.warning("MQTT consumer already running")
            return
        
        self._loop = asyncio.get_event_loop()
        self._running = True
        
        # Load device configurations
        await self._load_device_configs()
        
        # Load register map
        await self._load_register_map()
        
        # Determine port and TLS settings
        mqtt_port = settings.MQTT_TLS_PORT if settings.MQTT_TLS_ENABLED else settings.MQTT_BROKER_PORT
        use_tls = settings.MQTT_TLS_ENABLED
        
        # Create and configure MQTT client with unique client_id and clean_session=False
        # This prevents SSH channel leak by maintaining persistent session
        self._client = mqtt.Client(
            client_id=f"sumatic-{uuid.uuid4().hex[:8]}",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            clean_session=False,  # Maintain persistent session to prevent reconnect loops
        )
        
        # Set credentials if provided
        if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
            self._client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
        
        # Configure TLS/SSL if enabled
        if use_tls:
            try:
                # Set TLS options
                if settings.MQTT_TLS_CA_CERT:
                    # Use CA certificate for server verification
                    self._client.tls_set(
                        ca_certs=settings.MQTT_TLS_CA_CERT,
                        certfile=settings.MQTT_TLS_CLIENT_CERT,
                        keyfile=settings.MQTT_TLS_CLIENT_KEY,
                        cert_reqs=mqtt.ssl.CERT_REQUIRED if settings.MQTT_TLS_REQUIRE_CERT else mqtt.ssl.CERT_NONE,
                        tls_version=mqtt.ssl.PROTOCOL_TLS,
                    )
                    logger.info(f"MQTT TLS configured with CA cert: {settings.MQTT_TLS_CA_CERT}")
                else:
                    # Use default TLS context (for self-signed certs in development)
                    self._client.tls_set(
                        cert_reqs=mqtt.ssl.CERT_NONE if settings.MQTT_TLS_INSECURE else mqtt.ssl.CERT_REQUIRED,
                        tls_version=mqtt.ssl.PROTOCOL_TLS,
                    )
                    if settings.MQTT_TLS_INSECURE:
                        logger.warning("⚠️ MQTT TLS is running in INSECURE mode (certificate verification disabled)")
                    else:
                        logger.info("MQTT TLS configured with default system certificates")
                
                # Set TLS version and cipher options if needed
                self._client.tls_insecure_set(settings.MQTT_TLS_INSECURE)
                
            except Exception as e:
                logger.error(f"Failed to configure MQTT TLS: {e}")
                if not settings.DEBUG:
                    # In production, fail if TLS configuration fails
                    self._running = False
                    raise
        
        # Set callbacks
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect
        
        # Connect to broker with longer keepalive (3 minutes) to reduce ping frequency
        try:
            protocol_str = "TLS" if use_tls else "plain"
            self._client.connect(
                settings.MQTT_BROKER_HOST,
                mqtt_port,
                keepalive=180,  # 3 minutes - reduces tunnel stress
            )
            self._client.loop_start()
            logger.info(
                f"MQTT client connecting to {settings.MQTT_BROKER_HOST}:{mqtt_port} ({protocol_str})"
            )
        except Exception as e:
            logger.error(f"MQTT connection error: {e}")
            self._running = False
            raise
        
        # Start background monitoring task
        asyncio.create_task(self._monitor_loop())

    async def stop(self) -> None:
        """Stop the MQTT consumer."""
        self._running = False
        
        if self._client:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception as e:
                logger.error(f"Error stopping MQTT client: {e}")
            self._client = None
        
        logger.info("MQTT consumer stopped")

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        """MQTT on_connect callback."""
        if reason_code == 0:
            logger.info("MQTT broker connected successfully")
            add_mqtt_log("info", "✅ MQTT broker bağlantısı başarılı")
            
            # Subscribe to topics
            client.subscribe(settings.MQTT_TOPIC_ALLDATAS)
            client.subscribe(settings.MQTT_TOPIC_COMMANDS)
            client.subscribe(f"{settings.MQTT_TOPIC_COMMANDS}/#")
            
            logger.info(
                f"Subscribed to: {settings.MQTT_TOPIC_ALLDATAS}, "
                f"{settings.MQTT_TOPIC_COMMANDS}, "
                f"{settings.MQTT_TOPIC_COMMANDS}/#"
            )
            add_mqtt_log("info", f"📡 Konular (topics) abone: {settings.MQTT_TOPIC_ALLDATAS}, {settings.MQTT_TOPIC_COMMANDS}")
        else:
            logger.error(f"MQTT connection failed: {reason_code}")
            add_mqtt_log("error", f"❌ MQTT bağlantı başarısız: Kod {reason_code}")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        """MQTT on_disconnect callback."""
        logger.warning(f"MQTT disconnected: {reason_code}")
        add_mqtt_log("warning", f"⚠️ MQTT bağlantısı kesildi: Kod {reason_code}")
        if self._running:
            logger.info("MQTT will auto-reconnect...")
            add_mqtt_log("info", "🔄 MQTT otomatik yeniden bağlanıyor...")

    def _on_message(self, client, userdata, msg):
        """
        MQTT on_message callback.
        Delegates to async processing via event loop.
        """
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._process_message(msg.topic, msg.payload),
                self._loop,
            )

    async def _process_message(self, topic: str, payload: bytes) -> None:
        """
        Process an incoming MQTT message.
        
        Args:
            topic: MQTT topic
            payload: Message payload
        """
        try:
            # Handle command messages
            commands_topic = settings.MQTT_TOPIC_COMMANDS
            if topic == commands_topic or topic.startswith(f"{commands_topic}/"):
                await self._handle_commands(payload)
                return
            
            # Handle Alldatas messages
            if topic == settings.MQTT_TOPIC_ALLDATAS:
                await self._handle_alldatas(payload)
                return
            
        except Exception as e:
            logger.error(f"Error processing MQTT message on {topic}: {e}")

    async def _handle_commands(self, payload: bytes) -> None:
        """
        Handle Commands topic messages.
        
        Note: Only responds to time sync requests. Slave list commands are
        no longer sent as modems are pre-configured on the remote server.
        """
        if len(payload) < 10:
            return
        
        parsed = ModbusParser.parse_command_payload(payload)
        if not parsed:
            return
        
        modem_id = parsed["modem_id"]
        cmd = parsed["command"]
        
        # Only respond to known modems
        if modem_id not in self._known_modems:
            return
        
        topic_to_modem = f"{settings.MQTT_TOPIC_COMMANDS}/{modem_id}"
        
        if cmd == CMD_TIME_SYNC:
            resp = self._build_time_sync_response(datetime.now())
            self._client.publish(topic_to_modem, resp, qos=0)
            return

    async def _handle_alldatas(self, payload: bytes) -> None:
        """Handle Alldatas topic messages - main data processing."""
        parsed = ModbusParser.parse_alldatas(payload)
        if not parsed:
            # Log parse failure
            add_mqtt_log("warning", "Failed to parse Alldatas payload", data={"payload_length": len(payload)})
            return
        
        modem_id = parsed["modem_id"]
        addr = int(parsed["device_id"])
        
        # Skip slave list responses (addr > 1000000 indicates slave list response)
        if addr > 1000000:
            logger.debug(f"Skipping slave list response: modem={modem_id} addr={addr}")
            return
        
        # Log incoming data - ham payload bilgisi
        ts = parsed.get("timestamp")
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if ts else "?"
        add_mqtt_log("info", f"Received Alldatas message", modem_id=modem_id, data={
            "device_addr": addr,
            "device_timestamp": ts_str,
            "payload_size": len(payload),
            "raw_hex_preview": payload[:16].hex() if len(payload) >= 16 else payload.hex()
        })
        
        # Look up device configuration
        cfg = self._device_cfg.get((modem_id, addr))
        
        if not cfg:
            # Check cooldown before reloading configs
            now = time.time()
            if now - self._last_config_reload > 30:  # 30 second cooldown
                await self._load_device_configs()
                self._last_config_reload = now
                cfg = self._device_cfg.get((modem_id, addr))
            
            if not cfg:
                logger.warning(
                    f"Unknown device: modem={modem_id} addr={addr}"
                )
                # Log unknown device
                add_mqtt_log("warning", f"Unknown device: modem={modem_id} addr={addr}", modem_id=modem_id, data={"device_addr": addr})
                return
        
        device_id = cfg["device_id"]
        device_code = cfg["device_code"]
        
        # Ensure runtime state
        self._ensure_runtime_state(device_code)
        
        method_no = int(cfg.get("method_no", 0))
        
        # Auto-detect method if not set
        if method_no == 0:
            detected_method, triples = ModbusParser.autodetect_method(parsed)
            if detected_method == 0:
                return
            
            method_no = detected_method
            cfg["method_no"] = detected_method
            
            # Update method_no in database
            await self._update_method_no(modem_id, addr, detected_method)
            
            logger.info(f"Auto-detected method {method_no} for ({modem_id}, {addr})")
        
        # Parse data based on method
        wrote_any = False
        register_map = get_register_map()
        spike_filter = get_spike_filter()
        
        # Debug: Log parsing attempt
        logger.debug(f"{device_code}: Parsing with method_no={method_no}, data_len={len(parsed.get('data', b''))}")
        
        if method_no == 1:
            result = ModbusParser.method_1(parsed)
            if not result:
                logger.debug(f"{device_code}: Method 1 returned None, data={parsed.get('data', b'').hex()}")
                return
            fc, reg, val = result
            logger.debug(f"{device_code}: Method 1 result: fc={fc}, reg={reg}, val={val}")
            wrote_any = self._normalize_and_write(
                device_id, device_code, cfg, fc, reg, val,
                register_map, spike_filter,
            )
        
        elif method_no == 2:
            triples = ModbusParser.method_2(parsed)
            if not triples:
                logger.debug(f"{device_code}: Method 2 returned None/empty, data={parsed.get('data', b'').hex()}")
                return
            # method_2 returns list of (fc, reg, value) tuples
            # Process each register value
            logger.debug(f"{device_code}: Method 2 returned {len(triples)} triples")
            for fc, reg, val in triples:
                logger.debug(f"{device_code}: Processing triple: fc={fc}, reg={reg}, val={val}")
                if self._normalize_and_write(
                    device_id, device_code, cfg, fc, reg, val,
                    register_map, spike_filter,
                ):
                    wrote_any = True
        
        # Log if nothing was written
        if not wrote_any:
            logger.warning(f"{device_code}: No data written! method_no={method_no}, data={parsed.get('data', b'').hex()}")
            add_mqtt_log("warning", f"No data written for {device_code}", device_code=device_code, modem_id=modem_id, data={
                "method_no": method_no,
                "data_hex": parsed.get('data', b'').hex()[:100]
            })
        
        if wrote_any:
            self._last_seen[device_code] = time.time()
            await self._reset_online(device_code)
            
            # Update hourly data points counter
            if device_code in self._hourly_tracking:
                self._hourly_tracking[device_code]["data_points"] += 1
            
            # Her mesajda debounce ile kaydet - 2 saniye bekle, ikinci register'ı bekle
            # Eğer 2 saniye içinde yeni mesaj gelirse, önceki task iptal edilir ve yeniden başlar
            now = time.time()
            
            # Cancel any pending debounce task for this device
            existing_task = self._pending_saves.get(device_code)
            if existing_task and not existing_task.done():
                existing_task.cancel()
                logger.debug(f"{device_code}: Cancelled previous pending save, rescheduling")
            
            # Schedule a debounced save: wait briefly for more register messages
            # This allows both registers (19L and 5L) to arrive before saving
            async def _debounced_save(dev_id: int, dev_code: str) -> None:
                try:
                    await asyncio.sleep(self._debounce_delay)
                    await self._save_reading(dev_id, dev_code)
                    logger.debug(f"{dev_code}: Data saved to DB (debounced)")
                except asyncio.CancelledError:
                    pass  # Task was cancelled because a newer message arrived
                except Exception as e:
                    logger.error(f"Error in debounced save for {dev_code}: {e}")
                finally:
                    # Clean up from pending dict
                    self._pending_saves.pop(dev_code, None)
            
            task = asyncio.create_task(_debounced_save(device_id, device_code))
            self._pending_saves[device_code] = task
            
            # Update device last_seen (always update, not throttled)
            await self._update_device_last_seen(device_id)
            
            # Broadcast via WebSocket (only counter data)
            try:
                ws_manager = get_websocket_manager()
                cached_data = self._cache.get(device_code, {})
                counter_data = {
                    "Sayac 1": cached_data.get("Sayac 1"),
                    "Sayac 2": cached_data.get("Sayac 2"),
                }
                await ws_manager.broadcast_reading(device_id, counter_data)
            except Exception as e:
                logger.error(f"Error broadcasting reading for device {device_code}: {e}", exc_info=True)
            
            # Log successful data processing
            cached_data = self._cache.get(device_code, {})
            add_mqtt_log("info", f"Data saved for {device_code}", device_code=device_code, modem_id=modem_id, data={
                "cache": cached_data,
                "method_no": method_no
            })

    def _normalize_and_write(
        self,
        device_id: int,
        device_code: str,
        cfg: Dict[str, Any],
        fc: int,
        reg: int,
        val: int,
        register_map,
        spike_filter,
    ) -> bool:
        """
        Normalize reading and write to cache.
        Applies register offset, skip, alias, and spike filter.
        """
        # Apply register offset
        offset = int(cfg.get("reg_offset_by_fc", {}).get(fc, 0))
        reg = reg + offset
        
        # Check skip list
        skip_raw = cfg.get("skip_raw", set())
        if (fc, reg) in skip_raw:
            return False
        
        # Get register pairs (original + aliases)
        alias_map = cfg.get("alias_map", {})
        pairs = ModbusParser.apply_alias(fc, reg, alias_map)
        
        wrote_any = False
        
        for fc2, reg2 in pairs:
            col_name = register_map.get_name(fc2, reg2)
            if not col_name:
                logger.debug(f"{device_code}: No register mapping for fc={fc2}, reg={reg2}")
                continue
            
            # Apply spike filter
            if not spike_filter.is_valid(device_id, col_name, val):
                logger.debug(f"SPIKE rejected: device={device_code} {col_name}={val}")
                continue
            
            # Write to cache (with RAM protection)
            if device_code not in self._cache:
                self._cache[device_code] = {}
            
            # RAM koruması: cihaz başına max kayıt sınırını aşarsa eski değerleri temizle
            if len(self._cache[device_code]) >= self._max_cache_entries_per_device:
                # En eski yarısını sil
                keys_to_remove = list(self._cache[device_code].keys())[:self._max_cache_entries_per_device // 2]
                for old_key in keys_to_remove:
                    del self._cache[device_code][old_key]
                logger.debug(f"{device_code}: Cache trimmed, removed {len(keys_to_remove)} old entries")
            
            self._cache[device_code][col_name] = int(val)
            logger.debug(f"{device_code} {col_name}={val} (fc={fc2}, reg={reg2})")
            wrote_any = True
        
        return wrote_any

    async def _save_reading(self, device_id: int, device_code: str) -> None:
        """Save current cache to database as a reading - SADECE SAYAÇLAR.
        
        Her 10 dakikalık zaman dilimi için ayrı kayıt oluşturur.
        Zaman dilimleri: 11:40, 11:50, 12:00, 12:10...
        
        Mantık:
        - Şu anki zamanın 10 dakikalık dilimini hesapla (örn: 11:47 → 11:40)
        - Bu dilim için kayıt varsa: eksik sayaçları tamamla
        - Bu dilim için kayıt yoksa: yeni kayıt oluştur
        """
        cache_data = self._cache.get(device_code, {})
        if not cache_data:
            return
        
        # Sadece sayaç verilerini al (Türkçe isimler)
        counter_19l = cache_data.get("Sayac 1")
        counter_5l = cache_data.get("Sayac 2")
        
        # En az bir sayaç değeri olmalı
        if counter_19l is None and counter_5l is None:
            logger.debug(f"{device_code}: Skipping save - no counter data")
            return
        
        try:
            async with async_session_maker() as session:
                now = datetime.now(IST_TIMEZONE)
                
                # 10 dakikalık zaman dilimini hesapla
                # Örnek: 11:47 → 11:40, 11:53 → 11:50
                minutes = now.minute
                interval_minutes = int(self._save_interval / 60)  # 10 dakika
                floored_minutes = (minutes // interval_minutes) * interval_minutes
                time_slot = now.replace(minute=floored_minutes, second=0, microsecond=0)
                
                # Bu zaman dilimi için kayıt var mı kontrol et
                # time_slot'dan time_slot + 10 dakika arasını ara
                slot_end = time_slot + timedelta(seconds=self._save_interval)
                
                result = await session.execute(
                    select(DeviceReading)
                    .where(DeviceReading.device_id == device_id)
                    .where(DeviceReading.timestamp >= time_slot)
                    .where(DeviceReading.timestamp < slot_end)
                    .order_by(DeviceReading.timestamp.desc())
                    .limit(1)
                )
                existing_reading = result.scalar_one_or_none()
                
                if existing_reading:
                    # Bu zaman dilimi için kayıt var - sadece eksik sayaçları tamamla
                    updated = False
                    if counter_19l is not None and existing_reading.counter_19l is None:
                        existing_reading.counter_19l = int(counter_19l)
                        updated = True
                        logger.debug(f"{device_code}: Filled missing 19L counter - 19L={counter_19l}")
                    if counter_5l is not None and existing_reading.counter_5l is None:
                        existing_reading.counter_5l = int(counter_5l)
                        updated = True
                        logger.debug(f"{device_code}: Filled missing 5L counter - 5L={counter_5l}")
                    
                    if updated:
                        logger.info(
                            f"{device_code}: Updated reading in slot {time_slot.strftime('%H:%M')} "
                            f"- 19L={existing_reading.counter_19l}, 5L={existing_reading.counter_5l}"
                        )
                    else:
                        # Her iki sayaç da zaten dolu
                        logger.debug(
                            f"{device_code}: Both counters already present in slot {time_slot.strftime('%H:%M')}"
                        )
                else:
                    # Bu zaman dilimi için kayıt yok → yeni kayıt oluştur
                    # Status belirle: cihazın son görülme zamanına göre
                    last_seen = self._last_seen.get(device_code, 0.0)
                    now = time.time()
                    age = now - last_seen
                    is_online = last_seen > 0 and age <= settings.DEVICE_OFFLINE_THRESHOLD_SECONDS
                    reading_status = "online" if is_online else "offline"
                    
                    reading = DeviceReading(
                        device_id=device_id,
                        timestamp=time_slot,
                        counter_19l=int(counter_19l) if counter_19l is not None else None,
                        counter_5l=int(counter_5l) if counter_5l is not None else None,
                        status=reading_status
                    )
                    session.add(reading)
                    logger.info(
                        f"{device_code}: New reading created for slot {time_slot.strftime('%H:%M')} "
                        f"- 19L={counter_19l}, 5L={counter_5l}, status={reading.status}"
                    )
                    # Log insertion to live_data
                    try:
                        add_insertion_log(
                            device_id=device_id,
                            device_code=device_code,
                            timestamp=time_slot,
                            counter_19l=int(counter_19l) if counter_19l is not None else None,
                            counter_5l=int(counter_5l) if counter_5l is not None else None,
                            status=reading_status
                        )
                    except Exception as log_err:
                        logger.debug(f"Insertion log error (non-critical): {log_err}")
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error saving reading for device {device_code}: {e}")

    async def _update_device_last_seen(self, device_id: int) -> None:
        """Update device last_seen_at timestamp."""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(Device).where(Device.id == device_id)
                )
                device = result.scalar_one_or_none()
                if device:
                    device.last_seen_at = datetime.now(IST_TIMEZONE)
                    device.is_pending = False
                    await session.commit()
        except Exception as e:
            logger.error(f"Error updating last_seen for device {device_id}: {e}")

    async def _update_method_no(
        self, modem_id: str, device_addr: int, method_no: int
    ) -> None:
        """Update method_no in database."""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(Device).where(
                        and_(
                            Device.modem_id == modem_id,
                            Device.device_addr == device_addr,
                        )
                    )
                )
                device = result.scalar_one_or_none()
                if device:
                    device.method_no = method_no
                    await session.commit()
        except Exception as e:
            logger.error(f"Error updating method_no: {e}")

    def _ensure_runtime_state(self, device_code: str) -> None:
        """Ensure runtime state dicts are initialized for a device."""
        if device_code not in self._cache:
            self._cache[device_code] = {}
        if device_code not in self._last_seen:
            self._last_seen[device_code] = 0.0
        if device_code not in self._retry_count:
            self._retry_count[device_code] = 0
        if device_code not in self._next_retry_at:
            self._next_retry_at[device_code] = 0.0
        if device_code not in self._offline_reported:
            self._offline_reported[device_code] = False
        if device_code not in self._active_row_id:
            self._active_row_id[device_code] = None
        if device_code not in self._last_saved:
            self._last_saved[device_code] = 0.0

    async def _reset_online(self, device_code: str) -> None:
        """Reset online status for a device and broadcast status change."""
        was_offline = self._offline_reported.get(device_code, False)
        self._retry_count[device_code] = 0
        self._next_retry_at[device_code] = 0.0
        self._offline_reported[device_code] = False
        
        # Broadcast status change if device was offline
        if was_offline:
            ws_manager = get_websocket_manager()
            
            # Find device_id from config
            device_id = None
            for (mid, addr), cfg in self._device_cfg.items():
                if cfg.get("device_code") == device_code:
                    device_id = cfg.get("device_id")
                    break
            
            if device_id:
                await ws_manager.broadcast_status_change(
                    device_id=device_id,
                    status="ONLINE",
                    previous_status="OFFLINE",
                )
                logger.info(f"{device_code} back online - status broadcast sent")

    def _schedule_retry(self, device_code: str) -> None:
        """Schedule a retry for a device."""
        self._retry_count[device_code] = self._retry_count.get(device_code, 0) + 1
        self._next_retry_at[device_code] = (
            time.time() + settings.DEVICE_RETRY_INTERVAL_SECONDS
        )

    async def _mark_offline(self, device_code: str) -> None:
        """Mark a device as offline."""
        if not self._offline_reported.get(device_code, False):
            self._offline_reported[device_code] = True
            logger.warning(
                f"DEVICE OFFLINE: {device_code} ({settings.DEVICE_MAX_RETRIES} retries failed)"
            )
            
            # Broadcast alert via WebSocket
            ws_manager = get_websocket_manager()
            
            # Find device_id from config
            device_id = None
            for (mid, addr), cfg in self._device_cfg.items():
                if cfg.get("device_code") == device_code:
                    device_id = cfg.get("device_id")
                    break
            
            if device_id:
                await ws_manager.broadcast_status_change(
                    device_id=device_id,
                    status="OFFLINE",
                    previous_status="ONLINE",
                )
                await ws_manager.broadcast_alert(
                    alert_type="device_offline",
                    title=f"Cihaz Çevrimdışı: {device_code}",
                    message=f"{device_code} cihazı {settings.DEVICE_MAX_RETRIES} deneme sonunda çevrimdışı olarak işaretlendi.",
                    device_id=device_id,
                    severity="warning",
                )

    def _build_time_sync_response(self, now: datetime) -> bytes:
        """Build time sync response."""
        yy = now.year % 100
        return struct.pack(
            ">HBBBBBBB",
            CMD_TIME_SYNC,
            0x06,
            now.second,
            now.minute,
            now.hour,
            now.day,
            now.month,
            yy,
        )

    async def _load_device_configs(self) -> None:
        """Load device configurations from database."""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(Device).where(Device.is_enabled == True)
                )
                devices = result.scalars().all()
                
                self._device_cfg.clear()
                self._known_modems.clear()
                
                for device in devices:
                    modem_id = device.modem_id
                    addr = device.device_addr
                    
                    # Parse JSON configs - handle both dict and string types
                    reg_offset = device.reg_offset_json or {}
                    if isinstance(reg_offset, str):
                        try:
                            reg_offset = json.loads(reg_offset)
                        except (json.JSONDecodeError, TypeError):
                            reg_offset = {}
                    reg_offset_by_fc = {int(k): int(v) for k, v in (reg_offset or {}).items()}
                    
                    alias_raw = device.alias_json or {}
                    if isinstance(alias_raw, str):
                        try:
                            alias_raw = json.loads(alias_raw)
                        except (json.JSONDecodeError, TypeError):
                            alias_raw = {}
                    alias_map = {}
                    for k, v in (alias_raw or {}).items():
                        try:
                            fc1, reg1 = k.split(":")
                            fc2, reg2 = v.split(":")
                            alias_map[(int(fc1), int(reg1))] = (int(fc2), int(reg2))
                        except (ValueError, AttributeError):
                            continue
                    
                    skip_raw = set()
                    skip_raw_list = device.skip_raw_json or []
                    if isinstance(skip_raw_list, str):
                        try:
                            skip_raw_list = json.loads(skip_raw_list)
                        except (json.JSONDecodeError, TypeError):
                            skip_raw_list = []
                    for item in (skip_raw_list or []):
                        try:
                            if isinstance(item, str) and ":" in item:
                                fc_s, reg_s = item.split(":")
                                skip_raw.add((int(fc_s), int(reg_s)))
                        except (ValueError, AttributeError):
                            continue
                    
                    self._device_cfg[(modem_id, addr)] = {
                        "device_id": device.id,
                        "device_code": device.device_code,
                        "method_no": device.method_no,
                        "reg_offset_by_fc": reg_offset_by_fc,
                        "alias_map": alias_map,
                        "skip_raw": skip_raw,
                    }
                    self._known_modems.add(modem_id)
                    self._ensure_runtime_state(device.device_code)
                
                logger.info(
                    f"Loaded {len(self._device_cfg)} device configs, "
                    f"{len(self._known_modems)} known modems"
                )
                # Log device details
                for (mid, addr), cfg in self._device_cfg.items():
                    logger.info(
                        f"  Device: code={cfg['device_code']} modem={mid} addr={addr} "
                        f"method={cfg['method_no']} alias={cfg['alias_map']} skip={cfg['skip_raw']}"
                    )
                
        except Exception as e:
            logger.error(f"Error loading device configs: {e}")

    async def _load_last_save_timestamps(self) -> None:
        """Sunucu restart sonrası _last_saved sözlüğünü DB'den doldur.
        
        Bu sayede restart sonrası gelen MQTT mesajları throttle kontrolüne takılır
        ve duplicate kayıt oluşturmaz.
        """
        try:
            async with async_session_maker() as session:
                # Her cihaz için en son kayıt zamanını çek
                for (modem_id, addr), cfg in self._device_cfg.items():
                    device_id = cfg["device_id"]
                    device_code = cfg["device_code"]
                    
                    result = await session.execute(
                        select(DeviceReading)
                        .where(DeviceReading.device_id == device_id)
                        .order_by(DeviceReading.timestamp.desc())
                        .limit(1)
                    )
                    last_reading = result.scalar_one_or_none()
                    
                    if last_reading and last_reading.timestamp:
                        # timestamp'i unix time'a çevir
                        import pytz
                        ts = last_reading.timestamp
                        if ts.tzinfo is None:
                            # timezone-naive → IST olarak kabul et
                            ts = IST_TIMEZONE.localize(ts)
                        last_saved_unix = ts.timestamp()
                        self._last_saved[device_code] = last_saved_unix
                        logger.debug(
                            f"{device_code}: Loaded last_saved from DB: "
                            f"{last_reading.timestamp} (unix={last_saved_unix:.0f})"
                        )
                    
        except Exception as e:
            logger.error(f"Error loading last save timestamps: {e}")

    async def _load_register_map(self) -> None:
        """Load register definitions from database."""
        try:
            async with async_session_maker() as session:
                result = await session.execute(select(RegisterDefinition))
                records = result.scalars().all()
                
                register_map = get_register_map()
                register_map.load_from_db([
                    {"fc": r.fc, "reg": r.reg, "name": r.name}
                    for r in records
                ])
                
        except Exception as e:
            logger.error(f"Error loading register map: {e}")

    async def _monitor_loop(self) -> None:
        """
        Background monitoring loop for device health.
        
        Note: Modems are pre-configured on the remote server and continuously
        push data to MQTT broker. We operate in passive listening mode only,
        no active polling via CMD_SLAVE_LIST commands.
        """
        logger.info("MQTT monitor loop started (passive listening mode)")
        
        while self._running:
            try:
                now = time.time()
                
                # Get all configured device codes
                all_device_codes = set()
                for (modem_id, addr), cfg in self._device_cfg.items():
                    all_device_codes.add(cfg["device_code"])
                
                # Check each device's health
                for device_code in all_device_codes:
                    age = now - self._last_seen.get(device_code, 0.0)
                    
                    # Check if data is stale (including never-seen devices)
                    stale_threshold = settings.DEVICE_OFFLINE_THRESHOLD_SECONDS
                    if self._last_seen.get(device_code, 0.0) == 0 or age > stale_threshold:
                        if self._retry_count.get(device_code, 0) == 0:
                            self._schedule_retry(device_code)
                            logger.info(
                                f"{device_code} data stale. Starting retries "
                                f"({settings.DEVICE_MAX_RETRIES} max)"
                            )
                    
                    # Handle retries
                    retries = self._retry_count.get(device_code, 0)
                    max_retries = settings.DEVICE_MAX_RETRIES
                    next_retry = self._next_retry_at.get(device_code, 0.0)
                    
                    if retries > 0 and retries <= max_retries and now >= next_retry:
                        age = now - self._last_seen.get(device_code, 0.0)
                        
                        if self._last_seen.get(device_code, 0.0) > 0 and age <= stale_threshold:
                            await self._reset_online(device_code)
                        else:
                            if retries < max_retries:
                                self._schedule_retry(device_code)
                                logger.info(f"Retry {retries}/{max_retries} -> {device_code}")
                            else:
                                await self._mark_offline(device_code)
                
                # Update hourly status tracking (every 60 seconds)
                if now - self._last_hourly_check >= 60.0:
                    await self._update_hourly_status(all_device_codes)
                    self._last_hourly_check = now
                
                # Update 10-minute snapshot tracking (every 10 minutes)
                if now - self._last_snapshot_check >= self._snapshot_interval:
                    await self._update_snapshots(all_device_codes)
                    self._last_snapshot_check = now
                
                # RAM optimizasyonu: Periyodik temizlik (her saat)
                if now - self._last_cleanup_time >= self._cleanup_interval:
                    await self._cleanup_old_data()
                    
                    # WebSocket stale connection cleanup
                    try:
                        from app.services.websocket_manager import get_websocket_manager
                        ws_manager = get_websocket_manager()
                        await ws_manager.cleanup_stale_connections()
                    except Exception as e:
                        logger.error(f"Error cleaning up WebSocket connections: {e}")
                    
                    self._last_cleanup_time = now
                
            except Exception as e:
                logger.error(f"Error in MQTT monitor loop: {e}")
            
            await asyncio.sleep(1)
        
        logger.info("MQTT monitor loop stopped")

    async def _update_hourly_status(self, device_codes: Set[str]) -> None:
        """
        Update hourly status tracking for all devices.
        Called every 60 seconds. When hour boundary is crossed, saves previous hour's data.
        
        For each device and hour:
        - Count readings where status='online' as online_minutes
        - Count readings where status='offline' as offline_minutes
        - Total readings = data_points
        """
        now_ist = datetime.now(IST_TIMEZONE)
        current_hour_start = now_ist.replace(minute=0, second=0, microsecond=0)
        
        for device_code in device_codes:
            try:
                # Get device_id from config
                device_id = None
                for (modem_id, addr), cfg in self._device_cfg.items():
                    if cfg["device_code"] == device_code:
                        device_id = cfg.get("device_id")
                        break
                
                if not device_id:
                    continue
                
                # Initialize tracking for this device if not exists
                if device_code not in self._hourly_tracking:
                    self._hourly_tracking[device_code] = {
                        "hour_start": current_hour_start,
                        "online_minutes": 0,
                        "offline_minutes": 0,
                        "data_points": 0
                    }
                
                tracking = self._hourly_tracking[device_code]
                
                # Check if we've moved to a new hour
                if tracking["hour_start"] < current_hour_start:
                    # Save the PREVIOUS hour's data to database
                    await self._save_hourly_status(device_id, device_code, tracking)
                    
                    # Reset tracking for new hour
                    self._hourly_tracking[device_code] = {
                        "hour_start": current_hour_start,
                        "online_minutes": 0,
                        "offline_minutes": 0,
                        "data_points": 0
                    }
                    tracking = self._hourly_tracking[device_code]
                
                # Count all readings in the current hour by status
                # This increments the counters each time we check (every 60s)
                async with async_session_maker() as session:
                    from app.models.reading import DeviceReading
                    from sqlalchemy import select, func
                    
                    hour_start = tracking["hour_start"]
                    hour_end = hour_start + timedelta(hours=1)
                    
                    # Get count of online readings in current hour
                    online_result = await session.execute(
                        select(func.count(DeviceReading.id))
                        .where(DeviceReading.device_id == device_id)
                        .where(DeviceReading.timestamp >= hour_start)
                        .where(DeviceReading.timestamp < hour_end)
                        .where(DeviceReading.status == "online")
                    )
                    online_count = online_result.scalar() or 0
                    
                    # Get count of offline readings in current hour
                    offline_result = await session.execute(
                        select(func.count(DeviceReading.id))
                        .where(DeviceReading.device_id == device_id)
                        .where(DeviceReading.timestamp >= hour_start)
                        .where(DeviceReading.timestamp < hour_end)
                        .where(DeviceReading.status == "offline")
                    )
                    offline_count = offline_result.scalar() or 0
                    
                    total_count = online_count + offline_count
                    
                    # Update tracking with current hour counts
                    tracking["online_minutes"] = online_count
                    tracking["offline_minutes"] = offline_count
                    tracking["data_points"] = total_count
                
            except Exception as e:
                logger.error(f"Error updating hourly status for {device_code}: {e}")
    
    async def _save_hourly_status(
        self,
        device_id: int,
        device_code: str,
        tracking: Dict[str, Any]
    ) -> None:
        """
        Save hourly status data to database.
        """
        try:
            from app.models.device_status import DeviceHourlyStatus
            
            hour_start = tracking["hour_start"]
            hour_end = hour_start + timedelta(hours=1)
            
            # Determine status based on online/offline minutes
            online_mins = tracking["online_minutes"]
            offline_mins = tracking["offline_minutes"]
            data_points = tracking["data_points"]
            
            if online_mins >= 55:  # More than 55 minutes online
                status = "ONLINE"
            elif offline_mins >= 55:  # More than 55 minutes offline
                status = "OFFLINE"
            else:
                status = "PARTIAL"
            
            async with async_session_maker() as session:
                # Check if record already exists
                from sqlalchemy import select
                stmt = select(DeviceHourlyStatus).where(
                    DeviceHourlyStatus.device_id == device_id,
                    DeviceHourlyStatus.hour_start == hour_start
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()
                
                if existing:
                    # Update existing record
                    existing.status = status
                    existing.online_minutes = online_mins
                    existing.offline_minutes = offline_mins
                    existing.data_points = data_points
                    existing.updated_at = datetime.utcnow()
                else:
                    # Create new record
                    hourly_status = DeviceHourlyStatus(
                        device_id=device_id,
                        hour_start=hour_start,
                        hour_end=hour_end,
                        status=status,
                        online_minutes=online_mins,
                        offline_minutes=offline_mins,
                        data_points=data_points
                    )
                    session.add(hourly_status)
                
                await session.commit()
                logger.debug(
                    f"Saved hourly status for {device_code}: {status} "
                    f"(online: {online_mins}m, offline: {offline_mins}m, points: {data_points})"
                )
                
        except Exception as e:
            logger.error(f"Error saving hourly status for {device_code}: {e}")
    
    async def _update_snapshots(self, device_codes: Set[str]) -> None:
        """
        Update 10-minute snapshot tracking for all devices.
        Called every 10 minutes to track device status.
        Status is determined from device_readings table based on counter values.
        """
        now_ist = datetime.now(IST_TIMEZONE)
        
        # Calculate current 10-minute slot
        minutes = now_ist.minute
        interval_minutes = 10
        floored_minutes = (minutes // interval_minutes) * interval_minutes
        current_snapshot_time = now_ist.replace(minute=floored_minutes, second=0, microsecond=0)
        
        for device_code in device_codes:
            try:
                # Get device_id from config
                device_id = None
                for (modem_id, addr), cfg in self._device_cfg.items():
                    if cfg["device_code"] == device_code:
                        device_id = cfg.get("device_id")
                        break
                
                if not device_id:
                    continue
                
                # Initialize tracking for this device if not exists
                if device_code not in self._snapshot_tracking:
                    self._snapshot_tracking[device_code] = {
                        "snapshot_time": current_snapshot_time,
                        "data_received": False,
                        "null_count": 0
                    }
                
                tracking = self._snapshot_tracking[device_code]
                
                # Check if we've moved to a new 10-minute slot
                if tracking["snapshot_time"] < current_snapshot_time:
                    # Save the previous snapshot to database
                    await self._save_snapshot(device_id, device_code, tracking)
                    
                    # Reset tracking for new slot
                    self._snapshot_tracking[device_code] = {
                        "snapshot_time": current_snapshot_time,
                        "data_received": False,
                        "null_count": 0
                    }
                    tracking = self._snapshot_tracking[device_code]
                
                # Get status from device_readings table (last reading in current 10-minute slot)
                slot_end = current_snapshot_time + timedelta(minutes=interval_minutes)
                
                async with async_session_maker() as session:
                    from app.models.reading import DeviceReading
                    from sqlalchemy import select
                    
                    # Get the most recent reading in the current 10-minute slot
                    result = await session.execute(
                        select(DeviceReading)
                        .where(DeviceReading.device_id == device_id)
                        .where(DeviceReading.timestamp >= current_snapshot_time)
                        .where(DeviceReading.timestamp < slot_end)
                        .order_by(DeviceReading.timestamp.desc())
                        .limit(1)
                    )
                    latest_reading = result.scalar_one_or_none()
                    
                    if latest_reading:
                        # Use status from device_readings table
                        if latest_reading.status == "online":
                            tracking["data_received"] = True
                        elif latest_reading.status == "offline":
                            tracking["data_received"] = False
                        
                        # Check for null readings
                        if latest_reading.counter_19l is None and latest_reading.counter_5l is None:
                            tracking["null_count"] += 1
                    else:
                        # No reading yet this slot, check last_seen for fallback
                        last_seen = self._last_seen.get(device_code, 0.0)
                        if last_seen > 0:
                            age = time.time() - last_seen
                            is_online = age <= settings.DEVICE_OFFLINE_THRESHOLD_SECONDS
                            if is_online:
                                tracking["data_received"] = True
                
            except Exception as e:
                logger.error(f"Error updating snapshot for {device_code}: {e}")
    
    async def _save_snapshot(
        self,
        device_id: int,
        device_code: str,
        tracking: Dict[str, Any]
    ) -> None:
        """
        Save 10-minute snapshot data to database.
        """
        try:
            from app.models.device_status import DeviceStatusSnapshot
            
            snapshot_time = tracking["snapshot_time"]
            data_received = tracking["data_received"]
            null_count = tracking["null_count"]
            
            # Determine status: OFFLINE if no data received or high null count
            if not data_received or null_count >= 3:  # No data for 10 minutes or mostly nulls
                status = "OFFLINE"
            else:
                status = "ONLINE"
            
            # Get last_seen timestamp
            last_seen_ts = None
            last_seen_unix = self._last_seen.get(device_code, 0.0)
            if last_seen_unix > 0:
                last_seen_ts = datetime.fromtimestamp(last_seen_unix, IST_TIMEZONE)
            
            async with async_session_maker() as session:
                # Check if record already exists
                from sqlalchemy import select
                stmt = select(DeviceStatusSnapshot).where(
                    DeviceStatusSnapshot.device_id == device_id,
                    DeviceStatusSnapshot.snapshot_time == snapshot_time
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()
                
                if existing:
                    # Update existing record
                    existing.status = status
                    existing.last_seen_at = last_seen_ts
                    existing.data_received = 1 if data_received else 0
                    existing.null_values_count = null_count
                else:
                    # Create new record
                    snapshot = DeviceStatusSnapshot(
                        device_id=device_id,
                        snapshot_time=snapshot_time,
                        status=status,
                        last_seen_at=last_seen_ts,
                        data_received=1 if data_received else 0,
                        null_values_count=null_count
                    )
                    session.add(snapshot)
                
                await session.commit()
                logger.debug(
                    f"Saved snapshot for {device_code}: {status} "
                    f"(data_received: {data_received}, null_count: {null_count})"
                )
                
        except Exception as e:
            logger.error(f"Error saving snapshot for {device_code}: {e}")

    async def _cleanup_old_data(self) -> None:
        """
        RAM optimizasyonu: Eski veritabanı kayıtlarını temizle.
        Her saat çalışır, 7 günden eski verileri siler.
        """
        try:
            from sqlalchemy import delete
            from app.models.device_status import DeviceHourlyStatus, DeviceStatusSnapshot
            
            cutoff_date = datetime.now(IST_TIMEZONE) - timedelta(days=7)
            
            async with async_session_maker() as session:
                # 7 günden eski hourly status kayıtlarını sil
                result_hourly = await session.execute(
                    delete(DeviceHourlyStatus)
                    .where(DeviceHourlyStatus.hour_start < cutoff_date)
                )
                hourly_deleted = result_hourly.rowcount
                
                # 30 günden eski snapshot kayıtlarını sil
                cutoff_snapshots = datetime.now(IST_TIMEZONE) - timedelta(days=30)
                result_snapshots = await session.execute(
                    delete(DeviceStatusSnapshot)
                    .where(DeviceStatusSnapshot.snapshot_time < cutoff_snapshots)
                )
                snapshots_deleted = result_snapshots.rowcount
                
                await session.commit()
                
                if hourly_deleted > 0 or snapshots_deleted > 0:
                    logger.info(
                        f"RAM cleanup: Deleted {hourly_deleted} old hourly records "
                        f"and {snapshots_deleted} old snapshots"
                    )
                
        except Exception as e:
            logger.error(f"Error in RAM cleanup: {e}")

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        RAM kullanımı istatistiklerini döndür.
        Memory monitoring için kullanılır.
        """
        total_cache_entries = sum(len(cache) for cache in self._cache.values())
        
        return {
            "cached_devices": len(self._cache),
            "total_cache_entries": total_cache_entries,
            "hourly_tracking_entries": len(self._hourly_tracking),
            "snapshot_tracking_entries": len(self._snapshot_tracking),
            "pending_saves": len(self._pending_saves),
            "max_cache_per_device": self._max_cache_entries_per_device,
            "last_cleanup": self._last_cleanup_time,
        }

    def get_status(self) -> Dict[str, Any]:
        """Get MQTT consumer status."""
        return {
            "running": self._running,
            "connected": self._client.is_connected() if self._client else False,
            "known_modems": len(self._known_modems),
            "device_configs": len(self._device_cfg),
            "cached_devices": len(self._cache),
            "broker_host": settings.MQTT_BROKER_HOST,
            "broker_port": settings.MQTT_BROKER_PORT,
            "memory_stats": self.get_memory_stats(),
        }


# Global singleton instance
_mqtt_consumer: Optional[MQTTConsumer] = None


def get_mqtt_consumer() -> MQTTConsumer:
    """Get or create the MQTT consumer singleton."""
    global _mqtt_consumer
    if _mqtt_consumer is None:
        _mqtt_consumer = MQTTConsumer()
    return _mqtt_consumer

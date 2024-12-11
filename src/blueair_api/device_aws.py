import dataclasses
import logging

from .callbacks import CallbacksMixin
from .http_aws_blueair import HttpAwsBlueair
from .model_enum import ModelEnum
from . import ir_aws as ir

_LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass(slots=True)
class DeviceAws(CallbacksMixin):
    @classmethod
    async def create_device(cls, api, uuid, name, mac, type_name, refresh=False):
        _LOGGER.debug("UUID:"+uuid)
        device_aws = DeviceAws(
            api=api,
            uuid=uuid,
            name_api=name,
            mac=mac,
            type_name=type_name,
        )
        if refresh:
            await device_aws.refresh()
        _LOGGER.debug(f"create_device blueair device_aws: {device_aws}")
        return device_aws

    api: HttpAwsBlueair
    uuid: str  | None | type[NotImplemented] = None
    name: str  | None | type[NotImplemented] = None
    name_api: str  | None | type[NotImplemented] = None
    mac: str  | None | type[NotImplemented] = None
    type_name: str  | None | type[NotImplemented] = None

    sku: str  | None | type[NotImplemented] = None
    firmware: str  | None | type[NotImplemented] = None
    mcu_firmware: str  | None | type[NotImplemented] = None
    serial_number: str  | None | type[NotImplemented] = None

    brightness: int  | None | type[NotImplemented] = None
    child_lock: bool  | None | type[NotImplemented] = None
    fan_speed: int  | None | type[NotImplemented] = None
    fan_auto_mode: bool  | None | type[NotImplemented] = None
    standby: bool  | None | type[NotImplemented] = None
    night_mode: bool  | None | type[NotImplemented] = None
    germ_shield: bool  | None | type[NotImplemented] = None

    pm1: int  | None | type[NotImplemented] = None
    pm2_5: int  | None | type[NotImplemented] = None
    pm10: int  | None | type[NotImplemented] = None
    tVOC: int  | None | type[NotImplemented] = None
    temperature: int  | None | type[NotImplemented] = None
    humidity: int  | None | type[NotImplemented] = None
    filter_usage: int  | None | type[NotImplemented] = None  # percentage
    wifi_working: bool  | None | type[NotImplemented] = None

    # i35
    wick_usage: int  | None | type[NotImplemented] = None  # percentage
    wick_dry_mode: bool  | None | type[NotImplemented] = None
    water_shortage: bool  | None | type[NotImplemented] = None
    auto_regulated_humidity: int  | None | type[NotImplemented] = None

    async def refresh(self):
        _LOGGER.debug(f"refreshing blueair device aws: {self}")
        info = await self.api.device_info(self.name_api, self.uuid)
        # ir.parse_json(ir.Attribute, ir.query_json(info, "configuration.da"))
        ds = ir.parse_json(ir.Sensor, ir.query_json(info, "configuration.ds"))
        dc = ir.parse_json(ir.Control, ir.query_json(info, "configuration.dc"))

        sensor_data = ir.SensorPack(info["sensordata"]).to_latest_value()

        def getter(data_dict, decl_dict, key):
            return data_dict.get(key) if key in decl_dict else NotImplemented

        self.pm1 = getter(sensor_data, ds, "pm1")
        self.pm2_5 = getter(sensor_data, ds, "pm2_5")
        self.pm10 = getter(sensor_data, ds, "pm10")
        self.tVOC = getter(sensor_data, ds, "tVOC")
        self.temperature = getter(sensor_data, ds, "t")
        self.humidity = getter(sensor_data, ds, "h")

        self.name = ir.query_json(info, "configuration.di.name")
        self.firmware = ir.query_json(info, "configuration.di.cfv")
        self.mcu_firmware = ir.query_json(info, "configuration.di.mfv")
        self.serial_number = ir.query_json(info, "configuration.di.ds")
        self.sku = ir.query_json(info, "configuration.di.sku")

        states = ir.SensorPack(info["states"]).to_latest_value()
        # "online" is not defined in the schema.
        self.wifi_working = getter(states, {"online"}, "online")

        self.standby = getter(states, dc, "standby")
        self.night_mode = getter(states, dc, "nightmode")
        self.germ_shield = getter(states, dc, "germshield")
        self.brightness = getter(states, dc, "brightness")
        self.child_lock = getter(states, dc, "childlock")
        self.fan_speed = getter(states, dc, "fanspeed")
        self.fan_auto_mode = getter(states, dc, "automode")
        self.filter_usage = getter(states, dc, "filterusage")
        self.wick_usage = getter(states, dc, "wickusage")
        self.wick_dry_mode = getter(states, dc, "wickdrys")
        self.auto_regulated_humidity = getter(states, dc, "autorh")
        self.water_shortage = getter(states, dc, "wshortage")

        self.publish_updates()
        _LOGGER.debug(f"refreshed blueair device aws: {self}")

    async def set_brightness(self, value: int):
        self.brightness = value
        await self.api.set_device_info(self.uuid, "brightness", "v", value)
        self.publish_updates()

    async def set_fan_speed(self, value: int):
        self.fan_speed = value
        await self.api.set_device_info(self.uuid, "fanspeed", "v", value)
        self.publish_updates()

    async def set_standby(self, value: bool):
        self.standby = value
        await self.api.set_device_info(self.uuid, "standby", "vb", value)
        self.publish_updates()

    # FIXME: avoid state translation at the API level and depreate running.
    # replace with standby which is standard across aws devices.
    @property
    def running(self) -> bool | None:
        if self.standby is None or self.standby is NotImplemented:
            return self.standby
        return not self.standby

    async def set_running(self, running: bool):
        await self.set_standby(not running)

    async def set_fan_auto_mode(self, fan_auto_mode: bool):
        self.fan_auto_mode = fan_auto_mode
        await self.api.set_device_info(self.uuid, "automode", "vb", fan_auto_mode)
        self.publish_updates()

    async def set_auto_regulated_humidity(self, value: int):
        self.auto_regulated_humidity = value
        await self.api.set_device_info(self.uuid, "autorh", "v", value)
        self.publish_updates()

    async def set_child_lock(self, child_lock: bool):
        self.child_lock = child_lock
        await self.api.set_device_info(self.uuid, "childlock", "vb", child_lock)
        self.publish_updates()

    async def set_night_mode(self, night_mode: bool):
        self.night_mode = night_mode
        await self.api.set_device_info(self.uuid, "nightmode", "vb", night_mode)
        self.publish_updates()

    async def set_wick_dry_mode(self, value: bool):
        self.wick_dry_mode = value
        await self.api.set_device_info(self.uuid, "wickdrys", "vb", value)
        self.publish_updates()

    @property
    def model(self) -> ModelEnum:
        if self.sku == "111633":
            return ModelEnum.HUMIDIFIER_H35I
        if self.sku == "105820":
            return ModelEnum.PROTECT_7440I
        if self.sku == "105826":
            return ModelEnum.PROTECT_7470I
        if self.sku == "110059":
            return ModelEnum.MAX_211I
        if self.sku == "110092":
            return ModelEnum.MAX_311I
        if self.sku == "110057":
            return ModelEnum.MAX_411I
        if self.sku == "112124":
            return ModelEnum.T10I
        return ModelEnum.UNKNOWN


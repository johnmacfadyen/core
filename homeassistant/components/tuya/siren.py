"""Support for Tuya siren."""
from __future__ import annotations

from typing import Any

from tuya_iot import TuyaDevice, TuyaDeviceManager

from homeassistant.backports.enum import StrEnum
from homeassistant.components.siren import (
    SirenEntity,
    SirenEntityDescription,
    SirenEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HomeAssistantTuyaData
from .base import TuyaEntity, EnumTypeData
from .const import DOMAIN, TUYA_DISCOVERY_NEW, DPCode, DPType
   
# All descriptions can be found here:
# https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq
SIRENS: dict[str, tuple[SirenEntityDescription, ...]] = {
    # Multi-functional Sensor
    # https://developer.tuya.com/en/docs/iot/categorydgnbj?id=Kaiuz3yorvzg3
    "dgnbj": (
        SirenEntityDescription(
            key=DPCode.ALARM_SWITCH,
            name="Siren",
        ),
    ),
    # Siren Alarm
    # https://developer.tuya.com/en/docs/iot/categorysgbj?id=Kaiuz37tlpbnu
    "sgbj": (
        SirenEntityDescription(
            key=DPCode.ALARM_STATE,
            name="Siren",
            icon="mdi:alarm-bell",
        ),
        # Alert State (0: off, 1: on) - Siren won't trigger if this is off
        SirenEntityDescription(
            key=DPCode.ALERT_STATE,
            name="Armed",
            icon="mdi:shield-lock",
        ),
    ),
    # Smart Camera
    # https://developer.tuya.com/en/docs/iot/categorysp?id=Kaiuz35leyo12
    "sp": (
        SirenEntityDescription(
            key=DPCode.SIREN_SWITCH,
            name="Siren",
        ),
    ),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Tuya siren dynamically through Tuya discovery."""
    hass_data: HomeAssistantTuyaData = hass.data[DOMAIN][entry.entry_id]

    @callback
    def async_discover_device(device_ids: list[str]) -> None:
        """Discover and add a discovered Tuya siren."""
        entities: list[TuyaSirenEntity] = []
        for device_id in device_ids:
            device = hass_data.device_manager.device_map[device_id]
            if descriptions := SIRENS.get(device.category):
                for description in descriptions:
                    if description.key in device.status:
                        entities.append(
                            TuyaSirenEntity(
                                device, hass_data.device_manager, description
                            )
                        )

        async_add_entities(entities)

    async_discover_device([*hass_data.device_manager.device_map])

    entry.async_on_unload(
        async_dispatcher_connect(hass, TUYA_DISCOVERY_NEW, async_discover_device)
    )


class TuyaSirenEntity(TuyaEntity, SirenEntity):
    """Tuya Siren Entity."""

    _attr_supported_features = SirenEntityFeature.TURN_ON | SirenEntityFeature.TURN_OFF | SirenEntityFeature.VOLUME_SET | SirenEntityFeature.DURATION

    def __init__(
        self,
        device: TuyaDevice,
        device_manager: TuyaDeviceManager,
        description: SirenEntityDescription,
    ) -> None:
        """Init Tuya Siren."""
        super().__init__(device, device_manager)
        self.entity_description = description
        self._attr_unique_id = f"{super().unique_id}{description.key}"

    @property
    def is_on(self) -> bool:
        """Return true if siren is on."""
        if self.entity_description.key is DPCode.ALERT_STATE:
            return self.device.status.get(self.entity_description.key, False)
        
        if self.entity_description.key is DPCode.ALARM_STATE:
            sirenOn = self.device.status.get(self.entity_description.key)
            if sirenOn == "normal":
                return False
            if sirenOn == "alarm_sound": 
                return True
                    
        if self.entity_description.key is DPCode.ALARM_SWITCH:
            return self.device.status.get(self.entity_description.key, False)
    
        
    def turn_on(self, **kwargs: Any) -> None:
        """Turn the siren on."""
        
        if self.entity_description.key is DPCode.ALARM_STATE: 
            self._send_command([{"code": self.entity_description.key, "value": "alarm_sound"}])        
        else:
            self._send_command([{"code": self.entity_description.key, "value": True}])

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the siren off."""
        
        if self.entity_description.key is DPCode.ALARM_STATE: 
            self._send_command([{"code": self.entity_description.key, "value": "normal"}])
        else:
            self._send_command([{"code": self.entity_description.key, "value": False}])
        
        
        
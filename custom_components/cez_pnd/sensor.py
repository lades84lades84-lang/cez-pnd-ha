from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy, PERCENTAGE
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

SENSORS = [
    ("nt_today_kwh", "Spotřeba NT dnes", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL),
    ("vt_today_kwh", "Spotřeba VT dnes", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL),
    ("nt_register_kwh", "Registr NT", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    ("vt_register_kwh", "Registr VT", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    ("import_register_kwh", "Celkový odběr registr", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    ("export_register_kwh", "Celková dodávka registr", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    ("completeness", "Úplnost dat", PERCENTAGE, None, None),
]

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(PndSensor(coordinator, entry.data["electrometer_id"], *item) for item in SENSORS)

class PndSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator, meter_id, key, name, unit, device_class, state_class):
        super().__init__(coordinator)
        self.key = key
        self._attr_name = name
        self._attr_unique_id = f"cez_pnd_{meter_id}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_device_info = {
            "identifiers": {("cez_pnd", meter_id)},
            "name": "Elektroměr ČEZ PND",
            "manufacturer": "ČEZ Distribuce",
            "model": "PND online data"
        }
    @property
    def native_value(self):
        return self.coordinator.data.get(self.key) if self.coordinator.data else None

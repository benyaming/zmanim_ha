from typing import Callable, Optional
from datetime import datetime as dt, timedelta

import requests
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers import config_validation as cv
from homeassistant.util.dt import get_time_zone
from homeassistant.components.sensor import PLATFORM_SCHEMA

from timezonefinder import TimezoneFinder
from zmanim.util.geo_location import GeoLocation
from zmanim.zmanim_calendar import ZmanimCalendar


SCAN_INTERVAL = timedelta(seconds=5)

NAME_PARAM = 'name'
LAT_PARAM = 'lat'
LNG_PARAM = 'lng'
ELEVATION_PARAM = 'elevation'

DEFAULT_NAME = 'Zmanim sensor'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(LAT_PARAM): cv.string,
        vol.Required(LAT_PARAM): cv.latitude,
        vol.Required(LNG_PARAM): cv.longitude,
        vol.Optional(NAME_PARAM): cv.string,
        vol.Optional(ELEVATION_PARAM, default='0'): cv.Number
    }
)


def setup_platform(hass: HomeAssistant, config: dict, add_devies: Callable, discovery_info: bool = None):
    lat = config[LAT_PARAM]
    lng = config[LNG_PARAM]
    name = config.get(NAME_PARAM)
    elevation = config[ELEVATION_PARAM]
    add_devies([ZmanimSensor(lat, lng, elevation, name)])


def get_location_name(lat: float, lng: float) -> str:
    resp = requests.get(
        url='https://api.bigdatacloud.net/data/reverse-geocode-client',
        params={
            'latitude': str(lat),
            'longitude': str(lng),
            'localityLanguage': 'en'
        }
    ).json()
    city = resp.get('city')
    country = resp.get('countryName')
    return f'{city}, {country}'


class ZmanimSensor(Entity):
    tz: str = None
    lat: float = None
    lng: float = None
    elevation: float = None
    is_israel: bool = False
    location: GeoLocation = None
    location_name: str = None
    current_state = None

    def __init__(self, lat: float, lng: float, elevation: float, name: Optional[str]):
        self.location_name = name or get_location_name(lat, lng)
        tf = TimezoneFinder()
        self.tz = tf.timezone_at(lat=lat, lng=lng)
        self.is_israel = False if self.tz not in ('Asia/Tel_Aviv', 'Asia/Jerusalem', 'Asia/Hebron') else True
        self.location = GeoLocation(self.name, lat, lng, self.tz, elevation)

    @property
    def name(self):
        return self.location_name

    @property
    def state(self):
        return self.current_state

    def update(self):
        now = dt.now().astimezone(get_time_zone(self.tz))
        calendar = ZmanimCalendar(geo_location=self.location, date=now.date())
        resp = calendar.is_assur_bemelacha(now, in_israel=self.is_israel)
        self.current_state = resp

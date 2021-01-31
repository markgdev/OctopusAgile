import collections
import logging
from datetime import datetime, timedelta

import requests

_LOGGER = logging.getLogger("OctopusOutgoing")


class Outgoing:
    area_code = None
    url = None

    def __init__(self, area_code):
        self.area_code = area_code
        self.url = f"https://api.octopus.energy/v1/products/AGILE-OUTGOING-19-05-13/electricity-tariffs/E-1R-AGILE-OUTGOING-19-05-13-{area_code}/standard-unit-rates/"

    def round_time(self, t: datetime) -> datetime:
        """Rounds to start of current half hour time period
        Args:
            t (datetime): a datetime object
        Returns:
            datetime: the datetime representing the start of the half hour
                time period
        """
        minute = 00
        if t.minute // 30 == 1:
            minute = 30
        return t.replace(second=0, microsecond=0, minute=minute, hour=t.hour)

    def get_raw_rates(self, date_from: str, date_to: str = None):
        """Outgoing rate data from the Octopus API
        Args:
            date_from (str): date from in format "%Y-%m-%dT%H:%M:%SZ"
            date_to (str): date to in format "%Y-%m-%dT%H:%M:%SZ"
        Returns
            dict: the raw outgoing rate data
        """
        date_from = f"?period_from={ date_from }"
        if date_to is not None:
            date_to = f"&period_to={ date_to }"
        else:
            date_to = ""
        headers = {"content-type": "application/json"}
        r = requests.get(f"{self.url}/{ date_from }{ date_to }", headers=headers)
        results = r.json()["results"]
        _LOGGER.debug(r.url)
        return results

    def get_new_rates(self) -> dict:
        """
        Returns
            dict: all available future outgoing rates:
                * date_rate (dict): Dict of date/time as key and rate as vaue
                * rate_list (list): All outgoing rates as a list
        """

        date_from = datetime.strftime(datetime.utcnow(), "%Y-%m-%dT%H:%M:%SZ")
        return self.get_rates(date_from)

    def get_rates(self, date_from: str, date_to: str = None) -> dict:
        """
        Args:
            date_from (str): date from in format "%Y-%m-%dT%H:%M:%SZ"
            date_to (str): date to in format "%Y-%m-%dT%H:%M:%SZ"
        Returns
            dict: outgoing rates:
                * date_rate (dict): Dict of date/time as key and rate as vaue
                * rate_list (list): All outgoing rates as a list
        """

        results = self.get_raw_rates(date_from, date_to)

        date_rates = collections.OrderedDict()

        rate_list = []

        for result in results:
            price = result["value_inc_vat"]
            valid_from = result["valid_from"]
            date_rates[valid_from] = price
            rate_list.append(price)

        return {"date_rates": date_rates, "rate_list": rate_list}

    def get_previous_rate(self) -> float:
        """
        Returns
            float: the previous period outgoing rate
        """
        now = self.round_time(datetime.utcnow())
        rounded_time = datetime.strftime(self.round_time(now), "%Y-%m-%dT%H:%M:%SZ")
        prev_time = datetime.strftime(now - timedelta(minutes=30), "%Y-%m-%dT%H:%M:%SZ")
        date_rates = self.get_rates(prev_time, rounded_time)["date_rates"]
        return date_rates[next(iter(date_rates))]

    def get_current_rate(self) -> float:
        """
        Returns:
            float: the current period outgoing rate
        """
        now = self.round_time(datetime.utcnow())
        rounded_time = datetime.strftime(self.round_time(now), "%Y-%m-%dT%H:%M:%SZ")
        next_time = datetime.strftime(now + timedelta(minutes=30), "%Y-%m-%dT%H:%M:%SZ")
        date_rates = self.get_rates(rounded_time, next_time)["date_rates"]
        return date_rates[next(iter(date_rates))]

    def get_next_rate(self) -> float:
        """
        Returns
            float: the next period outgoing rate
        """
        now = self.round_time(datetime.utcnow())
        rounded_time = datetime.strftime(
            self.round_time(now) + timedelta(minutes=30), "%Y-%m-%dT%H:%M:%SZ"
        )
        next_time = datetime.strftime(now + timedelta(minutes=60), "%Y-%m-%dT%H:%M:%SZ")
        date_rates = self.get_rates(rounded_time, next_time)["date_rates"]
        return date_rates[next(iter(date_rates))]

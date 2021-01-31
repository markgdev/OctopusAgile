import requests
from datetime import datetime, timedelta, date
import collections

import logging

_LOGGER = logging.getLogger("OctopusAgile")


class Agile:
    area_code = None
    base_url = None

    def round_time(self, t) -> datetime:
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

    def __init__(self, area_code):
        self.area_code = area_code
        self.base_url = (
            "https://api.octopus.energy/v1/products/AGILE-18-02-21/electricity-tariffs"
        )

    def get_times_below(self, in_d: dict, limit: float):
        """Get a date_rate dict of any times below "limit"
        Args:
            in_d (dict): a date_rate dict.
            limit (float): a
        Returns:
            dict: A date_rate dict of any times below "limit"
        """
        ret_d = {}
        for time, rate in in_d.items():
            if rate <= limit:
                ret_d[time] = rate
        return ret_d

    def get_area_code(self):
        """
        Returns:
           str: The Distribution Network Operator area code that is being used
        """

        return self.area_code

    def get_min_times(self, num, in_d, requirements):
        """Get a date rate dict of "num" number of time periods in in_d.

        Args:
            in_d (dict): a date_rate dict
            requirements (list): a list of dicts with details of particular times that
                must be includes in the returned date_rate dict.
                Example, must have 2 slots between 1900 and 0600:
                {'slots': 2, 'time_from': '2020-04-15T19:00:00Z', 'time_to': '2020-04-16T06:00:00Z'}
        Returns:
            dict: A date_rate dict
        """
        ret_d = {}
        d = {}
        d.update(in_d)
        for i in range(num):
            min_key = min(d, key=d.get)
            ret_d[min_key] = d[min_key]
            del d[min_key]
        for requirement in requirements:
            slots_filled = []
            after_time = datetime.strptime(
                requirement["time_from"], "%Y-%m-%dT%H:%M:%SZ"
            )
            before_time = datetime.strptime(
                requirement["time_to"], "%Y-%m-%dT%H:%M:%SZ"
            )
            min_slots = requirement["slots"]

            for time, rate in ret_d.items():
                dttime = datetime.strptime(time, "%Y-%m-%dT%H:%M:%SZ")
                if after_time < dttime < before_time:
                    slots_filled.append(time)
            if len(slots_filled) < min_slots:
                for slot in slots_filled:
                    del ret_d[slot]
                new_rates = self.get_rates(
                    requirement["time_from"], requirement["time_to"]
                )
                new_mins = self.get_min_times(min_slots, new_rates["date_rates"], [])
                remove_list = self.get_max_times(min_slots - len(slots_filled), ret_d)
                for time, rate in remove_list.items():
                    del ret_d[time]
                for time, rate in new_mins.items():
                    ret_d[time] = rate
        return ret_d

    def get_max_times(self, num: int, in_d: dict) -> dict:
        """Get a date_rate dict of "num" number of max periods
        Args:
            num (int): the number of periods to return
            in_d (dict): a date_rate dict
        Returns:
            dict: A date_rate dict
        """
        ret_d = {}
        d = {}
        d.update(in_d)
        for i in range(num):
            min_key = max(d, key=d.get)
            ret_d[min_key] = d[min_key]
            del d[min_key]
        return ret_d

    def get_min_time_run(self, hours: int, in_d: dict):
        """Get a date_rate dict of the cheapest time period of "hours" hours.
        Args:
            in_d (dict): a date_rate dict
            hours (int): the number of hours you want the period for
        Returns:

        """
        slots = int(hours * 2)
        d = {}
        d.update(
            collections.OrderedDict(reversed(list(in_d.items())))
        )  # Dict was in wrong order
        keys = list(d.keys())
        avgs = {}
        for index, obj in enumerate(keys):
            this_avg = []
            for offset in range(0, slots):
                if index + offset < len(keys):
                    this_avg.append(d[keys[index + offset]])
                else:
                    min_key = min(avgs, key=avgs.get)
                    return {min_key: avgs[min_key]}
            avgs[keys[index]] = sum(this_avg) / slots

    def get_rates_delta(self, day_delta):
        """
        Args:
            day_delta (int):
        Returns
            dict: the same dict as get_rate for the past "day_delta" days
        """
        minute = 00
        if datetime.now().minute > 30:
            minute = 30
        prev_day = date.today() - timedelta(days=day_delta)
        this_day = date.today() - timedelta(days=day_delta - 1)

        date_from = f"{ prev_day.strftime('%Y-%m-%d') }T00:00"
        date_to = f"{ this_day.strftime('%Y-%m-%d') }T00:00"
        # print(date_from)
        return self.get_rates(date_from, date_to)

    def get_raw_rates(self, date_from: str, date_to: str = None) -> dict:
        """Agile rate data from the Octopus API
        Args:
            date_from (str): date from in format "%Y-%m-%dT%H:%M:%SZ"
            date_to (str): date to in format "%Y-%m-%dT%H:%M:%SZ"
        Returns
            dict: the raw agile rate data
        """

        date_from = f"?period_from={ date_from }"
        if date_to is not None:
            date_to = f"&period_to={ date_to }"
        else:
            date_to = ""
        headers = {"content-type": "application/json"}
        r = requests.get(
            f"{self.base_url}/"
            f"E-1R-AGILE-18-02-21-{self.area_code}/"
            f"standard-unit-rates/{ date_from }{ date_to }",
            headers=headers,
        )
        results = r.json()["results"]
        _LOGGER.debug(r.url)
        return results

    def get_new_rates(self) -> dict:
        """
        Returns:
            dict: All available future rates
        """
        date_from = datetime.strftime(datetime.utcnow(), "%Y-%m-%dT%H:%M:%SZ")
        return self.get_rates(date_from)

    def get_rates(self, date_from: str, date_to: str = None) -> dict:
        """
        Args:
            date_from (str): date from in format "%Y-%m-%dT%H:%M:%SZ"
            date_to (str): date to in format "%Y-%m-%dT%H:%M:%SZ"
        Returns:
            dict:
                - date_rate (dict): Dict of date/time as key and rate as vaue
                - rate_list (list): All Rates as a list
                - low_rate_list (list): All Rates below 15p
        """
        results = self.get_raw_rates(date_from, date_to)

        date_rates = collections.OrderedDict()

        rate_list = []
        low_rate_list = []

        for result in results:
            price = result["value_inc_vat"]
            valid_from = result["valid_from"]
            valid_to = result["valid_to"]
            date_rates[valid_from] = price
            rate_list.append(price)
            if price < 15:
                low_rate_list.append(price)

        return {
            "date_rates": date_rates,
            "rate_list": rate_list,
            "low_rate_list": low_rate_list,
        }

    def summary(self, days, daily_sum=False):
        """Print a summary of the rates for the past "days" days"""

        all_rates = {}
        all_rates_list = []
        all_low_rates_list = []
        water_rates = []
        day_count = 0
        for i in range(0, days):
            rates = self.get_rates_delta(i)
            rate_list = rates["rate_list"]
            low_rate_list = rates["low_rate_list"]
            date_rates = rates["date_rates"]
            all_rates.update(date_rates)
            all_rates_list.extend(rate_list)
            all_low_rates_list.extend(low_rate_list)

            mean_price = sum(rate_list) / len(rate_list)
            low_mean_price = sum(low_rate_list) / len(low_rate_list)

            cheapest6 = self.get_min_times(6, date_rates, [])
            day = datetime.strptime(
                next(iter(date_rates)), "%Y-%m-%dT%H:%M:%SZ"
            ).strftime("%Y-%m-%d")

            minTimeHrs = self.get_min_time_run(
                4,
            )
            minTimeHrsTime = list(minTimeHrs.keys())[0]
            minTimeHrsRate = minTimeHrs[list(minTimeHrs.keys())[0]]
            water_rates.append(minTimeHrsRate)

            if daily_sum:
                print(f"({day})                {cheapest6}")
                print(f"({day}) Avg Price:     {mean_price}")
                print(f"({day}) Low Avg Price: {low_mean_price}")
                print(f"({day}) Min Price:     {min(rate_list)}")
                print(f"({day}) Max Price:     {max(rate_list)}")
                print(f"({day}) Min 4 Hr Run:  {minTimeHrsTime}: {minTimeHrsRate}")
            else:
                print(".", end="")
                if day_count % 50 == 0:
                    print()
                day_count += 1
        print()

        overall_min = min(all_rates, key=all_rates.get)
        overall_max = max(all_rates, key=all_rates.get)

        mean_price = sum(all_rates_list) / len(all_rates_list)
        low_mean_price = sum(all_low_rates_list) / len(all_low_rates_list)
        avg_water_price = sum(water_rates) / len(water_rates)
        avg_water_usage = 7.738
        print()
        print("Overall stats:")
        print(f"Avg Price:       {mean_price}")
        print(f"Low Avg Price:   {low_mean_price}")
        print(
            f"Avg Water Price: {avg_water_price} (£{round(avg_water_usage*(avg_water_price/100), 2)}/day), "
            f"(£{round(avg_water_usage*(avg_water_price/100)*365, 2)}/year)"
        )
        print(
            f"Cur Water Price: {avg_water_price} (£{round(avg_water_usage*(15.44/100), 2)}/day), "
            f"(£{round(avg_water_usage*(15.44/100)*365, 2)}/year)"
        )
        print(f"Min Price:       {overall_min}: {all_rates[overall_min]}")
        print(f"Max Price:       {overall_max}: {all_rates[overall_max]}")
        print(f"Num Days:        {days}")

    def get_previous_rate(self) -> float:
        """
        Returns:
            float: the previous period rate
        """
        now = self.round_time(datetime.utcnow())
        rounded_time = datetime.strftime(self.round_time(now), "%Y-%m-%dT%H:%M:%SZ")
        prev_time = datetime.strftime(now - timedelta(minutes=30), "%Y-%m-%dT%H:%M:%SZ")
        date_rates = self.get_rates(prev_time, rounded_time)["date_rates"]
        return date_rates[next(iter(date_rates))]

    def get_current_rate(self) -> float:
        """
        Returns:
            float: the current period rate
        """
        now = self.round_time(datetime.utcnow())
        rounded_time = datetime.strftime(self.round_time(now), "%Y-%m-%dT%H:%M:%SZ")
        next_time = datetime.strftime(now + timedelta(minutes=30), "%Y-%m-%dT%H:%M:%SZ")
        date_rates = self.get_rates(rounded_time, next_time)["date_rates"]
        return date_rates[next(iter(date_rates))]

    def get_next_rate(self) -> float:
        """
        Returns:
            float: the next period rate
        """
        now = self.round_time(datetime.utcnow())
        rounded_time = datetime.strftime(
            self.round_time(now) + timedelta(minutes=30), "%Y-%m-%dT%H:%M:%SZ"
        )
        next_time = datetime.strftime(now + timedelta(minutes=60), "%Y-%m-%dT%H:%M:%SZ")
        date_rates = self.get_rates(rounded_time, next_time)["date_rates"]
        return date_rates[next(iter(date_rates))]


if __name__ == "__main__":
    myagile = Agile("L")
    rates = myagile.get_rates_delta(1)["date_rates"]
    low_rates = myagile.get_times_below(rates, 0)
    print(low_rates)
    print(myagile.get_min_time_run(3, rates))
    print("prev: ", myagile.get_previous_rate())
    print("now: ", myagile.get_current_rate())
    print("next: ", myagile.get_next_rate())
    print("New: ", myagile.get_new_rates())

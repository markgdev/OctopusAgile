# OctopusAgile
Init with the region code (Don't include the _) as per: https://en.wikipedia.org/wiki/Distribution_network_operator

## Methods
### Time format
All time formats are "%Y-%m-%dT%H:%M:%SZ" e.g. 2020-04-16T06:00:00Z

### get_raw_rates(date_from, date_to)
Returns the raw data as given to us by the API

### get_rates(date_from, date_to)
Returns a dict of:
* date_rate (dict): Dict of date/time as key and rate as vaue
* rate_list (list): All Rates as a list
* low_rate_list (list): All Rates below 15p

### get_rates_delta(day_delta)
Returns the same dict as get_rate for the past "day_delta" days

### get_sumary(days, daily_sum=False)
Print a summary of the rates for the past "days" days

### get_min_time_run(hours, in_d)
Get a date_rate dict of the cheapest time period of "hours" hours.

in_d is a date_rate dict.

### get_times_below(in_d, limit)
Get a date_rate dict of any times below "limit"

in_d is a date_rate dict.

### get_min_times(num, in_d, requirements)
Get a date rate dict of "num" number of time periods in in_d.

in_d is a date_rate dict.

Requirements a list of dicts with details of particular times that must be includes in the returned date_rate dict.

Example, must have 2 slots between 1900 and 0600: {'slots': 2, 'time_from': '2020-04-15T19:00:00Z', 'time_to': '2020-04-16T06:00:00Z'}

### get_max_times(num, in_d)
Get a date_rate dict of "num" number of max periods
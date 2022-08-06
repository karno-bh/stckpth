from datetime import datetime, timedelta


def past_round_minute_range(time: datetime, delta=1):
    t_from = time - timedelta(minutes=delta, seconds=time.second, microseconds=time.microsecond)
    t_to = t_from + timedelta(minutes=1)
    return range(int(t_from.timestamp()), int(t_to.timestamp()))


def past_round_hour_range(time: datetime, delta=1):
    t_from = time - timedelta(hours=delta, minutes=time.minute, seconds=time.second, microseconds=time.microsecond)
    t_to = t_from + timedelta(hours=1)
    return range(int(t_from.timestamp()), int(t_to.timestamp()))

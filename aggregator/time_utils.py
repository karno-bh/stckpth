from datetime import datetime, timedelta


def past_round_minute_range(time: datetime, delta=1):
    t_from = time - timedelta(minutes=delta, seconds=time.second, microseconds=time.microsecond)
    t_to = t_from + timedelta(minutes=1)
    print(t_from, t_to)
    return range(int(t_from.timestamp()), int(t_to.timestamp()))


def past_round_hour_range(time: datetime, delta=1):
    t_from = time - timedelta(hours=delta, minutes=time.minute, seconds=time.second, microseconds=time.microsecond)
    t_to = t_from + timedelta(hours=1)
    print(t_from, t_to)
    return range(int(t_from.timestamp()), int(t_to.timestamp()))


def test001():
    t00 = datetime.now()
    print(t00)
    print(past_round_minute_range(t00))
    # print(past_round_minute_range(t1))
    # t1 = past_round_minute_range(t0)
    # print(t1)
    # print(past_round_hour_range(t0))

if __name__ == '__main__':
    test001()
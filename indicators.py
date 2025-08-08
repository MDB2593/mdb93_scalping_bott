def ema(values, period):
    values = list(values)
    if not values or period <= 1:
        return values
    k = 2 / (period + 1)
    ema_vals = []
    ema_prev = values[0]
    ema_vals.append(ema_prev)
    for v in values[1:]:
        ema_prev = v * k + ema_prev * (1 - k)
        ema_vals.append(ema_prev)
    return ema_vals

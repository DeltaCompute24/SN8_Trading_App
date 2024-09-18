from datetime import datetime, timedelta


def get_assets_fee(asset_type):
    if asset_type == "crypto":
        return 0.001
    elif asset_type == "forex":
        return 0.00007
    else:  # for indices
        return 0.00009


def calculate_time_difference(open_time):
    open_time = datetime.fromisoformat(open_time)
    current_time = datetime.utcnow()

    total_days = (current_time - open_time).days

    def next_wednesday(date):
        days_until_wednesday = (2 - date.weekday() + 7) % 7
        return date + timedelta(days=days_until_wednesday)

    # Get the first Wednesday
    first_wednesday = next_wednesday(open_time)

    # If the first Wednesday is after the current time, there are no Wednesdays
    if first_wednesday > current_time:
        wednesday_count = 0
    else:
        # Calculate the number of weeks from the first Wednesday to current_time
        total_weeks = (current_time - first_wednesday).days // 7
        wednesday_count = total_weeks + 1

    return (total_days - wednesday_count), wednesday_count


def get_max_leverage(leverages: list, order_types: list):
    max_leverage = 0.0
    cur_leverage = 0.0
    for leverage, order_type in zip(leverages, order_types):
        if cur_leverage == 0.0:
            cur_leverage = leverage
            max_leverage = cur_leverage
            continue

        if order_type == 'LONG':
            cur_leverage += leverage
        elif order_type == 'SHORT':
            cur_leverage -= leverage

        if cur_leverage > max_leverage:
            max_leverage = cur_leverage

    return max_leverage


def calculate_fee(position, asset_type: str) -> float:
    fix_fee = get_assets_fee(asset_type)
    max_leverage = get_max_leverage(position.leverage_list or [], position.order_type_list or [])
    num_of_days_except_wed, num_of_weds = calculate_time_difference(position.open_time)
    return (fix_fee * num_of_days_except_wed * max_leverage) + (fix_fee * 3 * num_of_weds * max_leverage)

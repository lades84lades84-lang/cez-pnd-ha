def _num(value):
    try:
        return float(str(value).replace(",", ".")) if value is not None else None
    except (TypeError, ValueError):
        return None

def find_range(payload, name=None):
    ranges = payload.get("ranges", {})
    if not isinstance(ranges, dict):
        return None
    if name and isinstance(ranges.get(name), list) and ranges[name]:
        return ranges[name][0]
    for values in ranges.values():
        if isinstance(values, list) and values and isinstance(values[0], dict):
            return values[0]
    return None

def column_value(report_range, column_id):
    if not isinstance(report_range, dict):
        return None
    columns = report_range.get("columns", [])
    if isinstance(columns, dict):
        item = columns.get(str(column_id), columns.get(column_id))
        return _num(item.get("v", item.get("value"))) if isinstance(item, dict) else _num(item)
    if isinstance(columns, list):
        for item in columns:
            if isinstance(item, dict) and str(item.get("id", item.get("columnId", item.get("column")))) == str(column_id):
                return _num(item.get("v", item.get("value")))
    return None

def tariff_total(payload, name):
    return column_value(find_range(payload, name), 1007)

def tariff_completeness(payload, name):
    return column_value(find_range(payload, name), 1009)

def register_value(payload, series_key):
    ranges = payload.get("ranges", {})
    values = ranges.get(series_key) if isinstance(ranges, dict) else None
    if isinstance(values, list) and values:
        return column_value(values[0], 1006)
    if isinstance(values, dict):
        return column_value(values, 1006)
    return None

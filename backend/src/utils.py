import json
from datetime import date


# generalized response formats
def success_response(data, code=200):
    return json.dumps(data), code


def failure_response(message, code=404):
    return json.dumps({"error": message}), code


def process_date(request):
    body = json.loads(request.data)
    date_string = body.get("date", date.today().isoformat())
    requested_date = date.fromisoformat(date_string)
    return requested_date


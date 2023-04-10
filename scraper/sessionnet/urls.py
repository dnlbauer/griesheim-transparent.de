from urllib.parse import urlencode

from sessionnet.url_suffices import meeting_url_to_suffix


def get_meeting_url(meeting_id):
    return f"{meeting_url_to_suffix}?{urlencode({'__ksinr': str(meeting_id)})}"


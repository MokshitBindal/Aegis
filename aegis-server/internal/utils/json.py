"""JSON utilities for the server."""

import json
from datetime import date, datetime
from uuid import UUID


class AegisJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime, date, and UUID objects."""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, UUID):
            return str(obj)
        # Let the base class handle everything else
        return json.JSONEncoder.default(self, obj)

def dumps(obj):
    """Dump object to JSON string using our custom encoder."""
    return json.dumps(obj, cls=AegisJSONEncoder)
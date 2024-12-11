import logging
from datetime import datetime


class LogHandlerSumo(logging.Handler):
    def __init__(self, sumo_client):
        logging.Handler.__init__(self)
        self._sumoClient = sumo_client
        return

    def emit(self, record):
        try:
            dt = (
                datetime.now(datetime.timezone.utc)
                .replace(microsecond=0)
                .isoformat()
                + "Z"
            )
            json = {
                "severity": record.levelname,
                "message": record.getMessage(),
                "timestamp": dt,
                "source": record.name,
                "pathname": record.pathname,
                "funcname": record.funcName,
                "linenumber": record.lineno,
            }
            if "objectUuid" in record.__dict__:
                json["objectUuid"] = record.__dict__.get("objectUuid")

            self._sumoClient.post("/message-log/new", json=json)
        except Exception:
            # Never fail on logging
            pass

        return

    pass

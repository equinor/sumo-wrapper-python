import logging
from datetime import UTC, datetime


class LogHandlerSumo(logging.Handler):
    def __init__(self, sumo_client):
        logging.Handler.__init__(self)
        self._sumoClient = sumo_client

    def emit(self, record):
        try:
            dt = (
                datetime.now(UTC)
                .replace(microsecond=0, tzinfo=None)
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

            if "details" in record.__dict__:
                json["details"] = record.__dict__.get("details")

            self._sumoClient.post("/message-log/new", json=json)
        except Exception:
            # Never fail on logging
            pass



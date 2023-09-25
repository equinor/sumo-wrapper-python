import logging
from datetime import datetime


class LogHandlerSumo(logging.Handler):
    def __init__(self, sumoClient):
        logging.Handler.__init__(self)
        self._sumoClient = sumoClient
        return

    def emit(self, record):
        try:
            dt = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
            json = {
                "severity": record.levelname,
                "message": record.getMessage(),
                "timestamp": dt,
                "source": record.name,
                "pathname": record.pathname,
                "funcname": record.funcName,
                "linenumber": record.lineno,
            }
            self._sumoClient.post("/message-log/new", json=json)
        except Exception:
            # Never fail on logging
            pass

        return

    pass

import logging
from enum import Enum, auto
from typing import Optional


class LogEventTypes(Enum):
    NONE = auto()

    AUTH = auto()


class StructuredLogger:
    def __init__(self, name):
        self.logger: logging.Logger = logging.getLogger(__name__)

    def _generate_structured_log(
        self,
        event_name: Optional[str] = None,
        event_type: Optional[LogEventTypes] = LogEventTypes.NONE,
        msg: Optional[str] = None,
        **kwargs,
    ) -> dict:
        return {
            **{"event_name": event_name, "event_type": event_type.name, "msg": msg},
            **kwargs,
        }

    def debug(
        self,
        event_name: Optional[str] = None,
        event_type: Optional[LogEventTypes] = LogEventTypes.NONE,
        msg: Optional[str] = None,
        **kwargs,
    ) -> None:
        self.logger.debug(
            self._generate_structured_log(
                event_name=event_name,
                event_type=event_type,
                msg=msg,
                **kwargs,
            )
        )

    def info(
        self,
        event_name: Optional[str] = None,
        event_type: Optional[LogEventTypes] = LogEventTypes.NONE,
        msg: Optional[str] = None,
        **kwargs,
    ) -> None:
        self.logger.info(
            self._generate_structured_log(
                event_name=event_name,
                event_type=event_type,
                msg=msg,
                **kwargs,
            )
        )

    def warning(
        self,
        event_name: Optional[str] = None,
        event_type: Optional[LogEventTypes] = LogEventTypes.NONE,
        msg: Optional[str] = None,
        **kwargs,
    ) -> None:
        self.logger.warning(
            self._generate_structured_log(
                event_name=event_name,
                event_type=event_type,
                msg=msg,
                **kwargs,
            )
        )

    def error(
        self,
        event_name: Optional[str] = None,
        event_type: Optional[LogEventTypes] = LogEventTypes.NONE,
        msg: Optional[str] = None,
        **kwargs,
    ) -> None:
        self.logger.error(
            self._generate_structured_log(
                event_name=event_name,
                event_type=event_type,
                msg=msg,
                **kwargs,
            )
        )

    def exception(
        self,
        event_name: Optional[str] = None,
        event_type: Optional[LogEventTypes] = LogEventTypes.NONE,
        msg: Optional[str] = None,
        **kwargs,
    ) -> None:
        self.logger.exception(
            self._generate_structured_log(
                event_name=event_name,
                event_type=event_type,
                msg=msg,
                **kwargs,
            )
        )

    def critical(
        self,
        event_name: Optional[str] = None,
        event_type: Optional[LogEventTypes] = LogEventTypes.NONE,
        msg: Optional[str] = None,
        **kwargs,
    ) -> None:
        self.logger.critical(
            self._generate_structured_log(
                event_name=event_name,
                event_type=event_type,
                msg=msg,
                **kwargs,
            )
        )

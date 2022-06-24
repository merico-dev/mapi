from abc import ABC, abstractmethod

from .core import Request, Response


class ResponseDatabase(ABC):
    @abstractmethod
    def put(self, request: Request, response: Response):
        pass

    @abstractmethod
    def get(self, request: Request) -> Response:
        pass

    @abstractmethod
    def iter_responses(self):
        pass


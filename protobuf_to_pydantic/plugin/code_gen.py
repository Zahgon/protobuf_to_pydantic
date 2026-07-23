import base64
import importlib
import logging
import pathlib
import sys
import traceback
import types
from typing import Callable, Dict, Generic, Optional, Type

from google.protobuf.compiler.plugin_pb2 import CodeGeneratorRequest, CodeGeneratorResponse
from mypy_protobuf.main import Descriptors, code_generation

from protobuf_to_pydantic.plugin.config import ConfigT, get_config_by_module
from protobuf_to_pydantic.util import use_worker_dir_in_ctx

from protobuf_to_pydantic.protos import p2p_validate_pb2, validate_pb2  # isort:skip


logger = logging.getLogger(__name__)


class CodeGen(Generic[ConfigT]):
    config: ConfigT

    def __init__(self, config_class: Type[ConfigT]) -> None:
        self.config_class: Type[ConfigT] = config_class

        with code_generation() as (request, response):
            self.param_dict = self.gen_param_from_request(request)
            self.gen_config()
            self.generate_pydantic_model(Descriptors(request), response)

    @staticmethod
    def gen_param_from_request(request: CodeGeneratorRequest) -> dict:
        pass

    def _get_config_by_path(self, key: str) -> None:
        pass

    def _get_config_by_py_code(self, key: str) -> None:
        pass

    def gen_config(self) -> None:
        pass

    def generate_pydantic_model(self, descriptors: Descriptors, response: CodeGeneratorResponse) -> None:
        pass

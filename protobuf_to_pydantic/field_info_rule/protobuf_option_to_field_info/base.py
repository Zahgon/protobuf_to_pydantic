import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from google.protobuf.descriptor import FieldDescriptor

from protobuf_to_pydantic import _pydantic_adapter
from protobuf_to_pydantic.constant import protobuf_common_type_dict
from protobuf_to_pydantic.customer_con_type import (
    conbytes,
    confloat,
    conint,
    conlist,
    constr,
    contimedelta,
    contimestamp,
)
from protobuf_to_pydantic.customer_validator import validate_validator_dict
from protobuf_to_pydantic.field_info_rule.protobuf_option_to_field_info.types import rule_name_pydantic_type_dict
from protobuf_to_pydantic.field_info_rule.types import FieldInfoTypedDict

logger: logging.Logger = logging.getLogger(__name__)

pgv_column_to_pydantic_dict: Dict[str, str] = {
    "min_len": "min_length",
    "min_bytes": "min_length",
    "max_len": "max_length",
    "max_bytes": "max_length",
    "pattern": "regex",
    "unique": "unique_items",
    "gte": "ge",
    "lte": "le",
    "len_bytes": "len",
    "miss_default": "required",
}

special_type_rule_name_set = {
    "lt",
    "le",
    "gt",
    "ge",
    "const",
    "in",
    "not_in",
    "lt_now",
    "gt_now",
    "within",
    "min_pairs",
    "max_pairs",
}


def get_con_type_func_from_type_name(type_name: str) -> Optional[Callable]:
    pass


class BaseProtobufOptionToFieldInfo(object):
    @property
    def rule_dict(self) -> FieldInfoTypedDict:
        raise NotImplementedError

    def sub_value_handler(self, rule_value: Any) -> Dict[str, Any]:
        raise NotImplementedError

    def sub_type_name_handler(self, rule_value: Any) -> str:
        raise NotImplementedError

    def rule_value_to_field_value_handler(self, field_type_name: str, rule_name: str, rule_value: Any) -> Any:
        raise NotImplementedError

    def value_type_conversion_handler(self, field_type_name: str, rule_name: str, rule_value: Any) -> Tuple[bool, Any]:
        pass

    def _core_handler(
        self,
        rule_dict: Dict[str, Any],
        *,
        field_name: str,
        field_type: int,
        type_name: str,
        full_name: str,
    ) -> FieldInfoTypedDict:
        pass


type_not_support_dict: Dict[Any, Set[str]] = {
    FieldDescriptor.TYPE_BYTES: {"pattern"},
    FieldDescriptor.TYPE_STRING: {"min_bytes", "max_bytes", "well_known_regex", "strict"},
    "Any": {"ignore_empty", "defined_only", "no_sparse"},
}

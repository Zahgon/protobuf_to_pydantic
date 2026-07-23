from datetime import timedelta
from typing import Any, Dict, Optional, Tuple, Union

from protobuf_to_pydantic.field_info_rule.protobuf_option_to_field_info.base import (
    BaseProtobufOptionToFieldInfo,
    special_type_rule_name_set,
)
from protobuf_to_pydantic.field_info_rule.types import FieldInfoTypedDict
from protobuf_to_pydantic.grpc_types import FieldDescriptor, FieldDescriptorProto, Timestamp


class ProtobufOptionToFieldInfoWithCommentDict(BaseProtobufOptionToFieldInfo):

    def __init__(
        self,
        rule_dict: Dict[str, Any],
        field: Union[FieldDescriptor, FieldDescriptorProto],
        type_name: str,
        full_name: str,
    ):
        self._rule_dict = self._core_handler(
            rule_dict=rule_dict,
            field_name=field.name,
            field_type=field.type,
            type_name=type_name,
            full_name=full_name,
        )

    @property
    def rule_dict(self) -> FieldInfoTypedDict:
        pass

    @staticmethod
    def _duration_handler(_value: Any) -> Optional[timedelta]:
        pass

    def sub_value_handler(self, rule_value: Any) -> Dict[str, Any]:
        pass

    def sub_type_name_handler(self, rule_value: Any) -> str:
        pass

    def rule_value_to_field_value_handler(self, field_type_name: str, rule_name: str, rule_value: Any) -> Any:
        pass

    def value_type_conversion_handler(self, field_type_name: str, rule_name: str, rule_value: Any) -> Tuple[bool, Any]:
        pass


def gen_field_rule_info_dict_from_field_comment_dict(  # noqa: C901
    rule_dict: Dict[str, Any],
    field: Union[FieldDescriptor, FieldDescriptorProto],
    type_name: str,
    full_name: str,
) -> FieldInfoTypedDict:
    return ProtobufOptionToFieldInfoWithCommentDict(
        rule_dict=rule_dict, field=field, type_name=type_name, full_name=full_name
    ).rule_dict

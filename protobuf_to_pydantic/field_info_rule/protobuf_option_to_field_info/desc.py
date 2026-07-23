import logging
from typing import Any, Dict, List, Optional, Union

from google.protobuf.descriptor import Descriptor, FieldDescriptor
from google.protobuf.descriptor_pb2 import FieldDescriptorProto
from google.protobuf.message import Message

from protobuf_to_pydantic.field_info_rule.protobuf_option_to_field_info.base import BaseProtobufOptionToFieldInfo
from protobuf_to_pydantic.field_info_rule.types import FieldInfoTypedDict
from protobuf_to_pydantic.util import replace_protobuf_type_to_python_type

logger: logging.Logger = logging.getLogger(__name__)


def _has_raw_message_field(field_name: str, message: Message) -> bool:
    pass


class ProtobufOptionToFieldInfoWithFieldDesc(BaseProtobufOptionToFieldInfo):

    def __init__(
        self,
        field_descriptor: Union[Descriptor, FieldDescriptor],
        field: Union[FieldDescriptor, FieldDescriptorProto],
        type_name: str,
        full_name: str,
    ):
        self._rule_dict = self._core_handler(
            self.get_rule_dict(self.get_rule_name_list(field_descriptor), field_descriptor),
            field_name=field.name,
            field_type=field.type,
            type_name=type_name,
            full_name=full_name,
        )

    def get_rule_name_list(self, rule_descriptor: Union[Descriptor, FieldDescriptor]) -> List[str]:
        pass

    def get_rule_dict(
        self, rule_name_list: List[str], _field_descriptor: Union[Descriptor, FieldDescriptor]
    ) -> Dict[str, Any]:
        pass

    @property
    def rule_dict(self) -> FieldInfoTypedDict:
        pass

    def sub_value_handler(self, rule_value: Any) -> Dict[str, Any]:
        pass

    def sub_type_name_handler(self, rule_value: Any) -> str:
        pass

    def rule_value_to_field_value_handler(self, field_type_name: str, rule_name: str, rule_value: Any) -> Any:
        pass


def gen_field_info_dict_from_field_desc(
    type_name: str,
    full_name: str,
    field: Union[FieldDescriptor, FieldDescriptorProto],
    protobuf_pkg: str = "",
) -> FieldInfoTypedDict:
    """Parse the information for each filed

    :param type_name: field type name
    :param full_name: field fullname
    :param field:     message field
    :param protobuf_pkg: protobuf rule pkg name
    """
    field_info_dict: FieldInfoTypedDict = {"extra": {}, "skip": False, "required": False}

    if isinstance(field, FieldDescriptor):
        field_list = field.GetOptions().ListFields()
    elif isinstance(field, FieldDescriptorProto):
        field_list = field.options.ListFields()
    else:
        raise RuntimeError(f"Not support type:{field.type}")

    for option_descriptor, option_value in field_list:
        if protobuf_pkg:
            if not option_descriptor.full_name.endswith(f"{protobuf_pkg}.rules"):
                continue
        elif not option_descriptor.full_name.endswith("validate.rules"):
            continue

        rule_message: Any = option_value.message
        if rule_message:
            if getattr(rule_message, "skip", None):
                field_info_dict["skip"] = True
            if getattr(rule_message, "required", None):
                field_info_dict["required"] = True
        type_value: Optional[Descriptor] = getattr(option_value, type_name, None)
        if not type_value:
            continue
        if not type_value.ListFields():  # type: ignore
            type_value = getattr(option_value, "message", None)
            if not type_value or not type_value.ListFields():  # type: ignore
                logger.warning(f"{__name__} Can not found {full_name}'s {type_name} from {option_value}")

        field_info_dict.update(
            ProtobufOptionToFieldInfoWithFieldDesc(type_value, field, type_name, full_name).rule_dict  # type: ignore
        )

    return field_info_dict

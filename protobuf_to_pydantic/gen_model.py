import dataclasses
import datetime
import importlib
import inspect
import logging
import os
from enum import IntEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple, Type, Union

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from typing_extensions import Annotated, get_origin

from protobuf_to_pydantic import _pydantic_adapter, constant
from protobuf_to_pydantic.constant import protobuf_common_type_dict
from protobuf_to_pydantic.customer_validator import check_one_of
from protobuf_to_pydantic.exceptions import WaitingToCompleteException
from protobuf_to_pydantic.field_info_rule.field_info_param import (
    FieldInfoParamModel,
    field_info_param_dict_handle,
    field_info_param_dict_migration_v2_handler,
)
from protobuf_to_pydantic.field_info_rule.protobuf_option_to_field_info.comment import (
    gen_field_rule_info_dict_from_field_comment_dict,
)
from protobuf_to_pydantic.get_message_option import (
    get_message_option_dict_from_message_with_p2p,
    get_message_option_dict_from_message_with_pgv,
    get_message_option_dict_from_proto_file,
    get_message_option_dict_from_pyi_file,
)
from protobuf_to_pydantic.grpc_types import AnyMessage, Descriptor, FieldDescriptor, FieldMask, Message
from protobuf_to_pydantic.template import Template
from protobuf_to_pydantic.util import create_pydantic_model, pydantic_allow_validation_field_handler

if TYPE_CHECKING:
    from protobuf_to_pydantic.field_info_rule.types import FieldInfoTypedDict, MessageOptionTypedDict, UseOneOfTypedDict

logger: logging.Logger = logging.getLogger(__name__)

SKIP_RULE_MESSAGE_SUFFIX = "WithSkipRule"
ALLOW_ARBITRARY_TYPE = (AnyMessage, FieldMask)
FIELD_INFO_CLASS_ATTR = "_protobuf_to_pydantic_field_info_class"


def replace_file_name_to_class_name(filename: str) -> str:
    pass


class CodeRefModel(object):
    def __init__(
        self,
        one_of_dict: Dict[str, "UseOneOfTypedDict"],
        base_model: Type["BaseModel"],
        nested_message_dict: Dict[str, Type[Union[BaseModel, IntEnum]]],
        validators: Dict[str, classmethod],
    ) -> None:
        self.one_of_dict = one_of_dict
        self.base_model = base_model
        self.nested_message_dict = nested_message_dict
        self.validators = validators

    @classmethod
    def from_model(cls, model: Type[BaseModel]) -> "CodeRefModel":
        code_ref_model = getattr(model, "_code_ref", None)
        if code_ref_model and isinstance(code_ref_model, cls):
            return code_ref_model
        raise ValueError("Not found CodeRefModel, please set `enable_code_ref_gen==True` in gen_model func or class")

    @classmethod
    def set_to_model(
        cls,
        model: Type[BaseModel],
        *,
        one_of_dict: Dict[str, "UseOneOfTypedDict"],
        base_model: Type["BaseModel"],
        nested_message_dict: Dict[str, Type[Union[BaseModel, IntEnum]]],
        validators: Dict[str, classmethod],
    ) -> None:
        pass


@dataclasses.dataclass
class FieldDataClass(object):
    field_name: str
    field_type: Any
    field_type_name: str
    field_default: Any
    field_default_factory: Optional[_pydantic_adapter.NoArgAnyCallable]
    is_required: bool
    protobuf_field: FieldDescriptor
    nested_message_dict: Dict[str, Type[Union[BaseModel, IntEnum]]]
    descriptor: Descriptor
    validators: Dict[str, classmethod]


CREATE_MODEL_CACHE_T = Dict[Union[str, tuple], Optional[Type[BaseModel]]]
_create_model_cache: CREATE_MODEL_CACHE_T = {}


def clear_create_model_cache() -> None:
    _create_model_cache.clear()


def _set_field_info_default(field_info: FieldInfo, value: Any) -> None:
    pass


class M2P(object):
    def __init__(
        self,
        msg: Union[Type[Message], Descriptor],
        default_field: Type[FieldInfo] = FieldInfo,
        comment_prefix: str = "p2p",
        parse_msg_desc_method: Any = None,
        pydantic_base: Optional[Type["BaseModel"]] = None,
        pydantic_module: Optional[str] = None,
        local_dict: Optional[Dict[str, Any]] = None,
        template: Optional[Type[Template]] = None,
        message_type_dict_by_type_name: Optional[Dict[str, Any]] = None,
        message_default_factory_dict_by_type_name: Optional[Dict[str, Any]] = None,
        all_field_set_optional: bool = False,
        create_model_cache: Optional[CREATE_MODEL_CACHE_T] = None,
        enable_enum_name_value_desc: bool = False,
    ):
        proto_file_name = msg.DESCRIPTOR.file.name  # type: ignore
        global_message_option_dict: Dict[str, "MessageOptionTypedDict"] = {}

        if proto_file_name.endswith("empty.proto") or parse_msg_desc_method == "ignore":
            pass
        elif isinstance(parse_msg_desc_method, str) and Path(parse_msg_desc_method).exists():
            file_str: str = parse_msg_desc_method
            if not file_str.endswith("/"):
                file_str += "/"
            global_message_option_dict = get_message_option_dict_from_proto_file(
                file_str + proto_file_name, comment_prefix
            )
        elif inspect.ismodule(parse_msg_desc_method):
            if getattr(parse_msg_desc_method, msg.__name__, None) is not msg:  # type: ignore
                raise ValueError(f"Not the module corresponding to {msg}")
            pyi_file_name = parse_msg_desc_method.__file__ + "i"  # type: ignore
            if not Path(pyi_file_name).exists():
                raise RuntimeError(f"Can not found {msg} pyi file")
            global_message_option_dict = get_message_option_dict_from_pyi_file(pyi_file_name, comment_prefix)
        elif parse_msg_desc_method == "PGV":
            global_message_option_dict = get_message_option_dict_from_message_with_pgv(message=msg)  # type: ignore
        elif parse_msg_desc_method is not None:
            raise ValueError(
                f"parse_msg_desc_method param must be exist path, `ignore` or `PGV`,"
                f" not {parse_msg_desc_method}), now path:{os.getcwd()}"
            )
        else:
            global_message_option_dict = get_message_option_dict_from_message_with_p2p(message=msg)  # type: ignore

        self._all_field_set_optional: bool = all_field_set_optional
        self._parse_msg_desc_method = parse_msg_desc_method
        self._message_option_dict = global_message_option_dict
        self._default_field = default_field
        self._comment_prefix = comment_prefix
        self._creat_cache: CREATE_MODEL_CACHE_T = create_model_cache or _create_model_cache
        self._pydantic_base: Type["BaseModel"] = pydantic_base or BaseModel
        self._pydantic_module: str = pydantic_module or __name__
        self._comment_template: Template = (template or Template)(local_dict or {}, comment_prefix)
        self._message_type_dict_by_type_name: Dict[str, Any] = (
            message_type_dict_by_type_name or constant.message_name_type_dict
        )
        self._message_default_factory_dict_by_type_name: Dict[str, Any] = (
            message_default_factory_dict_by_type_name or constant.message_name_default_factory_dict
        )
        self._enable_enum_name_value_desc = enable_enum_name_value_desc

        self._gen_model: Type[BaseModel] = self._parse_msg_to_pydantic_model(
            descriptor=msg if isinstance(msg, Descriptor) else msg.DESCRIPTOR,
        )

    @property
    def model(self) -> Type[BaseModel]:
        pass

    def get_model(self, full_name: str) -> Type[BaseModel]:
        pass

    def _get_field_info_dict_by_full_name(
        self, full_name: str, package_name: str = ""
    ) -> Optional["FieldInfoTypedDict"]:
        pass

    def _is_type_a_mapping(self, message_type: Descriptor) -> bool:
        pass

    def _gen_enum_name_value_desc(self, enum_type: Any) -> str:
        if not self._enable_enum_name_value_desc:
            return ""
        value_desc = "\n".join(f"- {v.name} = {v.number}" for v in enum_type.values)
        if value_desc:
            return f"Enumeration {enum_type.name}:\n{value_desc}"
        return f"Enumeration {enum_type.name}:"

    @staticmethod
    def _merge_desc(*desc_list: str) -> str:
        return "\n\n".join(desc for desc in desc_list if desc)

    def _one_of_handle(self, descriptor: Descriptor) -> Tuple[Dict[str, "UseOneOfTypedDict"], Dict[str, Any]]:
        pass

    def _get_pydantic_base(self, config_dict: Dict[str, Any]) -> Type[BaseModel]:
        pass

    def get_nested_message_dict_by_message(self, descriptor: Descriptor) -> Dict[str, Type[Union[BaseModel, IntEnum]]]:
        pass

    def _protobuf_field_type_is_type_message_handler(self, field_dataclass: FieldDataClass, package_name: str) -> None:
        pass

    def _protobuf_field_type_is_type_enum_handler(self, field_dataclass: FieldDataClass) -> None:
        pass

    def _protobuf_field_lable_is_label_repeated_handler(self, field_dataclass: FieldDataClass) -> None:
        pass

    def _gen_field_info(
        self, field_dataclass: FieldDataClass, skip_validate_rule: bool, package_name: str
    ) -> Optional[FieldInfo]:
        pass

    def _parse_msg_to_pydantic_model(
        self,
        *,
        descriptor: Descriptor,
        class_name: str = "",
        skip_validate_rule: bool = False,
        root_descriptor: Optional[Descriptor] = None,
    ) -> Type[BaseModel]:
        pass


def msg_to_pydantic_model(
    msg: Union[Type[Message], Descriptor],
    default_field: Type[FieldInfo] = FieldInfo,
    comment_prefix: str = "p2p",
    parse_msg_desc_method: Any = None,
    local_dict: Optional[Dict[str, Any]] = None,
    pydantic_base: Optional[Type["BaseModel"]] = None,
    pydantic_module: Optional[str] = None,
    template: Optional[Type[Template]] = None,
    message_type_dict_by_type_name: Optional[Dict[str, Any]] = None,
    message_default_factory_dict_by_type_name: Optional[Dict[str, Any]] = None,
    all_field_set_optional: bool = False,
    create_model_cache: Optional[CREATE_MODEL_CACHE_T] = None,
    enable_enum_name_value_desc: bool = False,
) -> Type[BaseModel]:
    """
    Parse a message to a pydantic model
    :param msg: grpc Message or descriptor
    :param default_field: gen pydantic_model default Field, apply only to the outermost pydantic model
    :param comment_prefix: Customize the prefixes that need to be parsed for comments
    :param parse_msg_desc_method:
        Define a method for extracting the message extension property
        1.If the value is 'ignore', it means that no extraction is made
        2.If the value is the Protobuf file path, the Protobuf file is parsed and the information is extracted from
         the comments in the file
         Note: The extracted content is a text comment in the Protobuf file
        3.If the value is a Message object's module, it is extracted from the corresponding pyi file
         (pyi file is generated by mypy-protobuf)
         Note: The extracted content is a text comment in the Protobuf file
        4.If the value is PGV, the corresponding PGV information is extracted from the Message object
        5.If the value is None (default), the P2P information is extracted from the Message)
    :param local_dict: The variables corresponding to the p2p@local template
    :param pydantic_base: custom pydantic.BaseModel
    :param pydantic_module: custom create model's module name
    :param template: DescTemplate object, which can extend and modify template adaptation rules through inheritance
    :param message_type_dict_by_type_name: Define the Python type mapping corresponding to each Protobuf Type
    :param message_default_factory_dict_by_type_name: Define the default_factory corresponding to each Protobuf Type
    :param create_model_cache: Cache the generated model
    :param all_field_set_optional: If true, all fields become optional,
        see: https://github.com/so1n/protobuf_to_pydantic/issues/60
    :param enable_enum_name_value_desc: If true, generated IntEnum docs include protobuf enum name/value pairs.
    """
    return M2P(
        msg=msg,
        default_field=default_field,
        comment_prefix=comment_prefix,
        parse_msg_desc_method=parse_msg_desc_method,
        local_dict=local_dict,
        pydantic_module=pydantic_module,
        pydantic_base=pydantic_base,
        template=template,
        message_type_dict_by_type_name=message_type_dict_by_type_name,
        message_default_factory_dict_by_type_name=message_default_factory_dict_by_type_name,
        create_model_cache=create_model_cache,
        all_field_set_optional=all_field_set_optional,
        enable_enum_name_value_desc=enable_enum_name_value_desc,
    ).model

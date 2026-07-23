import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

from lark import Lark, Token, Transformer, Tree
from lark.tree import ParseTree  # type: ignore

BNF = r"""
OCTALDIGIT: "0..7"
IDENT: ( "_" )* LETTER ( LETTER | DECIMALDIGIT | "_" )*
FULLIDENT: IDENT ( "." IDENT )*
MESSAGENAME: IDENT
ENUMNAME: IDENT
FIELDNAME: IDENT
ONEOFNAME: IDENT
MAPNAME: IDENT
SERVICENAME: IDENT
TAGNAME: IDENT
TAGVALUE: IDENT
RPCNAME: IDENT
MESSAGETYPE: [ "." ] ( IDENT "." )* MESSAGENAME
ENUMTYPE: [ "." ] ( IDENT "." )* ENUMNAME
INTLIT    : DECIMALLIT | OCTALLIT | HEXLIT
DECIMALLIT: ( "1".."9" ) ( DECIMALDIGIT )*
OCTALLIT  : "0" ( OCTALDIGIT )*
HEXLIT    : "0" ( "x" | "X" ) HEXDIGIT ( HEXDIGIT )*
FLOATLIT: ( DECIMALS "." [ DECIMALS ] [ EXPONENT ] | DECIMALS EXPONENT | "."DECIMALS [ EXPONENT ] ) | "inf" | "nan"
DECIMALS : DECIMALDIGIT ( DECIMALDIGIT )*
EXPONENT : ( "e" | "E" ) [ "+" | "-" ] DECIMALS
BOOLLIT: "true" | "false"
STRLIT: ( "'" ( CHARVALUE )* "'" ) |  ( "\"" ( CHARVALUE )* "\"" )
CHARVALUE: HEXESCAPE | OCTESCAPE | CHARESCAPE |  /[^\0\n\\]/
HEXESCAPE: "\\" ( "x" | "X" ) HEXDIGIT HEXDIGIT
OCTESCAPE: "\\" OCTALDIGIT OCTALDIGIT OCTALDIGIT
CHARESCAPE: "\\" ( "a" | "b" | "f" | "n" | "r" | "t" | "v" | "\\" | "'" | "\"" )
QUOTE: "'" | "\""
EMPTYSTATEMENT: ";"
CONSTANT: FULLIDENT | ( [ "-" | "+" ] INTLIT ) | ( [ "-" | "+" ] FLOATLIT ) | STRLIT | BOOLLIT
syntax: "syntax" "=" QUOTE "proto3" QUOTE ";"
import: "import" [ "weak" | "public" ] STRLIT ";"
package: "package" FULLIDENT ";"
option: "option" OPTIONNAME  "=" CONSTANT ";"
OPTIONNAME: ( IDENT | "(" FULLIDENT ")" ) ( "." IDENT )*
TYPE: "double" | "float" | "int32" | "int64" | "uint32" | "uint64" | "sint32" | "sint64" | "fixed32"
    | "fixed64" | "sfixed32" | "sfixed64" | "bool" | "string" | "bytes" | MESSAGETYPE | ENUMTYPE
FIELDNUMBER: INTLIT
field: [ comments ] TYPE FIELDNAME "=" FIELDNUMBER [ "[" fieldoptions "]" ] TAIL
fieldoptions: fieldoption ( ","  fieldoption )*
fieldoption: OPTIONNAME "=" CONSTANT
repeatedfield: [ comments ] "repeated" field
optionalfield: [ comments ] "optional" field
oneof: [ comments ] "oneof" ONEOFNAME "{" ( oneoffield | EMPTYSTATEMENT )* "}"
oneoffield:  [ comments ] TYPE FIELDNAME "=" FIELDNUMBER [ "[" fieldoptions "]" ] ";"
mapfield: [ comments ] "map" "<" KEYTYPE "," TYPE ">" MAPNAME "=" FIELDNUMBER [ "[" fieldoptions "]" ] TAIL
KEYTYPE: "int32" | "int64" | "uint32" | "uint64" | "sint32" | "sint64" | "fixed32" | "fixed64" | "sfixed32"
    | "sfixed64" | "bool" | "string"
reserved: "reserved" ( ranges | fieldnames ) ";"
ranges: range ( "," range )*
range:  INTLIT [ "to" ( INTLIT | "max" ) ]
fieldnames: FIELDNAME ( "," FIELDNAME )*
enum: [ comments ] "enum" ENUMNAME enumbody
enumbody: "{" ( enumfield | EMPTYSTATEMENT )* "}"
enumfield: [ COMMENTS ] IDENT "=" INTLIT [ "[" enumvalueoption ( ","  enumvalueoption )* "]" ] TAIL
enumvalueoption: OPTIONNAME "=" CONSTANT
message: [ comments ] "message" MESSAGENAME messagebody
messagebody: "{" ( repeatedfield | optionalfield | field | enum | message | option | oneof | mapfield | reserved
    | EMPTYSTATEMENT | comments )* "}"
googleoption: "option" "(google.api.http)"  "=" "{" [ "post:" CONSTANT [ "body:" CONSTANT ] ] "}" ";"
service: [ comments ] "service" SERVICENAME "{" ( option | rpc | EMPTYSTATEMENT )* "}"
rpc: [ comments ] "rpc" RPCNAME "(" [ "stream" ] MESSAGETYPE ")" "returns" "(" [ "stream" ] MESSAGETYPE ")" \
 ( ( "{" ( googleoption | option | EMPTYSTATEMENT )* "}" ) | ";" )
proto:[ comments ] syntax ( import | package | option | topleveldef | EMPTYSTATEMENT )*
topleveldef: message | enum | service | comments
TAIL: ";" [/[\s|\t]/] [ COMMENT ]
COMMENT: "//" /.*/ [ "\n" ]
comments: COMMENT ( COMMENT )*
COMMENTS: COMMENT ( COMMENT )*
%import common.HEXDIGIT
%import common.DIGIT -> DECIMALDIGIT
%import common.LETTER
%import common.WS
%import common.NEWLINE
%ignore WS
"""


@dataclass
class Comment(object):
    content: str
    tags: Dict[str, Any]


@dataclass
class Field(object):
    comment: Comment
    type: str
    key_type: str
    val_type: str
    name: str
    number: int


@dataclass
class OneOfField(object):
    comment: Comment
    type: str
    key_type: str
    val_type: str
    name: str
    number: int


@dataclass
class Enum(object):
    comment: Comment
    name: str
    fields: Dict[str, Field]


@dataclass
class Message(object):
    comment: Comment
    name: str
    oneofs: List[OneOfField]
    fields: List[Field]
    messages: Dict[str, "Message"]
    enums: Dict[str, Enum]


@dataclass
class RpcFunc(object):
    name: str
    in_type: str
    out_type: str
    uri: str


@dataclass
class Service(object):
    name: str
    functions: List[RpcFunc]


@dataclass
class ProtoFile(object):
    messages: Dict[str, Message]
    enums: Dict[str, Enum]
    services: Dict[str, Service]
    imports: List[str]
    options: Dict[str, str]
    package: str


class ProtoTransformer(Transformer):

    @staticmethod
    def message(tokens: list) -> Message:
        pass

    @staticmethod
    def messagebody(
        items: List[Union[Message, Enum, Field]]
    ) -> Tuple[List[OneOfField], List[Field], Dict[str, Message], Dict[str, Enum]]:
        pass

    @staticmethod
    def field(tokens: list) -> Field:
        pass

    @staticmethod
    def repeatedfield(tokens: list) -> Field:
        pass

    @staticmethod
    def optionalfield(tokens: list) -> Field:
        pass

    def oneoffield(self, tokens: list) -> OneOfField:
        pass

    def oneof(self, tokens: list) -> Token:
        pass

    @staticmethod
    def mapfield(tokens: list) -> Field:
        pass

    @staticmethod
    def comments(tokens: list) -> Comment:
        pass

    @staticmethod
    def enum(tokens: list) -> Enum:
        pass

    @staticmethod
    def enumbody(tokens: list) -> List[Field]:
        pass

    @staticmethod
    def service(tokens: list) -> Service:
        pass

    @staticmethod
    def rpc(tokens: List) -> RpcFunc:
        pass


def _recursive_to_dict(obj: Any) -> Dict[str, Any]:
    pass


def parse_from_file(file: str) -> Optional[ProtoFile]:
    with open(file, "r") as f:
        data = f.read()
    if data:
        return parse(data)
    return None


def parse(data: str) -> ProtoFile:
    parser: Lark = Lark(BNF, start="proto", parser="lalr")
    tree: ParseTree = parser.parse(data)
    trans_tree: Tree = ProtoTransformer().transform(tree)
    enums: Dict[str, Enum] = {}
    messages: Dict[str, Message] = {}
    services: Dict[str, Service] = {}
    imports: List[str] = []
    options: Dict[str, str] = {}
    package: str = ""

    import_tree = trans_tree.find_data("import")
    for tree in import_tree:
        for child in tree.children:
            imports.append(child.value.strip('"'))

    option_tree = trans_tree.find_data("option")
    for tree in option_tree:
        options[tree.children[0]] = tree.children[1].strip('"')

    package_tree = trans_tree.find_data("package")
    for tree in package_tree:
        package = tree.children[0]

    top_data = trans_tree.find_data("topleveldef")
    for top_level in top_data:
        for child in top_level.children:
            if isinstance(child, Message):
                messages[child.name] = child
            if isinstance(child, Enum):
                enums[child.name] = child
            if isinstance(child, Service):
                services[child.name] = child
    return ProtoFile(messages, enums, services, imports, options, package)


def serialize2json(data: str) -> str:
    pass


def serialize2json_from_file(file: str) -> Optional[str]:
    pass

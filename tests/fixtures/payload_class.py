from typing import Type

import pytest


from src.s3p_plugin_parser_jcb.jcb import JCB as imported_payload_class


@pytest.fixture(scope="module")
def fix_plugin_class() -> Type[imported_payload_class]:
    return imported_payload_class

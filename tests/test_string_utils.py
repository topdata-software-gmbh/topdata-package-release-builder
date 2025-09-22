import pytest

from topdata_package_release_builder.string_utils import camel_to_kebab_for_js_asset


@pytest.mark.parametrize(
    "input_str,expected",
    [
        ("TopdataCategoryFilterSW6", "topdata-category-filter-s-w6"),
        ("MyPlugin", "my-plugin"),
        ("MySWPlugin", "my-s-w-plugin"),
        ("AnotherSW", "another-s-w"),
        ("Plugin2Go", "plugin2-go"),
    ],
)
def test_camel_to_kebab_for_js_asset(input_str, expected):
    assert camel_to_kebab_for_js_asset(input_str) == expected

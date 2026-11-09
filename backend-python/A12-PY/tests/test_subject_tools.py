import json
import unittest

from a12_ppt.presentation.subject_tools import (
    DEFAULT_SUBJECT_DATA,
    SUBJECT_TOOL_TYPES,
    default_subject_data,
    normalize_subject_tool_markup,
    normalize_subject_tool_type,
    subject_tools_prompt_section,
)


def read_attribute(tag_text: str, name: str) -> str:
    marker = f'{name}="'
    start = tag_text.index(marker) + len(marker)
    end = tag_text.index('"', start)
    return tag_text[start:end]


def read_data_attribute(tag_text: str) -> dict:
    marker = "data-subject-data='"
    start = tag_text.index(marker) + len(marker)
    end = tag_text.index("'", start)
    return json.loads(tag_text[start:end])


class SubjectToolMarkupTests(unittest.TestCase):
    def test_plain_html_is_untouched(self):
        html = "<html><body><div class=\"card\">没有学科工具</div></body></html>"
        self.assertEqual(normalize_subject_tool_markup(html), html)

    def test_valid_container_is_canonicalized(self):
        html = (
            '<div class="card" data-subject-type="coordinate_system" '
            "data-subject-data='{\"xRange\":8,\"yRange\":6,\"points\":[{\"label\":\"A\",\"x\":1,\"y\":2}]}'>"
            "<svg></svg></div>"
        )
        result = normalize_subject_tool_markup(html)
        self.assertIn('data-ppt-type="subject"', result)
        self.assertIn('data-subject-type="coordinate_system"', result)
        self.assertIn('id="a12-subject-1"', result)
        self.assertIn('class="card"', result)
        data = read_data_attribute(result)
        self.assertEqual(data["xRange"], 8)
        self.assertEqual(data["points"][0]["label"], "A")

    def test_malformed_attribute_quotes_are_repaired(self):
        html = (
            '<div data-subject-type="coordinate_system" '
            'data-subject-data="{"xRange":8,"yRange":6,"points":[{"label":"A","x":1,"y":2}]}">x</div>'
        )
        result = normalize_subject_tool_markup(html)
        self.assertIn('data-subject-type="coordinate_system"', result)
        self.assertNotIn('data-subject-data="', result)
        data = read_data_attribute(result)
        self.assertEqual(data["xRange"], 8)
        self.assertEqual(data["yRange"], 6)
        self.assertEqual(data["points"][0]["x"], 1)

    def test_invalid_json_falls_back_to_defaults(self):
        html = '<div data-subject-type="table" data-subject-data="{not json">x</div>'
        result = normalize_subject_tool_markup(html)
        self.assertEqual(read_data_attribute(result), DEFAULT_SUBJECT_DATA["table"])

    def test_type_alias_is_normalized(self):
        html = '<div data-subject-type="coordinate" data-subject-data=\'{"xRange":4}\'>x</div>'
        result = normalize_subject_tool_markup(html)
        self.assertIn('data-subject-type="coordinate_system"', result)
        self.assertEqual(read_data_attribute(result)["xRange"], 4)

    def test_type_is_inferred_from_payload(self):
        html = '<div data-subject-data=\'{"type":"mermaid_diagram","mermaid":"flowchart LR\\nA-->B"}\'>x</div>'
        result = normalize_subject_tool_markup(html)
        self.assertIn('data-subject-type="mermaid_diagram"', result)
        self.assertIn("flowchart LR", read_data_attribute(result)["mermaid"])

    def test_payload_without_type_drops_subject_markers(self):
        html = '<div class="card" data-subject-data=\'{"foo":1}\'>x</div>'
        result = normalize_subject_tool_markup(html)
        self.assertNotIn("data-subject-data", result)
        self.assertIn('class="card"', result)
        self.assertIn("x</div>", result)

    def test_multiple_containers_get_unique_ids(self):
        html = (
            '<div data-subject-type="geometry" data-subject-data=\'{"construction":"square"}\'>a</div>'
            '<div data-subject-type="table" data-subject-data=\'{"columns":["A"],"rows":[["1"]]}\'>b</div>'
        )
        result = normalize_subject_tool_markup(html)
        self.assertIn('id="a12-subject-1"', result)
        self.assertIn('id="a12-subject-2"', result)

    def test_existing_id_is_kept(self):
        html = '<div id="subject-9" data-subject-type="english_four_line" data-subject-data=\'{"text":"Aa"}\'>x</div>'
        result = normalize_subject_tool_markup(html)
        self.assertIn('id="subject-9"', result)
        self.assertNotIn("a12-subject-1", result)

    def test_duplicate_ids_are_deduplicated(self):
        html = (
            '<div id="dup" data-subject-type="geometry" data-subject-data=\'{"construction":"square"}\'>a</div>'
            '<div id="dup" data-subject-type="table" data-subject-data=\'{"columns":["A"],"rows":[["1"]]}\'>b</div>'
        )
        result = normalize_subject_tool_markup(html)
        self.assertEqual(result.count('id="dup"'), 1)
        self.assertIn('id="a12-subject-2"', result)

    def test_out_of_range_values_are_clamped(self):
        html = (
            '<div data-subject-type="coordinate_system" '
            "data-subject-data='{\"xRange\":99,\"yRange\":-3,\"points\":[{\"x\":999,\"y\":-999}]}'>x</div>"
        )
        data = read_data_attribute(normalize_subject_tool_markup(html))
        self.assertEqual(data["xRange"], 10)
        self.assertEqual(data["yRange"], 2)
        self.assertEqual(data["points"][0]["x"], 10)
        self.assertEqual(data["points"][0]["y"], -2)

    def test_invalid_enum_falls_back_to_default_shape(self):
        html = '<div data-subject-type="solid_geometry" data-subject-data=\'{"solid":"hexagon"}\'>x</div>'
        data = read_data_attribute(normalize_subject_tool_markup(html))
        self.assertEqual(data["solid"], "cube")
        self.assertEqual(data["dimensions"], DEFAULT_SUBJECT_DATA["solid_geometry"]["dimensions"])

    def test_single_quote_inside_payload_is_escaped(self):
        html = (
            '<div data-subject-type="table" '
            "data-subject-data='{\"columns\":[\"项目\"],\"rows\":[[\"It's fine\"]]}'>x</div>"
        )
        result = normalize_subject_tool_markup(html)
        self.assertIn("\\u0027", result)
        self.assertEqual(read_data_attribute(result)["rows"][0][0], "It's fine")

    def test_other_attributes_and_children_are_preserved(self):
        html = (
            '<div id="tool-1" class="a12-subject-tool card" style="width:520px" '
            "data-subject-type=\"mermaid_diagram\" data-subject-data='{\"mermaid\":\"flowchart LR\\nA-->B\"}'>"
            '<svg viewBox="0 0 10 10"><path d="M0 0"/></svg></div>'
        )
        result = normalize_subject_tool_markup(html)
        self.assertIn('class="a12-subject-tool card"', result)
        self.assertIn('style="width:520px"', result)
        self.assertIn('<svg viewBox="0 0 10 10"><path d="M0 0"/></svg></div>', result)

    def test_data_name_is_filled_when_missing(self):
        html = '<div data-subject-type="chinese_tianzige" data-subject-data=\'{"entries":[{"character":"你"}]}\'>x</div>'
        result = normalize_subject_tool_markup(html)
        self.assertIn('data-name="语文田字格/拼音"', result)


class SubjectToolPayloadTests(unittest.TestCase):
    def test_every_type_round_trips_through_markup(self):
        for subject_type in SUBJECT_TOOL_TYPES:
            with self.subTest(subject_type=subject_type):
                payload = json.dumps(default_subject_data(subject_type), ensure_ascii=False)
                html = f'<div data-subject-type="{subject_type}" data-subject-data=\'{payload}\'>x</div>'
                result = normalize_subject_tool_markup(html)
                self.assertIn(f'data-subject-type="{subject_type}"', result)
                data = read_data_attribute(result)
                self.assertIsInstance(data, dict)

    def test_unknown_type_falls_back_to_geometry(self):
        self.assertEqual(normalize_subject_tool_type("quantum_board"), "geometry")
        self.assertEqual(normalize_subject_tool_type(""), "geometry")
        self.assertEqual(normalize_subject_tool_type("TIANZIGE"), "chinese_tianzige")

    def test_defaults_are_deep_copied(self):
        first = default_subject_data("table")
        first["columns"].append("__mutated__")
        self.assertNotIn("__mutated__", DEFAULT_SUBJECT_DATA["table"]["columns"])

    def test_prompt_section_lists_every_type(self):
        section = subject_tools_prompt_section()
        for subject_type in SUBJECT_TOOL_TYPES:
            self.assertIn(subject_type, section)
        self.assertIn("data-subject-data", section)


if __name__ == "__main__":
    unittest.main()

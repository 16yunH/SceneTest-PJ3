from __future__ import annotations

import unittest

from scenetest.agents.code_agent import CodeAgent
from scenetest.agents.contract_agent import ContractAgent
from scenetest.core.contract_schema import CameraSpec, ContractObject, Relation, SceneContract
from scenetest.core.repair_rules import repair_loop
from scenetest.core.scene_builder import SceneBuilder
from scenetest.core.test_compiler import compile_tests
from scenetest.core.test_runner import execute_scene_code, run_tests, summarize_results


PROMPT = (
    "Create a cozy desk scene with a laptop on a wooden desk, a lamp to the left "
    "of the laptop, a coffee cup to the right of the laptop, and a small plant "
    "behind the laptop. Use warm yellow lighting."
)


class PipelineTests(unittest.TestCase):
    def test_contract_parser_extracts_core_requirements(self) -> None:
        contract = ContractAgent().parse(PROMPT, scene_id="unit")
        self.assertEqual(contract.get_object("desk").material, "wood")
        relation_keys = {(rel.subject, rel.relation, rel.object) for rel in contract.relations}
        self.assertIn(("laptop", "on", "desk"), relation_keys)
        self.assertIn(("lamp", "left_of", "laptop"), relation_keys)
        self.assertIn(("coffee_cup", "right_of", "laptop"), relation_keys)
        self.assertIn(("plant", "behind", "laptop"), relation_keys)
        self.assertEqual(contract.style["lighting"], "warm")

    def test_repair_loop_passes_compiled_tests(self) -> None:
        contract = ContractAgent().parse(PROMPT, scene_id="unit")
        tests = compile_tests(contract)
        scene, error = execute_scene_code(CodeAgent().generate(contract, method="contract_only"))
        self.assertIsNone(error)
        before = summarize_results(run_tests(scene, tests))
        self.assertLess(before["passed"], before["total"])
        repaired = repair_loop(scene, contract, tests, max_iterations=3)
        after = summarize_results(repaired["final_results"])
        self.assertEqual(after["passed"], after["total"])
        self.assertGreaterEqual(repaired["iterations"], 1)

    def test_open_object_parser_resolves_short_references(self) -> None:
        prompt = (
            "Create a chess table scene with a chess board on a table, a white king "
            "to the left of the board, a black queen to the right of the board, "
            "and a clock behind the board. Use neutral lighting."
        )
        contract = ContractAgent().parse(prompt, scene_id="chess")
        relation_keys = {(rel.subject, rel.relation, rel.object) for rel in contract.relations}
        self.assertIn(("king", "left_of", "chess_board"), relation_keys)
        self.assertIn(("queen", "right_of", "chess_board"), relation_keys)
        self.assertIn(("clock", "behind", "chess_board"), relation_keys)
        self.assertIn(("chess_board", "on", "table"), relation_keys)

    def test_open_object_parser_filters_scene_titles_and_plain_cups(self) -> None:
        prompt = (
            "Create a bathroom counter with a mirror behind a table, a soap dispenser "
            "to the left of the mirror, a toothbrush cup to the right of the mirror, "
            "and a towel in front of the table. Use clean neutral lighting."
        )
        contract = ContractAgent().parse(prompt, scene_id="bathroom")
        object_ids = {obj.id for obj in contract.objects}
        relation_keys = {(rel.subject, rel.relation, rel.object) for rel in contract.relations}
        self.assertNotIn("bathroom_counter", object_ids)
        self.assertNotIn("coffee_cup", object_ids)
        self.assertIn("cup", object_ids)
        self.assertIn(("cup", "right_of", "mirror"), relation_keys)

    def test_open_object_parser_maps_definite_noun_aliases(self) -> None:
        prompt = (
            "Create a warehouse packing table with a cardboard box on a table, "
            "a barcode scanner to the right of the box, a tape roll to the left "
            "of the box, and a label printer behind the table. Use bright neutral lighting."
        )
        contract = ContractAgent().parse(prompt, scene_id="warehouse")
        relation_keys = {(rel.subject, rel.relation, rel.object) for rel in contract.relations}
        self.assertIn(("barcode_scanner", "right_of", "cardboard_box"), relation_keys)
        self.assertIn(("tape_roll", "left_of", "cardboard_box"), relation_keys)
        self.assertIn(("cardboard_box", "on", "table"), relation_keys)

    def test_supported_objects_remain_on_surface_after_planar_relation(self) -> None:
        scene = SceneBuilder()
        scene.add_low_table("low_table")
        scene.add_cube("tray", on="low_table")
        scene.add_cylinder("vase", on="low_table")
        scene.place_relation("vase", "behind", "tray", margin=0.35)
        contract = SceneContract(
            id="support_relation",
            prompt="vase on table and behind tray",
            objects=[
                ContractObject(id="low_table", type="low_table"),
                ContractObject(id="tray", type="cube"),
                ContractObject(id="vase", type="cylinder"),
            ],
            relations=[
                Relation(subject="vase", relation="on", object="low_table", margin=0.2),
                Relation(subject="vase", relation="behind", object="tray", margin=0.2),
            ],
            style={"lighting": "neutral"},
            camera=CameraSpec(visible_objects=["low_table", "tray", "vase"]),
        )
        summary = summarize_results(run_tests(scene, compile_tests(contract)))
        self.assertEqual(summary["passed"], summary["total"])


if __name__ == "__main__":
    unittest.main()

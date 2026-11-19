"""Request order is part of the model input contract, not just JSON key/value equality."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")
TEXT = "질문 계약 검사: 기록된 문구와 선택지 순서를 보존합니다."


@unittest.skipUnless(NODE, "Node is required for actual JavaScript request construction")
class QuestionContractOrderTests(unittest.TestCase):
    def javascript(self, mutation=""):
        code = "const E=require(process.argv[1]);" + mutation + "process.stdout.write(JSON.stringify(E.questions(process.argv[2])));"
        return json.loads(subprocess.check_output([NODE, "-e", code, str(ROOT / "apps/shared/dmsg-engine.js"), TEXT], text=True))

    def python(self, source, module):
        code = "import sys,json;sys.path.insert(0,sys.argv[1]);from " + module + " import model_bridge as m;print(json.dumps(m.questions(sys.argv[2]),ensure_ascii=False))"
        return json.loads(subprocess.check_output([sys.executable, "-c", code, str(source), TEXT], text=True))

    def test_actual_javascript_and_both_python_requests_have_identical_option_order(self):
        js = self.javascript()
        for label, source, module in [("dmsg", ROOT, "dmsg.prototype"), ("vendor", ROOT / "vendor/dmsg", "prototype")]:
            with self.subTest(python_source=label):
                py = self.python(source, module)
                self.assertEqual(js, py, "Question content changed")
                self.assertEqual(list(js["questions"]), list(py["questions"]), "Question order changed")
                for key, q in py["questions"].items():
                    if q["type"] == "choice":
                        self.assertEqual(list(js["questions"][key]["criteria"]), list(q["criteria"]),
                                         key + " Choice order differs despite equal JSON values")
                    elif q["type"] == "score":
                        self.assertEqual(js["questions"][key]["criteria"], q["criteria"])

    def test_choice_criteria_missing_or_extra_key_is_rejected(self):
        for mutation in ["delete E.data.model.questions.q_action.criteria.none;",
                         "E.data.model.questions.q_action.criteria.unapproved='extra';"]:
            with self.subTest(mutation=mutation):
                code = ("const E=require(process.argv[1]);" + mutation +
                        "try{E.questions('x');process.stdout.write(JSON.stringify({accepted:true}));}"
                        "catch(e){process.stdout.write(JSON.stringify({name:e.name,code:e.code}));}")
                result = json.loads(subprocess.check_output([NODE, "-e", code, str(ROOT / "apps/shared/dmsg-engine.js")], text=True))
                self.assertEqual(result, {"name": "ContractError", "code": "QUESTION_CRITERIA_MISMATCH_q_action"})

    def test_building_request_does_not_mutate_exported_question_data(self):
        code = ("const E=require(process.argv[1]);const before=JSON.stringify(E.data.model.questions);"
                "const q=E.questions('x');q.questions.q_action.criteria.none='changed externally';"
                "process.stdout.write(JSON.stringify({same:before===JSON.stringify(E.data.model.questions)}));")
        result = json.loads(subprocess.check_output([NODE, "-e", code, str(ROOT / "apps/shared/dmsg-engine.js")], text=True))
        self.assertTrue(result["same"])


if __name__ == "__main__":
    unittest.main()
